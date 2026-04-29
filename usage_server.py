#!/usr/bin/env python3
"""
Claude Usage Dashboard — lokální HTTP server na portu 7823
Spusť: python3 ~/.claude/usage_server.py
"""
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import date, datetime, timedelta

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
  --bg:#111113;--surface:#1a1a1d;--surface2:#222226;--border:#2e2e32;
  --text:#f5f5f5;--muted:#8b8b8f;--muted2:#56565a;
  --blue:#4f9cf9;--green:#3ecf6e;--yellow:#f59e0b;--red:#ef4444;--purple:#c084fc;
  --radius:14px;
}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh;padding:40px 28px;max-width:900px;margin:0 auto;}

.header{margin-bottom:36px;}
.header h1{font-size:1.2rem;font-weight:700;letter-spacing:-0.02em;display:flex;align-items:center;gap:8px;margin-bottom:3px;}
.dot{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 2s infinite;flex-shrink:0;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
.header-sub{color:var(--muted);font-size:0.78rem;}
.badge{font-size:0.62rem;background:rgba(79,156,249,0.12);color:var(--blue);border:1px solid rgba(79,156,249,0.25);padding:1px 8px;border-radius:20px;font-weight:600;}

/* Section titles */
.section-title{font-size:0.9rem;font-weight:700;margin-bottom:18px;letter-spacing:-0.01em;}

/* Limit rows */
.limit-row{margin-bottom:24px;}
.limit-row:last-child{margin-bottom:0;}
.lr-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:7px;}
.lr-name{font-size:0.85rem;font-weight:500;}
.lr-meta{font-size:0.72rem;color:var(--muted);margin-top:2px;}
.lr-right{text-align:right;}
.lr-pct{font-size:0.85rem;font-weight:600;}
.lr-tokens{font-size:0.7rem;color:var(--muted);margin-top:2px;font-family:'JetBrains Mono',monospace;}
.c-ok{color:var(--blue)}.c-warn{color:var(--yellow)}.c-danger{color:var(--red)}.c-green{color:var(--green)}.c-purple{color:var(--purple)}.c-muted{color:var(--muted)}

/* Bar */
.bar-track{background:var(--surface2);border-radius:6px;height:8px;overflow:hidden;position:relative;}
.bar-fill{height:100%;border-radius:6px;transition:width 0.7s ease;}
.bar-ok{background:linear-gradient(90deg,#2563eb,#4f9cf9);}
.bar-warn{background:linear-gradient(90deg,#d97706,#fbbf24);}
.bar-danger{background:linear-gradient(90deg,#dc2626,#f87171);}

/* Threshold pills */
.pills{display:flex;gap:5px;margin-top:7px;}
.pill{font-size:0.63rem;padding:2px 7px;border-radius:20px;font-weight:600;border:1px solid var(--border);color:var(--muted2);}
.pill.active{border-color:rgba(245,158,11,0.5);color:var(--yellow);background:rgba(245,158,11,0.08);}
.pill.hit{border-color:rgba(239,68,68,0.5);color:var(--red);background:rgba(239,68,68,0.08);}

hr{border:none;border-top:1px solid var(--border);margin:28px 0;}

/* Cards */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:28px;}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px 18px;}
.card-lbl{font-size:0.62rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted2);margin-bottom:6px;}
.card-val{font-size:1.55rem;font-weight:700;font-family:'JetBrains Mono',monospace;letter-spacing:-0.02em;}
.card-sub{font-size:0.7rem;color:var(--muted);margin-top:3px;}

/* Table */
.tbl-wrap{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;margin-bottom:14px;}
.tbl-head{padding:10px 18px;background:var(--surface2);border-bottom:1px solid var(--border);font-size:0.68rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);}
table{width:100%;border-collapse:collapse;font-size:0.79rem;}
td,th{padding:9px 18px;text-align:left;border-bottom:1px solid #ffffff05;}
tr:last-child td{border-bottom:none;}
th{font-size:0.62rem;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted2);font-weight:600;}
.mono{font-family:'JetBrains Mono',monospace;font-size:0.77rem;}
.tag{display:inline-block;padding:2px 7px;border-radius:20px;font-size:0.63rem;font-weight:600;background:rgba(79,156,249,0.12);color:var(--blue);}
.no-data{text-align:center;padding:48px;color:var(--muted2);font-size:0.85rem;}

/* Inline bar in table */
.mini-bar{display:flex;align-items:center;gap:8px;}
.mini-track{flex:1;background:var(--surface2);border-radius:3px;height:5px;overflow:hidden;}
.mini-fill{height:100%;border-radius:3px;}
</style>
</head>
<body>

<div class="header">
  <h1><span class="dot"></span> Plan usage limits <span class="badge">Max (5×)</span></h1>
  <div class="header-sub">Obnovuje se každých 10 s &nbsp;·&nbsp; <span id="last-update"></span></div>
</div>

<div id="app"><div class="no-data">Načítám…</div></div>

<script>
// ── Limity: nastav dle svého plánu ─────────────────────────────
// Max 5x plan — přibližné limity v USD (snadněji porovnatelné)
const LIMITS = {
  session_usd:  10,    // USD / session (~5h)
  daily_usd:    20,    // USD / den
  weekly_usd:  100,    // USD / týden
};
const THRESHOLDS = [30, 50, 75, 90];

function fmt(n){
  if(!n&&n!==0) return '—';
  if(n>=1e6) return (n/1e6).toFixed(2)+'M';
  if(n>=1e3) return (n/1e3).toFixed(1)+'k';
  return String(n);
}
function fmtUSD(c,dp=2){ return '$'+(c||0).toFixed(dp); }
function barCls(p){ return p>=90?'bar-danger':p>=50?'bar-warn':'bar-ok'; }
function colorCls(p){ return p>=90?'c-danger':p>=50?'c-warn':'c-ok'; }

function pills(pct){
  return THRESHOLDS.map(t=>{
    let c=''; if(pct>=t) c=pct>=90?'hit':'active';
    return `<span class="pill ${c}">${t}%</span>`;
  }).join('');
}

function limitRow(name, meta, used_usd, limit_usd, extra_tokens){
  const pct = limit_usd>0 ? Math.min(100, used_usd/limit_usd*100) : 0;
  const pc = pct.toFixed(0);
  return `<div class="limit-row">
    <div class="lr-header">
      <div>
        <div class="lr-name">${name}</div>
        <div class="lr-meta">${meta}</div>
      </div>
      <div class="lr-right">
        <div class="lr-pct ${colorCls(pct)}">${pc}% used</div>
        <div class="lr-tokens">${fmtUSD(used_usd,4)} / ${fmtUSD(limit_usd)}</div>
        ${extra_tokens?`<div class="lr-tokens">${fmt(extra_tokens)} tokenů</div>`:''}
      </div>
    </div>
    <div class="bar-track"><div class="bar-fill ${barCls(pct)}" style="width:${pct}%"></div></div>
    <div class="pills">${pills(pct)}</div>
  </div>`;
}

// ── Výpočty z dat ────────────────────────────────────────────────
function getToday(){ return new Date().toISOString().split('T')[0]; }

function lastFriday20(){
  const now = new Date();
  const d = now.getDay(); // 0=Sun,6=Sat,5=Fri
  let back = ((d + 2) % 7); // dní zpět na pátek
  if(back===0) back=7;
  const fri = new Date(now);
  fri.setDate(now.getDate()-back);
  fri.setHours(20,0,0,0);
  if(fri > now) fri.setDate(fri.getDate()-7);
  return fri;
}

function weeklyFromDaily(daily){
  const fri = lastFriday20();
  let cost=0, tokens=0, turns=0;
  for(const [day, v] of Object.entries(daily)){
    const d = new Date(day+'T12:00:00');
    if(d >= fri){
      cost   += v.cost_usd||0;
      tokens += (v.input||0)+(v.output||0);
      turns  += v.turns||0;
    }
  }
  const nextFri = new Date(fri); nextFri.setDate(fri.getDate()+7);
  const diff = nextFri - new Date();
  const dH = Math.floor(diff/3600000);
  const dM = Math.floor((diff%3600000)/60000);
  return {cost, tokens, turns, resetStr: `Resets in ${dH}h ${dM}min (Fri 20:00)`};
}

function currentSessionData(sessions, sessionTotals){
  // Najdi nejnovější session_id z posledních entries
  if(!sessions||!sessions.length) return {cost:0, tokens:0, resetStr:'—'};
  const last = sessions[sessions.length-1];
  const sid = last.session_id;
  // Sečti všechny entries pro tuto session
  let cost=0, tokens=0;
  for(const s of sessions){
    if(s.session_id===sid){
      cost   += s.cost_usd||0;
      tokens += (s.input||0)+(s.output||0);
    }
  }
  // Reset: 5h od prvního záznamu session
  const first = sessions.find(s=>s.session_id===sid);
  if(first){
    const start = new Date(first.ts);
    const reset = new Date(start.getTime()+5*3600*1000);
    const diff  = reset - new Date();
    if(diff>0){
      const dH=Math.floor(diff/3600000), dM=Math.floor((diff%3600000)/60000);
      return {cost, tokens, resetStr:`Resets in ${dH} hr ${dM} min`};
    }
  }
  return {cost, tokens, resetStr:'Resets soon'};
}

async function load(){
  try{
    const r = await fetch('/data');
    const data = await r.json();
    render(data);
    document.getElementById('last-update').textContent='Aktualizováno '+new Date().toLocaleTimeString('cs-CZ');
  }catch(e){
    document.getElementById('app').innerHTML='<div class="no-data">Server neodpovídá.</div>';
  }
}

function render(data){
  const sessions = data.sessions||[];
  const daily    = data.daily||{};
  const total    = data.total||{};
  const today    = getToday();
  const todayD   = daily[today]||{};
  const week     = weeklyFromDaily(daily);
  const sess     = currentSessionData(sessions, data.session_totals||{});

  let html = '';

  // ── Current session ─────────────────────────────────────────
  html += `<div class="section-title">Current session</div>`;
  html += limitRow('All models', sess.resetStr, sess.cost, LIMITS.session_usd, sess.tokens);
  html += '<hr>';

  // ── Weekly limits ──────────────────────────────────────────
  html += `<div class="section-title">Weekly limits</div>`;
  html += limitRow('All models', week.resetStr, week.cost, LIMITS.weekly_usd, week.tokens);
  html += '<hr>';

  // ── Daily ──────────────────────────────────────────────────
  html += `<div class="section-title">Dnes</div>`;
  html += limitRow('All models', 'Resets at midnight', todayD.cost_usd||0, LIMITS.daily_usd, (todayD.input||0)+(todayD.output||0));
  html += '<hr>';

  // ── Summary cards ──────────────────────────────────────────
  html += `<div class="cards">
    <div class="card">
      <div class="card-lbl">Dnes — cena</div>
      <div class="card-val c-green">${fmtUSD(todayD.cost_usd||0)}</div>
      <div class="card-sub">${todayD.turns||0} turns</div>
    </div>
    <div class="card">
      <div class="card-lbl">Dnes — tokeny</div>
      <div class="card-val c-ok">${fmt((todayD.input||0)+(todayD.output||0))}</div>
      <div class="card-sub">↑${fmt(todayD.input||0)} ↓${fmt(todayD.output||0)}</div>
    </div>
    <div class="card">
      <div class="card-lbl">Týden — cena</div>
      <div class="card-val c-warn">${fmtUSD(week.cost)}</div>
      <div class="card-sub">${week.turns} turns</div>
    </div>
    <div class="card">
      <div class="card-lbl">Celkem</div>
      <div class="card-val c-muted">${fmtUSD(total.cost_usd||0)}</div>
      <div class="card-sub">${total.turns||0} turns</div>
    </div>
  </div>`;

  // ── Přehled po dnech ───────────────────────────────────────
  const days = Object.entries(daily).sort((a,b)=>b[0].localeCompare(a[0])).slice(0,14);
  if(days.length){
    const maxCost = Math.max(...days.map(([,v])=>v.cost_usd||0));
    html += `<div class="tbl-wrap">
      <div class="tbl-head">Přehled po dnech</div>
      <table>
        <tr><th>Datum</th><th>Turns</th><th>Tokeny</th><th>Cache read</th><th>Cena</th><th></th></tr>
        ${days.map(([day,v])=>{
          const cost=v.cost_usd||0;
          const pct=maxCost>0?Math.min(100,cost/LIMITS.daily_usd*100):0;
          const cls=barCls(pct);
          return `<tr>
            <td class="mono">${day}${day===today?' <span class="tag">dnes</span>':''}</td>
            <td>${v.turns||0}</td>
            <td class="mono">${fmt((v.input||0)+(v.output||0))}</td>
            <td class="mono c-muted">${fmt(v.cache_read||0)}</td>
            <td class="mono c-green">${fmtUSD(cost,4)}</td>
            <td style="width:120px">
              <div class="mini-bar">
                <div class="mini-track"><div class="mini-fill ${cls}" style="width:${pct}%"></div></div>
                <span style="font-size:0.68rem;color:var(--muted);min-width:32px;text-align:right">${pct.toFixed(0)}%</span>
              </div>
            </td>
          </tr>`;
        }).join('')}
      </table>
    </div>`;
  }

  // ── Posledních turns ───────────────────────────────────────
  const recent = sessions.slice(-25).reverse();
  if(recent.length){
    html += `<div class="tbl-wrap">
      <div class="tbl-head">Posledních ${recent.length} záznamů</div>
      <table>
        <tr><th>Čas</th><th>Session</th><th>Model</th><th>Input+Output</th><th>Cache read</th><th>Cena</th></tr>
        ${recent.map(s=>`<tr>
          <td class="mono c-muted">${(s.ts||'').split('T')[1]?.slice(0,8)||'—'}</td>
          <td class="mono" style="color:var(--muted2);font-size:0.7rem">${(s.session_id||'').slice(0,8)}…</td>
          <td><span class="tag">${(s.model||'sonnet').replace('claude-','').replace(/-4-[567]/g,'')}</span></td>
          <td class="mono">${fmt((s.input||0)+(s.output||0))}</td>
          <td class="mono c-muted">${fmt(s.cache_read||0)}</td>
          <td class="mono c-green">${fmtUSD(s.cost_usd||0,4)}</td>
        </tr>`).join('')}
      </table>
    </div>`;
  }

  if(!days.length&&!recent.length){
    html+='<div class="no-data">Žádná data.</div>';
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
        return {"sessions":[],"daily":{},"total":{}}
    with open(LOG_PATH) as f:
        return json.load(f)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/data":
            data=json.dumps(load_data()).encode()
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(data)
        else:
            body=HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
    def log_message(self,*a):pass

if __name__=="__main__":
    port=7823
    print(f"Claude Usage Dashboard: http://localhost:{port}")
    HTTPServer(("localhost",port),Handler).serve_forever()
