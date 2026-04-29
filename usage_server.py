#!/usr/bin/env python3
"""
Claude Usage Dashboard — lokální HTTP server na portu 7823
Spusť: python3 ~/.claude/usage_server.py
"""
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import date, timedelta

LOG_PATH = os.path.expanduser("~/.claude/usage_log.json")

LIMITS = {
    "daily_cost_usd":   20.0,
    "weekly_cost_usd": 100.0,
    "session_cost_usd": 10.0,
}

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
  --green:#4ade80;--blue:#60a5fa;--purple:#c084fc;--orange:#fb923c;--red:#f87171;--yellow:#fbbf24;
}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh;padding:32px 24px;max-width:1100px;margin:0 auto;}
h1{font-size:1.4rem;font-weight:700;letter-spacing:-0.02em;margin-bottom:4px;display:flex;align-items:center;gap:10px;}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.sub{color:var(--muted);font-size:0.82rem;margin-bottom:28px;}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-bottom:24px;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;}
.card-label{font-size:0.7rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted2);margin-bottom:8px;}
.card-value{font-size:1.9rem;font-weight:700;font-family:'JetBrains Mono',monospace;letter-spacing:-0.02em;}
.card-sub{font-size:0.78rem;color:var(--muted);margin-top:4px;}
.green{color:var(--green)}.blue{color:var(--blue)}.purple{color:var(--purple)}.orange{color:var(--orange)}.red{color:var(--red)}.yellow{color:var(--yellow)}

/* Progress bar */
.limit-block{margin-top:12px;}
.limit-row{display:flex;justify-content:space-between;font-size:0.72rem;color:var(--muted);margin-bottom:5px;}
.limit-row strong{color:var(--text);}
.bar-wrap{background:var(--surface2);border-radius:4px;height:7px;overflow:hidden;}
.bar{height:100%;border-radius:4px;transition:width 0.6s ease;}
.bar-ok    {background:linear-gradient(90deg,#3b82f6,#60a5fa);}
.bar-warn  {background:linear-gradient(90deg,#f59e0b,#fbbf24);}
.bar-danger{background:linear-gradient(90deg,#ef4444,#f87171);}
.thresholds{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap;}
.thr{font-size:0.65rem;padding:2px 7px;border-radius:20px;font-weight:600;border:1px solid;}
.thr-ok    {border-color:#3f3f46;color:var(--muted2);}
.thr-active{border-color:#f59e0b;color:#fbbf24;background:rgba(251,191,36,0.1);}
.thr-hit   {border-color:#ef4444;color:#f87171;background:rgba(239,68,68,0.1);}

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
</style>
</head>
<body>
<h1><span class="dot"></span> Claude Usage</h1>
<p class="sub">Automaticky se obnovuje každých 10 sekund &nbsp;·&nbsp; <span id="last-update"></span></p>
<div id="app"><div class="no-data">Načítám data…</div></div>

<script>
const LIMITS = {daily:20, weekly:100, session:10};
const THRESHOLDS = [30,50,75,90];

function fmt(n){
  if(n>=1e6) return (n/1e6).toFixed(2)+'M';
  if(n>=1e3) return (n/1e3).toFixed(1)+'k';
  return String(n||0);
}
function fmtCost(c){return '$'+(c||0).toFixed(4);}
function fmtCost2(c){return '$'+(c||0).toFixed(2);}

function barClass(pct){
  if(pct>=90) return 'bar-danger';
  if(pct>=50) return 'bar-warn';
  return 'bar-ok';
}

function limitBlock(used, limit, label){
  const pct = limit>0 ? Math.min(100, used/limit*100) : 0;
  const cls = barClass(pct);
  const thrHtml = THRESHOLDS.map(t=>{
    let c = 'thr-ok';
    if(pct>=t) c = pct>=90 ? 'thr-hit' : 'thr-active';
    return `<span class="thr ${c}">${t}%</span>`;
  }).join('');
  return `
    <div class="limit-block">
      <div class="limit-row">
        <span>${label}</span>
        <strong>${fmtCost2(used)} / ${fmtCost2(limit)} &nbsp;(${pct.toFixed(0)}%)</strong>
      </div>
      <div class="bar-wrap"><div class="bar ${cls}" style="width:${pct}%"></div></div>
      <div class="thresholds">${thrHtml}</div>
    </div>`;
}

function getWeekly(daily){
  const today = new Date();
  let sum = 0;
  for(let i=0;i<7;i++){
    const d = new Date(today); d.setDate(d.getDate()-i);
    const key = d.toISOString().split('T')[0];
    sum += (daily[key]||{}).cost_usd||0;
  }
  return sum;
}

function getLastSessionCost(sessions){
  if(!sessions||!sessions.length) return 0;
  // Seskup poslední session
  const last = sessions[sessions.length-1];
  const sid = last.session_id;
  let cost = 0;
  for(let i=sessions.length-1;i>=0;i--){
    if(sessions[i].session_id===sid) cost+=sessions[i].cost_usd||0;
    else break;
  }
  return cost;
}

async function load(){
  try{
    const r = await fetch('/data');
    const data = await r.json();
    render(data);
    document.getElementById('last-update').textContent='Aktualizováno: '+new Date().toLocaleTimeString('cs-CZ');
  }catch(e){
    document.getElementById('app').innerHTML='<div class="no-data">Server neodpovídá.</div>';
  }
}

function render(data){
  const today = new Date().toISOString().split('T')[0];
  const d = (data.daily||{})[today]||{};
  const t = data.total||{};
  const sessions = data.sessions||[];

  const d_cost = d.cost_usd||0;
  const weekly  = getWeekly(data.daily||{});
  const s_cost  = getLastSessionCost(sessions);

  let html = '<div class="cards">';

  // Karta: Dnes
  html += `<div class="card">
    <div class="card-label">Dnes</div>
    <div class="card-value ${d_cost/LIMITS.daily>=0.9?'red':d_cost/LIMITS.daily>=0.5?'yellow':'green'}">${fmtCost2(d_cost)}</div>
    <div class="card-sub">${d.turns||0} turns &nbsp;·&nbsp; ${fmt((d.input||0)+(d.output||0))} tokenů</div>
    ${limitBlock(d_cost, LIMITS.daily, 'Denní limit')}
  </div>`;

  // Karta: Týden
  html += `<div class="card">
    <div class="card-label">Tento týden</div>
    <div class="card-value ${weekly/LIMITS.weekly>=0.9?'red':weekly/LIMITS.weekly>=0.5?'yellow':'blue'}">${fmtCost2(weekly)}</div>
    <div class="card-sub">Limit ${fmtCost2(LIMITS.weekly)} / týden</div>
    ${limitBlock(weekly, LIMITS.weekly, 'Týdenní limit')}
  </div>`;

  // Karta: Session
  html += `<div class="card">
    <div class="card-label">Aktuální session</div>
    <div class="card-value ${s_cost/LIMITS.session>=0.9?'red':s_cost/LIMITS.session>=0.5?'yellow':'purple'}">${fmtCost2(s_cost)}</div>
    <div class="card-sub">Limit ${fmtCost2(LIMITS.session)} / session</div>
    ${limitBlock(s_cost, LIMITS.session, 'Session limit')}
  </div>`;

  // Karta: Celkem
  html += `<div class="card">
    <div class="card-label">Celkem</div>
    <div class="card-value orange">${fmtCost2(t.cost_usd||0)}</div>
    <div class="card-sub">${t.turns||0} turns &nbsp;·&nbsp; ${fmt((t.input||0)+(t.output||0))} tokenů</div>
  </div>`;

  html += '</div>';

  // Přehled po dnech
  const days = Object.entries(data.daily||{}).sort((a,b)=>b[0].localeCompare(a[0])).slice(0,14);
  if(days.length){
    html += `<div class="section">
      <div class="section-head">Přehled po dnech (posledních 14)</div>
      <table>
        <tr><th>Datum</th><th>Turns</th><th>Input</th><th>Output</th><th>Cache read</th><th>Cena</th><th>% denního limitu</th></tr>
        ${days.map(([day,v])=>{
          const pct=Math.min(100,(v.cost_usd||0)/LIMITS.daily*100);
          const cls=pct>=90?'red':pct>=50?'yellow':'green';
          return `<tr>
            <td class="mono">${day}${day===today?' <span class="tag">dnes</span>':''}</td>
            <td>${v.turns||0}</td>
            <td class="mono">${fmt(v.input||0)}</td>
            <td class="mono">${fmt(v.output||0)}</td>
            <td class="mono" style="color:var(--muted)">${fmt(v.cache_read||0)}</td>
            <td class="mono ${cls}">${fmtCost(v.cost_usd||0)}</td>
            <td>
              <div class="bar-wrap" style="width:120px">
                <div class="bar ${barClass(pct)}" style="width:${pct}%"></div>
              </div>
              <span style="font-size:0.7rem;color:var(--muted)">${pct.toFixed(0)}%</span>
            </td>
          </tr>`;
        }).join('')}
      </table>
    </div>`;
  }

  // Posledních 20 turns
  const recent = sessions.slice(-20).reverse();
  if(recent.length){
    html += `<div class="section">
      <div class="section-head">Posledních ${recent.length} turns</div>
      <table>
        <tr><th>Čas</th><th>Session</th><th>Model</th><th>Input</th><th>Output</th><th>Cache read</th><th>Cena</th></tr>
        ${recent.map(s=>`<tr>
          <td class="mono" style="color:var(--muted)">${(s.ts||'').split('T')[1]?.slice(0,8)||'-'}</td>
          <td class="mono" style="color:var(--muted2);font-size:0.7rem">${(s.session_id||'').slice(0,8)}…</td>
          <td><span class="tag">${s.model||'sonnet'}</span></td>
          <td class="mono">${fmt(s.input||0)}</td>
          <td class="mono">${fmt(s.output||0)}</td>
          <td class="mono" style="color:var(--muted)">${fmt(s.cache_read||0)}</td>
          <td class="mono green">${fmtCost(s.cost_usd||0)}</td>
        </tr>`).join('')}
      </table>
    </div>`;
  }

  if(!days.length&&!recent.length){
    html+='<div class="no-data">Žádná data ještě.</div>';
  }

  document.getElementById('app').innerHTML=html;
}

load();
setInterval(load,10000);
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
        pass

if __name__ == "__main__":
    port = 7823
    server = HTTPServer(("localhost", port), Handler)
    print(f"Claude Usage Dashboard běží na http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Zastaven.")
