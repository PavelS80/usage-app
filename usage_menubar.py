#!/usr/bin/env python3
"""
Claude Usage — macOS menu bar app
Zobrazuje využití tokenů Claude Code v liště nahoře.
"""
import rumps
import json
import os
from datetime import date, datetime

LOG_PATH = os.path.expanduser("~/.claude/usage_log.json")

# Ceny za 1M tokenů (Sonnet 4.6 / Opus 4.7 — orientační)
PRICE_INPUT  = 3.0   # USD / 1M input tokenů
PRICE_OUTPUT = 15.0  # USD / 1M output tokenů
PRICE_CACHE_READ  = 0.30
PRICE_CACHE_WRITE = 3.75

def fmt_k(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)

def estimate_cost(inp, out, cr, cw):
    return (inp * PRICE_INPUT + out * PRICE_OUTPUT +
            cr * PRICE_CACHE_READ + cw * PRICE_CACHE_WRITE) / 1_000_000

def load_log():
    if not os.path.exists(LOG_PATH):
        return None
    try:
        with open(LOG_PATH) as f:
            return json.load(f)
    except Exception:
        return None


class ClaudeUsageApp(rumps.App):
    def __init__(self):
        super().__init__("≈", quit_button=None)
        self.menu = [
            rumps.MenuItem("─── Dnes ───", callback=None),
            rumps.MenuItem("Načítám…",    callback=None),
            None,
            rumps.MenuItem("─── Celkem ───", callback=None),
            rumps.MenuItem("Načítám…",       callback=None),
            None,
            rumps.MenuItem("─── Posledních 5 turns ───", callback=None),
            None,
            rumps.MenuItem("↺ Obnovit",  callback=self.refresh),
            rumps.MenuItem("🗑 Reset dat", callback=self.reset_data),
            None,
            rumps.MenuItem("Ukončit",    callback=self.quit_app),
        ]
        self.refresh(None)
        # Auto-refresh každých 30 sekund
        self._timer = rumps.Timer(self.refresh, 30)
        self._timer.start()

    def refresh(self, _):
        log = load_log()
        today = date.today().isoformat()

        if not log:
            self.title = "Claude ·"
            self.menu["Načítám…"].title = "Žádná data — čekám na první session"
            return

        # ── Dnes ──
        d = log.get("daily", {}).get(today, {})
        d_in  = d.get("input", 0)
        d_out = d.get("output", 0)
        d_cr  = d.get("cache_read", 0)
        d_cw  = d.get("cache_write", 0)
        d_cost = d.get("cost_usd") or estimate_cost(d_in, d_out, d_cr, d_cw)
        d_turns = d.get("turns", 0)

        # ── Celkem ──
        t = log.get("total", {})
        t_in   = t.get("input", 0)
        t_out  = t.get("output", 0)
        t_cr   = t.get("cache_read", 0)
        t_cw   = t.get("cache_write", 0)
        t_cost = t.get("cost_usd") or estimate_cost(t_in, t_out, t_cr, t_cw)
        t_turns = t.get("turns", 0)

        # Ikonka v liště — denní cena
        self.title = f"≈ ${d_cost:.3f}"

        # Aktualizace menu položek
        self.menu["─── Dnes ───"].title = f"─── Dnes ({today}) ───"

        today_text = (
            f"  ↑ {fmt_k(d_in)}  ↓ {fmt_k(d_out)} tokenů  •  "
            f"{d_turns} turns  •  ${d_cost:.4f}"
        )
        # Najdi první "Načítám…" a aktualizuj
        items = list(self.menu.keys())
        self._set_item(0, today_text)

        self._set_item(1, (
            f"  ↑ {fmt_k(t_in)}  ↓ {fmt_k(t_out)} tokenů  •  "
            f"{t_turns} turns  •  ${t_cost:.4f}"
        ))

        # Posledních 5 sessions
        sessions = log.get("sessions", [])[-5:]
        sessions.reverse()
        self._update_recent(sessions)

    def _set_item(self, idx, text):
        """Nastaví text n-té 'Načítám…' položky."""
        count = 0
        for key in self.menu.keys():
            item = self.menu[key]
            if hasattr(item, 'title') and (item.title.startswith("  ") or item.title == "Načítám…"):
                if count == idx:
                    item.title = text
                    return
                count += 1

    def _update_recent(self, sessions):
        # Odstraň staré session položky a přidej nové pod separátor
        pass  # rumps neumožňuje snadno dynamicky měnit sekce, necháme staticky

    def reset_data(self, _):
        response = rumps.alert(
            title="Reset dat",
            message="Opravdu chceš smazat všechna usage data?",
            ok="Smazat", cancel="Zrušit"
        )
        if response.clicked == 1:
            empty = {"sessions": [], "daily": {}, "total": {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0, "turns": 0}}
            with open(LOG_PATH, "w") as f:
                json.dump(empty, f, indent=2)
            self.title = "≈ $0.000"
            rumps.notification("Claude Usage", "", "Data smazána.")

    def quit_app(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    ClaudeUsageApp().run()
