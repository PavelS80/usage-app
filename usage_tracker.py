#!/usr/bin/env python3
"""
Claude Code stop hook — čte tokeny přímo z transcript JSONL souborů.
Spouštěno automaticky po každé odpovědi (Stop hook).
Použití pro rebuild: python3 usage_tracker.py --rebuild
"""
import sys
import json
import os
import glob
from datetime import datetime, timezone, timedelta

LOG_PATH    = os.path.expanduser("~/.claude/usage_log.json")
ALERTS_PATH = os.path.expanduser("~/.claude/usage_alerts.json")
DEBUG_LOG   = os.path.expanduser("~/.claude/usage_debug.log")
PROJ_DIR    = os.path.expanduser("~/.claude/projects")

# ── Limity (uprav dle svého plánu) ──────────────────────────────────────────
LIMITS = {
    "daily_cost_usd":   20.0,    # USD / den
    "weekly_cost_usd": 100.0,    # USD / týden
    "session_cost_usd": 10.0,    # USD / session
}
THRESHOLDS = [30, 50, 75, 90]   # % pro upozornění

# ── Ceny za 1M tokenů ───────────────────────────────────────────────────────
PRICES = {
    "claude-sonnet-4-6": {"input": 3.0,  "output": 15.0,  "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4-7":   {"input": 15.0, "output": 75.0,  "cache_read": 1.50, "cache_write": 18.75},
    "claude-haiku-4-5":  {"input": 0.80, "output": 4.0,   "cache_read": 0.08, "cache_write": 1.00},
}
DEFAULT_PRICE = {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75}

def calc_cost(model, inp, out, cr, cw):
    p = PRICES.get(model, DEFAULT_PRICE)
    return (inp * p["input"] + out * p["output"] +
            cr * p["cache_read"] + cw * p["cache_write"]) / 1_000_000

def debug(msg):
    with open(DEBUG_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")

def load_log():
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "sessions": [],
        "daily": {},
        "total": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0, "turns": 0},
        "session_totals": {},
    }

def save_log(data):
    with open(LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)

def load_alerts():
    if os.path.exists(ALERTS_PATH):
        try:
            with open(ALERTS_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_alerts(data):
    with open(ALERTS_PATH, "w") as f:
        json.dump(data, f, indent=2)

def notify(title, msg):
    escaped = msg.replace('"', '\\"').replace("'", "\\'")
    os.system(f'osascript -e \'display notification "{escaped}" with title "{title}" sound name "Ping"\'')
    debug(f"NOTIFY: {title} — {msg}")

def check_alerts(log, session_id, session_cost):
    """Zkontroluje překročení prahů a pošle notifikace."""
    alerts = load_alerts()
    today  = datetime.now().date().isoformat()

    # Týdenní součet (posledních 7 dní)
    week_start = (datetime.now().date() - timedelta(days=6)).isoformat()
    weekly_cost = sum(
        v["cost_usd"]
        for day, v in log.get("daily", {}).items()
        if day >= week_start
    )

    daily_cost = log.get("daily", {}).get(today, {}).get("cost_usd", 0.0)

    checks = [
        ("session",  f"session:{session_id}", session_cost,  LIMITS["session_cost_usd"],  "session"),
        ("daily",    f"daily:{today}",         daily_cost,    LIMITS["daily_cost_usd"],    "den"),
        ("weekly",   f"weekly:{week_start}",   weekly_cost,   LIMITS["weekly_cost_usd"],   "týden"),
    ]

    changed = False
    for kind, key, used, limit, label in checks:
        if limit <= 0:
            continue
        pct = used / limit * 100
        sent = alerts.get(key, [])

        for thr in THRESHOLDS:
            if pct >= thr and thr not in sent:
                notify(
                    f"Claude Usage — {thr}% {label}",
                    f"${used:.2f} z ${limit:.0f} ({pct:.0f}%) — {label}"
                )
                sent.append(thr)
                changed = True

        alerts[key] = sent

    if changed:
        save_alerts(alerts)

def read_transcript(path):
    """Přečte JSONL transcript, vrátí seznam deduplikovaných assistant zpráv."""
    if not os.path.exists(path):
        return []
    seen = set()
    messages = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "assistant":
                    continue
                msg = obj.get("message", {})
                msg_id = msg.get("id", "")
                if msg_id and msg_id in seen:
                    continue
                if msg_id:
                    seen.add(msg_id)
                usage = msg.get("usage", {})
                inp = usage.get("input_tokens", 0)
                out = usage.get("output_tokens", 0)
                cr  = usage.get("cache_read_input_tokens", 0)
                cw  = usage.get("cache_creation_input_tokens", 0)
                if not inp and not out:
                    continue
                ts_raw = obj.get("timestamp", "")
                try:
                    ts  = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).astimezone().isoformat(timespec="seconds")
                    day = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).astimezone().date().isoformat()
                except Exception:
                    ts  = datetime.now().isoformat(timespec="seconds")
                    day = datetime.now().date().isoformat()
                messages.append({
                    "ts": ts, "day": day,
                    "model": msg.get("model", ""),
                    "input": inp, "output": out,
                    "cache_read": cr, "cache_write": cw,
                })
    except Exception as e:
        debug(f"Chyba při čtení {path}: {e}")
    return messages


# ── Stop hook (normální provoz) ──────────────────────────────────────────────

def run_hook():
    raw = sys.stdin.read().strip()
    debug(f"RAW stdin: {raw[:300] if raw else '(prázdné)'}")
    if not raw:
        return
    try:
        event = json.loads(raw)
    except Exception as e:
        debug(f"JSON parse error: {e}")
        return

    session_id      = event.get("session_id", "unknown")
    transcript_path = event.get("transcript_path", "")
    if not transcript_path:
        debug("Chybí transcript_path")
        return

    messages = read_transcript(transcript_path)
    if not messages:
        debug("Žádné tokeny v transcript")
        return

    cur = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "turns": len(messages), "model": ""}
    for m in messages:
        cur["input"]       += m["input"]
        cur["output"]      += m["output"]
        cur["cache_read"]  += m["cache_read"]
        cur["cache_write"] += m["cache_write"]
        cur["model"]        = m["model"] or cur["model"]

    log = load_log()
    if "session_totals" not in log:
        log["session_totals"] = {}

    prev    = log["session_totals"].get(session_id, {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "turns": 0})
    d_inp   = cur["input"]       - prev["input"]
    d_out   = cur["output"]      - prev["output"]
    d_cr    = cur["cache_read"]  - prev["cache_read"]
    d_cw    = cur["cache_write"] - prev["cache_write"]
    d_turns = cur["turns"]       - prev["turns"]

    if d_inp <= 0 and d_out <= 0 and d_turns <= 0:
        debug("Žádná nová data od posledního Stop")
        return

    model = cur["model"] or "claude-sonnet-4-6"
    cost  = calc_cost(model, d_inp, d_out, d_cr, d_cw)
    today = datetime.now().date().isoformat()

    log["session_totals"][session_id] = {
        "input": cur["input"], "output": cur["output"],
        "cache_read": cur["cache_read"], "cache_write": cur["cache_write"],
        "turns": cur["turns"],
    }

    log["total"]["input"]       += d_inp
    log["total"]["output"]      += d_out
    log["total"]["cache_read"]  += d_cr
    log["total"]["cache_write"] += d_cw
    log["total"]["cost_usd"]    += cost
    log["total"]["turns"]       += d_turns

    if today not in log["daily"]:
        log["daily"][today] = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0, "turns": 0}
    log["daily"][today]["input"]       += d_inp
    log["daily"][today]["output"]      += d_out
    log["daily"][today]["cache_read"]  += d_cr
    log["daily"][today]["cache_write"] += d_cw
    log["daily"][today]["cost_usd"]    += cost
    log["daily"][today]["turns"]       += d_turns

    log["sessions"].append({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "model": model,
        "input": d_inp, "output": d_out,
        "cache_read": d_cr, "cache_write": d_cw,
        "cost_usd": cost,
    })
    if len(log["sessions"]) > 500:
        log["sessions"] = log["sessions"][-500:]

    save_log(log)

    # Celková cena aktuální session
    session_total_cost = calc_cost(
        model,
        cur["input"], cur["output"], cur["cache_read"], cur["cache_write"]
    )
    check_alerts(log, session_id, session_total_cost)
    debug(f"OK: session={session_id} delta in={d_inp} out={d_out} cost=${cost:.6f}")


# ── Rebuild z celé historie ──────────────────────────────────────────────────

def rebuild():
    print("Rebuilduji usage_log.json ze všech transcript souborů…")
    files = glob.glob(os.path.join(PROJ_DIR, "**", "*.jsonl"), recursive=True)
    print(f"Nalezeno {len(files)} JSONL souborů")

    daily = {}
    total = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0, "turns": 0}
    sessions_log   = []
    session_totals = {}

    for fpath in sorted(files):
        session_id = os.path.splitext(os.path.basename(fpath))[0]
        messages   = read_transcript(fpath)
        if not messages:
            continue

        s_inp = s_out = s_cr = s_cw = 0
        model = ""
        for m in messages:
            day   = m["day"]
            model = m["model"] or model
            cost  = calc_cost(model or "claude-sonnet-4-6", m["input"], m["output"], m["cache_read"], m["cache_write"])

            if day not in daily:
                daily[day] = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0, "turns": 0}
            daily[day]["input"]       += m["input"]
            daily[day]["output"]      += m["output"]
            daily[day]["cache_read"]  += m["cache_read"]
            daily[day]["cache_write"] += m["cache_write"]
            daily[day]["cost_usd"]    += cost
            daily[day]["turns"]       += 1

            total["input"]       += m["input"]
            total["output"]      += m["output"]
            total["cache_read"]  += m["cache_read"]
            total["cache_write"] += m["cache_write"]
            total["cost_usd"]    += cost
            total["turns"]       += 1

            s_inp += m["input"]; s_out += m["output"]
            s_cr  += m["cache_read"]; s_cw += m["cache_write"]

        session_totals[session_id] = {"input": s_inp, "output": s_out, "cache_read": s_cr, "cache_write": s_cw, "turns": len(messages)}
        s_cost = calc_cost(model or "claude-sonnet-4-6", s_inp, s_out, s_cr, s_cw)
        sessions_log.append({
            "ts": messages[-1]["ts"],
            "session_id": session_id,
            "model": model or "claude-sonnet-4-6",
            "input": s_inp, "output": s_out,
            "cache_read": s_cr, "cache_write": s_cw,
            "cost_usd": s_cost,
        })
        print(f"  {session_id[:8]}…  {len(messages)} turns  ${s_cost:.4f}")

    sessions_log = sorted(sessions_log, key=lambda x: x["ts"])[-500:]
    log = {"sessions": sessions_log, "daily": daily, "total": total, "session_totals": session_totals}
    save_log(log)

    print(f"\nHotovo.")
    print(f"  Celkem turns : {total['turns']}")
    print(f"  Celkem tokeny: {total['input']+total['output']:,}")
    print(f"  Celkem cena  : ${total['cost_usd']:.4f}")
    for day in sorted(daily)[-7:]:
        d = daily[day]
        print(f"  {day}: {d['turns']} turns, {d['input']+d['output']:,} tokenů, ${d['cost_usd']:.4f}")


if __name__ == "__main__":
    if "--rebuild" in sys.argv:
        rebuild()
    else:
        run_hook()
