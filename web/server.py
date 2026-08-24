#!/usr/bin/env python3
import base64
import json
import os
import subprocess
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = "0.0.0.0"
PORT = 8080
CONTROL = "/srv/scripts/server.sh"

HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RPI Server</title>
<style>
:root{color-scheme:dark;--bg:#0f1115;--panel:#181b22;--panel2:#20242d;--border:#303642;--text:#f1f3f5;--muted:#9ba3af;--green:#35c759;--red:#ff453a;--yellow:#ffd60a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}header{padding:24px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}h1{margin:0;font-size:24px}.subtitle,#updated{color:var(--muted);font-size:13px}.subtitle{margin-top:4px}#updated{font-size:12px}main{max-width:1100px;margin:auto;padding:24px}.system-card{margin-bottom:24px}.system-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}.system-stat,.container{background:var(--panel2);border:1px solid var(--border);border-radius:10px;padding:14px}.system-stat-label{color:var(--muted);font-size:12px;margin-bottom:6px}.system-stat-value{font-size:20px;font-weight:700}.system-stat-detail,.container-info{color:var(--muted);font-size:11px;margin-top:4px}.global-actions,.actions{display:flex;gap:10px;flex-wrap:wrap}.global-actions{margin-bottom:24px}button{border:0;border-radius:9px;padding:11px 16px;color:#fff;font-weight:600;cursor:pointer;background:var(--panel2)}button:hover{filter:brightness(1.15)}button:disabled{opacity:.5;cursor:wait}.start{background:#1d8f3d}.stop{background:#b8322b}.restart{background:#a57900}.card{background:var(--panel);border:1px solid var(--border);border-radius:14px;margin-bottom:18px;overflow:hidden}.card-header{padding:18px 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border)}.card-title{font-size:18px;font-weight:700}.status{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted)}.dot{width:10px;height:10px;border-radius:50%;background:var(--muted)}.dot.running{background:var(--green);box-shadow:0 0 8px rgba(53,199,89,.6)}.dot.stopped{background:var(--red)}.dot.warning{background:var(--yellow)}.card-body{padding:18px 20px}.actions{margin-bottom:18px}.containers{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}.container-name{font-weight:600;margin-bottom:7px}.container-info{font-size:12px;line-height:1.5}.process-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.process-table{width:100%;border-collapse:collapse;font-size:13px}.process-table th{text-align:left;color:var(--muted);font-size:11px;padding:8px;border-bottom:1px solid var(--border)}.process-table td{padding:8px;border-bottom:1px solid var(--border)}.process-table td:last-child,.process-table th:last-child{text-align:right}.log{background:#090a0d;border:1px solid var(--border);border-radius:10px;padding:12px;font-family:monospace;font-size:12px;white-space:pre-wrap;max-height:180px;overflow:auto;color:#c9d1d9}footer{text-align:center;color:var(--muted);font-size:11px;padding:20px}@media(max-width:800px){.process-grid{grid-template-columns:1fr}}@media(max-width:600px){main{padding:14px}header{padding:18px}.actions,.global-actions{flex-direction:column}button{width:100%}}
</style></head><body>
<header><div><h1>RPI Server</h1><div class="subtitle">Docker stack control</div></div><div id="updated">Loading...</div></header>
<main>
<div class="global-actions"><button class="start" onclick="action('start','all')">▶ Start All</button><button class="stop" onclick="confirmAction('stop','all')">■ Stop All</button><button class="restart" onclick="confirmAction('restart','all')">↻ Restart All</button></div>
<section class="card system-card"><div class="card-header"><div class="card-title">System</div></div><div class="card-body"><div id="system" class="system-grid"><div class="system-stat"><div class="system-stat-label">Loading</div><div class="system-stat-value">—</div></div></div></div></section>
<div id="stacks"></div>
<section class="card"><div class="card-header"><div class="card-title">Processes</div></div><div class="card-body"><div class="process-grid"><div><h3>Linux Processes</h3><table class="process-table"><thead><tr><th>Process</th><th>PID</th><th>RAM</th></tr></thead><tbody id="processes"><tr><td colspan="3">Loading...</td></tr></tbody></table></div><div><h3>Activity</h3><div id="log" class="log">Ready.</div></div></div></div></section>
</main><footer>RPI Server Control</footer>
<script>
const stackNames={download:"Download Stack",arr:"ARR Stack"};
function esc(v){return String(v).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;")}
function log(m){const e=document.getElementById("log"),n=new Date().toLocaleTimeString();e.textContent=`[${n}] ${m}\n`+e.textContent}
function confirmAction(c,s){const l=s==="all"?"all stacks":s==="jdownloader"?"JDownloader":stackNames[s];if(confirm(`${c.toUpperCase()} ${l}?`))action(c,s)}
async function action(c,s){document.querySelectorAll("button").forEach(b=>b.disabled=true);log(`${c} ${s}...`);try{const r=await fetch(`/api/action?command=${encodeURIComponent(c)}&stack=${encodeURIComponent(s)}`,{method:"POST"}),d=await r.json();if(!r.ok)throw Error(d.error||"Action failed");log(d.message||`${c} ${s} completed`);await loadStatus()}catch(e){log(`ERROR: ${e.message}`)}document.querySelectorAll("button").forEach(b=>b.disabled=false)}
function uptime(s){if(s==null)return"—";const d=Math.floor(s/86400);s%=86400;const h=Math.floor(s/3600);s%=3600;const m=Math.floor(s/60);return d?`${d}d ${h}h`:h?`${h}h ${m}m`:`${m}m`}
function renderSystem(s){if(!s)return`<div class="system-stat"><div class="system-stat-label">System</div><div class="system-stat-value">Unavailable</div></div>`;const m=s.memory,d=s.disk,l=s.load;return `<div class="system-stat"><div class="system-stat-label">CPU</div><div class="system-stat-value">${s.cpu_percent==null?"—":esc(s.cpu_percent)+"%"}</div><div class="system-stat-detail">Load ${l?esc(l.map(v=>v.toFixed(2)).join(" / ")):"—"}</div></div><div class="system-stat"><div class="system-stat-label">Temperature</div><div class="system-stat-value">${s.temperature_c==null?"—":esc(s.temperature_c)+"°C"}</div><div class="system-stat-detail">CPU temperature</div></div><div class="system-stat"><div class="system-stat-label">Memory</div><div class="system-stat-value">${m?esc(m.percent)+"%":"—"}</div><div class="system-stat-detail">${m?esc(m.used_mb)+" / "+esc(m.total_mb)+" MB":"Unavailable"}</div>${m?`<div class="system-stat-detail">Available: ${esc(m.available_mb)} MB</div><div class="system-stat-detail">Cache: ${esc(m.cached_mb)} MB</div><div class="system-stat-detail">Swap: ${esc(m.swap.used_mb)} / ${esc(m.swap.total_mb)} MB (${esc(m.swap.percent)}%)</div>`:""}</div><div class="system-stat"><div class="system-stat-label">Disk</div><div class="system-stat-value">${d?esc(d.percent)+"%":"—"}</div><div class="system-stat-detail">${d?esc(d.used_gb)+" / "+esc(d.total_gb)+" GB":"Unavailable"}</div></div><div class="system-stat"><div class="system-stat-label">Uptime</div><div class="system-stat-value">${uptime(s.uptime_seconds)}</div><div class="system-stat-detail">Since last boot</div></div>`}
function renderProcesses(ps){const e=document.getElementById("processes");if(!ps||!ps.length){e.innerHTML='<tr><td colspan="3">No process information available.</td></tr>';return}e.innerHTML=ps.map(p=>`<tr><td>${esc(p.name)}</td><td>${esc(p.pid)}</td><td>${esc(p.memory_mb)} MB</td></tr>`).join("")}
function statusInfo(stack){const running=stack&&stack.status==="running",healthy=stack&&stack.healthy===true;return running&&healthy?["running","Running"]:running?["warning","Running / Attention"]:["stopped","Stopped"]}
function renderStack(name,stack){const [cls,text]=statusInfo(stack),key=name==="Download Stack"?"download":"arr";let cs="";for(const[n,c]of Object.entries((stack&&stack.containers)||{}))cs+=`<div class="container"><div class="container-name">${esc(n)}</div><div class="container-info">Status: ${esc(c.status)}<br>Health: ${esc(c.health||"none")}<br>Image: ${esc(c.image||"")}</div></div>`;if(!cs)cs='<div class="container"><div class="container-info">No containers running.</div></div>';return `<section class="card"><div class="card-header"><div class="card-title">${esc(name)}</div><div class="status"><span class="dot ${cls}"></span>${text}</div></div><div class="card-body"><div class="actions"><button class="start" onclick="action('start','${key}')">▶ Start</button><button class="stop" onclick="confirmAction('stop','${key}')">■ Stop</button><button class="restart" onclick="confirmAction('restart','${key}')">↻ Restart</button></div><div class="containers">${cs}</div></div></section>`}
function renderJDownloader(stack){const c=(stack&&stack.containers&&stack.containers.jdownloader)||null;const running=c&&c.status==="running";const cls=running?"running":"stopped",text=running?"Running":"Stopped";return `<section class="card"><div class="card-header"><div class="card-title">JDownloader</div><div class="status"><span class="dot ${cls}"></span>${text}</div></div><div class="card-body"><div class="actions"><button class="start" onclick="action('start','jdownloader')">▶ Start</button><button class="stop" onclick="confirmAction('stop','jdownloader')">■ Stop</button><button class="restart" onclick="confirmAction('restart','jdownloader')">↻ Restart</button></div><div class="containers"><div class="container"><div class="container-name">jdownloader</div><div class="container-info">Status: ${c?esc(c.status):"not created"}<br>Health: ${c?esc(c.health||"none"):"none"}<br>Image: ${c?esc(c.image||""):"jlesage/jdownloader-2:latest"}</div></div></div></div></section>`}
async function loadStatus(){try{const r=await fetch("/api/status",{cache:"no-store"}),d=await r.json();if(!r.ok)throw Error(d.error||"Status request failed");document.getElementById("system").innerHTML=renderSystem(d.system);renderProcesses(d.processes);document.getElementById("stacks").innerHTML=renderStack(stackNames.download,d.download)+renderJDownloader(d.download)+renderStack(stackNames.arr,d.arr);document.getElementById("updated").textContent="Updated "+new Date().toLocaleTimeString()}catch(e){document.getElementById("updated").textContent="Status error";log(`ERROR: ${e.message}`)}}
loadStatus();setInterval(loadStatus,5000);
</script></body></html>'''

def run_control(command, stack):
    if command not in {"start", "stop", "restart"}:
        raise ValueError("Invalid command")
    if stack not in {"download", "arr", "jdownloader", "all"}:
        raise ValueError("Invalid stack")
    result = subprocess.run([CONTROL, command, stack], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180)
    if result.returncode != 0:
        raise RuntimeError(result.stdout.strip() or "Command failed")
    return result.stdout.strip()

def _read_int(path):
    try: return int(Path(path).read_text().strip())
    except (OSError, ValueError): return None

def get_system_stats():
    s={}
    t=_read_int("/sys/class/thermal/thermal_zone0/temp");s["temperature_c"]=round(t/1000,1) if t is not None else None
    try:
        v=list(map(int,Path("/proc/stat").read_text().splitlines()[0].split()[1:]));idle=v[3]+(v[4] if len(v)>4 else 0);total=sum(v);prev=getattr(get_system_stats,"_cpu_sample",None);get_system_stats._cpu_sample=(total,idle)
        s["cpu_percent"]=round(100*(total-prev[0]-(idle-prev[1]))/(total-prev[0]),1) if prev and total>prev[0] else None
    except (OSError,ValueError,IndexError): s["cpu_percent"]=None
    try:
        mem={k:int(v.split()[0]) for k,v in (line.split(":",1) for line in Path("/proc/meminfo").read_text().splitlines())};total=mem["MemTotal"];avail=mem["MemAvailable"];used=total-avail;cached=max(mem.get("Cached",0)+mem.get("SReclaimable",0)-mem.get("Shmem",0),0);st=mem.get("SwapTotal",0);sf=mem.get("SwapFree",0);su=st-sf
        s["memory"]={"used_mb":round(used/1024,1),"total_mb":round(total/1024,1),"available_mb":round(avail/1024,1),"cached_mb":round(cached/1024,1),"percent":round(100*used/total,1),"swap":{"used_mb":round(su/1024,1),"total_mb":round(st/1024,1),"percent":round(100*su/st,1) if st else 0.0}}
    except (OSError,ValueError,KeyError,ZeroDivisionError): s["memory"]=None
    try:s["load"]=[float(x) for x in Path("/proc/loadavg").read_text().split()[:3]]
    except (OSError,ValueError,IndexError):s["load"]=None
    try:s["uptime_seconds"]=int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError,ValueError,IndexError):s["uptime_seconds"]=None
    try:
        u=os.statvfs("/");total=u.f_blocks*u.f_frsize;free=u.f_bavail*u.f_frsize;used=total-free;s["disk"]={"used_gb":round(used/1024**3,1),"total_gb":round(total/1024**3,1),"percent":round(100*used/total,1) if total else 0.0}
    except OSError:s["disk"]=None
    return s

def get_process_stats(limit=15):
    out=[]
    try:page=os.sysconf("SC_PAGE_SIZE")
    except OSError:return []
    for p in os.listdir("/proc"):
        if not p.isdigit():continue
        try:
            stat=Path(f"/proc/{p}/stat").read_text();close=stat.rfind(")")
            if close<0:continue
            fields=stat[close+2:].split();rss=int(fields[21])*page/1024/1024;name=stat[stat.find("(")+1:close]
            out.append({"pid":int(p),"name":name,"memory_mb":round(rss,1)})
        except (OSError,ValueError,IndexError):continue
    out.sort(key=lambda x:x["memory_mb"],reverse=True);return out[:limit]

def get_status():
    r=subprocess.run([CONTROL,"status","--json"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=30)
    if r.returncode!=0:raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "Status failed")
    d=json.loads(r.stdout);d["system"]=get_system_stats();d["processes"]=get_process_stats();return d

def authorized(h):
    user=os.environ.get("RPI_UI_USER","");pw=os.environ.get("RPI_UI_PASSWORD","")
    if not user or not pw:return False
    raw=h.headers.get("Authorization","")
    if not raw.startswith("Basic "):return False
    try:u,p=base64.b64decode(raw[6:],validate=True).decode().split(":",1)
    except Exception:return False
    return u==user and p==pw

def require_auth(h):
    if authorized(h):return True
    h.send_response(401);h.send_header("WWW-Authenticate",'Basic realm="RPI Server"');h.send_header("Content-Type","application/json");h.send_header("Content-Length","0");h.end_headers();return False

class Handler(BaseHTTPRequestHandler):
    def send_json(self,data,status=200):
        payload=json.dumps(data).encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(payload)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(payload)
    def do_GET(self):
        if not require_auth(self):return
        path=urllib.parse.urlparse(self.path).path
        if path=="/":
            p=HTML.encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(p)));self.end_headers();self.wfile.write(p);return
        if path=="/api/status":
            try:self.send_json(get_status())
            except Exception as e:self.send_json({"error":str(e)},500)
            return
        self.send_json({"error":"Not found"},404)
    def do_POST(self):
        if not require_auth(self):return
        u=urllib.parse.urlparse(self.path)
        if u.path!="/api/action":self.send_json({"error":"Not found"},404);return
        q=urllib.parse.parse_qs(u.query);command=q.get("command",[None])[0];stack=q.get("stack",[None])[0]
        try:self.send_json({"ok":True,"message":run_control(command,stack)})
        except ValueError as e:self.send_json({"error":str(e)},400)
        except Exception as e:self.send_json({"error":str(e)},500)
    def log_message(self,fmt,*args):print("%s - %s"%(self.address_string(),fmt%args))

if __name__=="__main__":
    if not os.path.exists(CONTROL):raise SystemExit(f"Control script not found: {CONTROL}")
    print(f"RPI Server UI listening on http://{HOST}:{PORT}");ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
