#!/usr/bin/env python3
"""
Claude Usage Dashboard — lokální HTTP server na portu 7823
Spusť: python3 ~/.claude/usage_server.py
"""
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import date

LOG_PATH = os.path.expanduser("~/.claude/usage_log.json")

HTML = r"""<!DOCTYPE html>
<html lang="cs">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Claude Usage</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#09090b;--surface:#18181b;--surface2:#27272a;--border:#3f3f46;
  --text:#fafafa;--muted:#a1a1aa;--muted2:#71717a;
  --green:#4ade80;--blue:#60a5fa;--purple:#c084fc;--orange:#fb923c;--red:#f87171;
}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh;padding:32px 24px;}
h1{font-size:1.4rem;font-weight:700;letter-spacing:-0.02em;margin-bottom:4px;display:flex;align-items:center;gap:10px;}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.sub{color:var(--muted);font-size:0.82rem;margin-bottom:32px;}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:32px;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;}
.card-label{font-size:0.7rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted2);margin-bottom:8px;}
.card-value{font-size:1.9rem;font-weight:700;font-family:'JetBrains Mono',monospace;letter-spacing:-0.02em;}
.card-sub{font-size:0.78rem;color:var(--muted);margin-top:4px;}
.green{color:var(--green)}.blue{color:var(--blue)}.purple{color:var(--purple)}.orange{color:var(--orange)}
.section{background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:16px;}
.section-head{padding:12px 20px;background:var(--surface2);border-bottom:1px solid var(--border);font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);}
table{width:100%;border-collapse:collapse;font-size:0.83rem;}
td,th{padding:10px 20px;text-align:left;border-bottom:1px solid #ffffff08;}
tr:last-child td{border-bottom:none;}
th{font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted2);font-weight:600;}
.mono{font-family:'JetBrains Mono',monospace;font-size:0.8rem;}
.tag{display:inline-block;padding:2px 8px;border-radius:20px;font-size:0.68rem;font-weight:600;background:rgba(96,165,250,0.15);color:var(--blue);}
.updated{font-size:0.72rem;color:var(--muted2);text-align:right;margin-top:16px;}
.no-data{text-align:center;padding:48px;color:var(--muted2);}
.bar-wrap{background:var(--surface2);border-radius:4px;height:6px;margin-top:8px;overflow:hidden;}
.bar{height:100%;border-radius:4px;background:linear-gradient(90deg,var(--blue),var(--purple));transition:width 0.6s ease;}
</style>
</head>
<body>
<h1><span class="dot"></span> Claude Usage</h1>
<p class="sub">Automaticky se obnovuje každých 10 sekund &nbsp;·&nbsp; <span id="last-update"></span></p>

<div id="app"><div class="no-data">Načítám data…</div></div>

<script>
function fmt(n){
  if(n>=1e6) return (n/1e6).toFixed(2)+'M';
  if(n>=1e3) return (n/1e3).toFixed(1)+'k';
  return String(n||0);
}
function fmtCost(c){return '$'+(c||0).toFixed(4);}
function fmtDate(ts){
  const d=new Date(ts);
  return d.toLocaleTimeString('cs-CZ',{hour:'2-digit',minute:'2-digit'});
}

async function load(){
  try{
    const r = await fetch('/data');
    const data = await r.json();
    render(data);
    document.getElementById('last-update').textContent = 'Aktualizováno: '+new Date().toLocaleTimeString('cs-CZ');
  }catch(e){
    document.getElementById('app').innerHTML = '<div class="no-data">Žádná data — spusť Claude Code session a odpovědi se začnou zachytávat.</div>';
  }
}

function render(data){
  const today = new Date().toISOString().split('T')[0];
  const d = (data.daily||{})[today] || {};
  const t = data.total || {};
  const sessions = (data.sessions||[]).slice(-20).reverse();

  const d_cost = d.cost_usd || 0;
  const t_cost = t.cost_usd || 0;
  const d_in = d.input||0, d_out = d.output||0;
  const t_in = t.input||0, t_out = t.output||0;

  // Progress bar — denní vs celkový
  const pct = t_cost > 0 ? Math.min(100, Math.round(d_cost/t_cost*100)) : 0;

  let html = `
  <div class="cards">
    <div class="card">
      <div class="card-label">Dnes — cena</div>
      <div class="card-value green">${fmtCost(d_cost)}</div>
      <div class="card-sub">${d.turns||0} turns</div>
      <div class="bar-wrap"><div class="bar" style="width:${pct}%"></div></div>
    </div>
    <div class="card">
      <div class="card-label">Dnes — tokeny</div>
      <div class="card-value blue">${fmt(d_in+d_out)}</div>
      <div class="card-sub">↑ ${fmt(d_in)} in &nbsp; ↓ ${fmt(d_out)} out</div>
    </div>
    <div class="card">
      <div class="card-label">Celkem — cena</div>
      <div class="card-value purple">${fmtCost(t_cost)}</div>
      <div class="card-sub">${t.turns||0} turns celkem</div>
    </div>
    <div class="card">
      <div class="card-label">Celkem — tokeny</div>
      <div class="card-value orange">${fmt(t_in+t_out)}</div>
      <div class="card-sub">↑ ${fmt(t_in)} in &nbsp; ↓ ${fmt(t_out)} out</div>
    </div>
  </div>`;

  // Denní přehled
  const days = Object.entries(data.daily||{}).sort((a,b)=>b[0].localeCompare(a[0])).slice(0,7);
  if(days.length){
    html += `<div class="section">
      <div class="section-head">Přehled po dnech</div>
      <table>
        <tr><th>Datum</th><th>Turns</th><th>Input</th><th>Output</th><th>Cena</th></tr>
        ${days.map(([day,v])=>`
        <tr>
          <td class="mono">${day}${day===today?' <span class="tag">dnes</span>':''}</td>
          <td>${v.turns||0}</td>
          <td class="mono">${fmt(v.input||0)}</td>
          <td class="mono">${fmt(v.output||0)}</td>
          <td class="mono green">${fmtCost(v.cost_usd||0)}</td>
        </tr>`).join('')}
      </table>
    </div>`;
  }

  // Posledních 20 sessions
  if(sessions.length){
    html += `<div class="section">
      <div class="section-head">Posledních ${sessions.length} turns</div>
      <table>
        <tr><th>Čas</th><th>Model</th><th>Input</th><th>Output</th><th>Cache read</th><th>Cena</th></tr>
        ${sessions.map(s=>`
        <tr>
          <td class="mono muted2">${s.ts?s.ts.split('T')[1]?.slice(0,8):'-'}</td>
          <td><span class="tag">${s.model||'sonnet'}</span></td>
          <td class="mono">${fmt(s.input||0)}</td>
          <td class="mono">${fmt(s.output||0)}</td>
          <td class="mono" style="color:var(--muted)">${fmt(s.cache_read||0)}</td>
          <td class="mono green">${fmtCost(s.cost_usd||0)}</td>
        </tr>`).join('')}
      </table>
    </div>`;
  }

  if(!days.length && !sessions.length){
    html += '<div class="no-data">Žádná data ještě — čekej na první Claude odpověď po instalaci hooku.</div>';
  }

  document.getElementById('app').innerHTML = html;
}

load();
setInterval(load, 10000);
</script>
</body>
</html>"""

def load_data():
    if not os.path.exists(LOG_PATH):
        return {"sessions": [], "daily": {}, "total": {}}
    with open(LOG_PATH) as f:
        return json.load(f)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/data":
            data = json.dumps(load_data()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        else:
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *args):
        pass  # tiché logování

if __name__ == "__main__":
    port = 7823
    server = HTTPServer(("localhost", port), Handler)
    print(f"Claude Usage Dashboard běží na http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Zastaven.")
