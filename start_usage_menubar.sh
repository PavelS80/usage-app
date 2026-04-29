#!/bin/bash
# Spustí Claude Usage menu bar app na pozadí
# Přidej do ~/.zshrc nebo spusť ručně
pkill -f usage_menubar.py 2>/dev/null
sleep 0.3
nohup python3 /Users/pavelspacek/.claude/usage_menubar.py > /tmp/claude_usage.log 2>&1 &
echo "Claude Usage app spuštěna (PID $!)"
