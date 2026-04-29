#!/usr/bin/env python3
"""
Claude Code stop hook — zachytí usage data a zapíše do ~/.claude/usage_log.json
Spouštěno automaticky po každé odpovědi.
"""
import sys
import json
import os
from datetime import datetime, date

LOG_PATH = os.path.expanduser("~/.claude/usage_log.json")

def load_log():
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"sessions": [], "daily": {}, "total": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0, "turns": 0}}

def save_log(data):
    with open(LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)

DEBUG_LOG = os.path.expanduser("~/.claude/usage_debug.log")

def debug(msg):
    with open(DEBUG_LOG, "a") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")

def main():
    raw = sys.stdin.read().strip()
    debug(f"RAW stdin: {raw[:500] if raw else '(prázdné)'}")
    if not raw:
        return

    try:
        event = json.loads(raw)
    except Exception as e:
        debug(f"JSON parse error: {e}")
        return

    usage = event.get("usage", {})
    cost = event.get("costUSD") or event.get("cost_usd") or 0.0
    session_id = event.get("session_id", "unknown")
    model = event.get("model", "")

    input_tokens  = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_read    = usage.get("cache_read_input_tokens", 0)
    cache_write   = usage.get("cache_creation_input_tokens", 0)

    # Pokud nejsou tokeny v usage, zkus přímo v eventu
    if not input_tokens:
        input_tokens  = event.get("input_tokens", 0)
        output_tokens = event.get("output_tokens", 0)
        cache_read    = event.get("cache_read_input_tokens", 0)
        cache_write   = event.get("cache_creation_input_tokens", 0)

    if not input_tokens and not output_tokens and not cost:
        return  # nic k zaznamenání

    log = load_log()
    today = date.today().isoformat()

    # Celkový součet
    log["total"]["input"]       += input_tokens
    log["total"]["output"]      += output_tokens
    log["total"]["cache_read"]  += cache_read
    log["total"]["cache_write"] += cache_write
    log["total"]["cost_usd"]    += cost
    log["total"]["turns"]       += 1

    # Denní součet
    if today not in log["daily"]:
        log["daily"][today] = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0, "turns": 0}
    log["daily"][today]["input"]       += input_tokens
    log["daily"][today]["output"]      += output_tokens
    log["daily"][today]["cache_read"]  += cache_read
    log["daily"][today]["cache_write"] += cache_write
    log["daily"][today]["cost_usd"]    += cost
    log["daily"][today]["turns"]       += 1

    # Záznam session
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "model": model,
        "input": input_tokens,
        "output": output_tokens,
        "cache_read": cache_read,
        "cache_write": cache_write,
        "cost_usd": cost,
    }
    log["sessions"].append(entry)
    # Drž jen posledních 500 záznamů
    if len(log["sessions"]) > 500:
        log["sessions"] = log["sessions"][-500:]

    save_log(log)

if __name__ == "__main__":
    main()
