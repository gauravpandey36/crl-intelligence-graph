#!/usr/bin/env python3
"""L9 — inject the companion chat + vendor-screener widgets into portal/index.html
(idempotent). Adds a 'guide' panel and a 'screen your vendors' box that call the
portal server API. Includes a cached-greeting placeholder (no autoplay, WCAG-safe)."""
from pathlib import Path

IDX = Path(__file__).resolve().parent.parent / "portal" / "index.html"
MARK = "<!--WIDGETS-->"

WIDGETS = """<!--WIDGETS-->
<style>
#guide{position:fixed;right:18px;bottom:18px;width:340px;max-width:92vw;background:#fff;
border:1px solid var(--rule);border-radius:14px;box-shadow:0 16px 40px rgba(10,30,51,.18);
font-size:14px;z-index:60;display:flex;flex-direction:column;max-height:70vh}
#guide .gh{background:var(--ink);color:var(--bg);padding:10px 14px;border-radius:14px 14px 0 0;
font-weight:700;display:flex;align-items:center;gap:8px}
#guide .gb{padding:12px;overflow:auto;flex:1}
#guide .m{margin:0 0 10px;line-height:1.5}#guide .m.u{text-align:right}
#guide .m.u span{background:var(--ink);color:var(--bg);padding:6px 10px;border-radius:12px 12px 2px 12px;display:inline-block}
#guide .m.g span{background:#f3eedf;padding:6px 10px;border-radius:12px 12px 12px 2px;display:inline-block}
#guide .gc{display:flex;gap:6px;padding:10px;border-top:1px solid var(--rule)}
#guide input{flex:1;border:1px solid var(--rule);border-radius:8px;padding:8px;font:inherit}
#guide button{border:1px solid var(--ink);background:var(--ink);color:var(--bg);border-radius:8px;padding:8px 12px;cursor:pointer}
#screen textarea{width:100%;min-height:72px;border:1px solid var(--rule);border-radius:8px;padding:8px;font:inherit}
.hit{border-left:3px solid var(--amber);padding:4px 10px;margin:6px 0;background:#fff}
.clean{color:var(--muted);font-style:italic;padding:4px 10px}
.greet{display:flex;gap:12px;align-items:center;background:#fff;border:1px solid var(--rule);border-radius:12px;padding:12px;margin:14px 0}
.greet .av{width:54px;height:54px;border-radius:50%;background:linear-gradient(135deg,var(--ink),var(--amber));color:#fff;display:grid;place-items:center;font-weight:700;flex-shrink:0}
</style>

<div class="greet"><div class="av">CRL</div><div><strong>Your guide is here.</strong><br>
<span style="color:var(--muted)">Ask me anything about the graph, or screen your own vendors against FDA watch lists — free, nothing leaves your browser.</span></div></div>

<div class="sec" id="screen"><h2>Screen your vendors against FDA watch lists</h2>
<p style="color:var(--muted);font-size:13px">Paste your CDMO / vendor names (one per line). Educational, not regulatory advice.</p>
<textarea id="vlist" placeholder="Acme Pharma Ltd&#10;Contoso CDMO Inc"></textarea>
<div style="margin-top:8px"><button onclick="runScreen()">Screen</button></div>
<div id="sresult"></div></div>

<div id="guide">
  <div class="gh">Guide</div>
  <div class="gb" id="gbody"><p class="m g"><span>…</span></p></div>
  <div class="gc"><input id="gin" placeholder="ask about the graph…"
    onkeydown="if(event.key==='Enter')gsend()"><button onclick="gsend()">Send</button></div>
</div>

<script>
const SID='s'+Math.random().toString(36).slice(2);
function esc(s){return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function gadd(who,t){const b=document.getElementById('gbody');
 b.insertAdjacentHTML('beforeend',`<p class="m ${who}"><span>${esc(t)}</span></p>`);b.scrollTop=b.scrollHeight;}
async function gchat(msg){const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({session:SID,msg})});return (await r.json());}
async function gsend(){const i=document.getElementById('gin');const m=i.value.trim();if(!m)return;
 i.value='';gadd('u',m);gadd('g','…');const d=await gchat(m);
 const b=document.getElementById('gbody');b.lastElementChild.remove();gadd('g',d.text||'(…)');}
(async()=>{const b=document.getElementById('gbody');b.innerHTML='';const d=await gchat('');gadd('g',d.text||'Hello.');})();
async function runScreen(){
 const names=document.getElementById('vlist').value.split('\\n').map(s=>s.trim()).filter(Boolean);
 if(!names.length)return;
 const out=document.getElementById('sresult');out.innerHTML='<p class="clean">screening…</p>';
 const r=await fetch('/api/screen',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({vendors:names})});
 const d=await r.json();let h='';
 (d.results||[]).forEach(v=>{
  if(v.status==='FLAGGED'){h+=`<div class="hit"><strong>${esc(v.vendor)}</strong>`;
   v.hits.forEach(x=>{h+=`<br>• ${esc(x.list)} — ${Math.round(x.confidence*100)}% ${esc(x.level)} (matched '${esc(x.matched_firm||'')}', src ${esc(x.source||'')})`;});
   h+='</div>';}
  else h+=`<div class="clean">${esc(v.vendor)} — no public watch-list match (not a clean bill — FDA does not inspect everyone)</div>`;});
 if(d.exposure)h+=`<p style="margin-top:8px"><strong>Exposure index: ${d.exposure.exposure_index}</strong> (${esc(d.exposure.band)}). Descriptive, traceable, not predictive of FDA action.</p>`;
 out.innerHTML=h||'<p class="clean">no vendors</p>';
}
</script>
"""


def main():
    txt = IDX.read_text()
    if MARK in txt:
        print("[L9] widgets already present"); return
    txt = txt.replace("</div></body></html>", "</div>" + WIDGETS + "</body></html>")
    IDX.write_text(txt)
    print(f"[L9] injected companion + screener widgets into {IDX}")


if __name__ == "__main__":
    main()
