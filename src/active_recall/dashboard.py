"""Self-contained, local learning-workspace dashboard generation."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .progress import summarize
from .workspace import atomic_write, iter_records, now_iso


def _clean(value: Any) -> Any:
    """Make workspace metadata safe to serialize into a standalone HTML file."""
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    return value


def dashboard_data(workspace: Path) -> dict[str, Any]:
    """Return read-only workspace data for the local dashboard."""
    root = workspace.expanduser().resolve()
    grouped: dict[str, list[dict[str, Any]]] = {"source": [], "topic": [], "path": [], "study-session": [], "confusion-item": []}
    for path, metadata, body in iter_records(root):
        kind = str(metadata.get("kind", ""))
        if kind not in grouped:
            continue
        item = _clean(metadata)
        item["record_path"] = str(path.relative_to(root))
        item["body_preview"] = body.strip()[:400]
        grouped[kind].append(item)
    for values in grouped.values():
        values.sort(key=lambda item: (str(item.get("name") or item.get("title") or item.get("id") or "")).lower())

    source_names = {str(item.get("id")): str(item.get("title") or item.get("id")) for item in grouped["source"]}
    topic_names = {str(item.get("id")): str(item.get("name") or item.get("id")) for item in grouped["topic"]}
    path_names = {str(item.get("id")): str(item.get("name") or item.get("id")) for item in grouped["path"]}
    open_confusion = [item for item in grouped["confusion-item"] if item.get("status") == "open"]
    topic_status = Counter(str(item.get("status", "unknown")) for item in grouped["topic"])
    path_status = Counter(str(item.get("status", "unknown")) for item in grouped["path"])
    source_status = Counter(str(item.get("extraction_status", "unknown")) for item in grouped["source"])
    progress = summarize(root)
    return {
        "generated_at": now_iso(),
        "workspace_name": root.name,
        "workspace_path": str(root),
        "summary": {
            "sources": len(grouped["source"]),
            "topics": len(grouped["topic"]),
            "active_topics": topic_status.get("active", 0),
            "completed_topics": topic_status.get("completed", 0),
            "paths": len(grouped["path"]),
            "active_paths": path_status.get("active", 0),
            "sessions": progress["sessions"],
            "questions": progress["questions"],
            "open_confusion": len(open_confusion),
        },
        "progress": progress,
        "status_counts": {"topics": dict(topic_status), "paths": dict(path_status), "sources": dict(source_status)},
        "names": {"sources": source_names, "topics": topic_names, "paths": path_names},
        "records": {
            "sources": grouped["source"], "topics": grouped["topic"], "paths": grouped["path"],
            "sessions": grouped["study-session"], "confusion": grouped["confusion-item"],
        },
    }


def _page(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ — Learning dashboard</title>
<style>
:root{color-scheme:dark;--bg:#101417;--surface:#171d21;--surface2:#20282d;--ink:#edf2ef;--muted:#9dacaa;--line:#334047;--accent:#81d7b4;--accent2:#e7b979;--danger:#ee8c8c;--radius:13px;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);line-height:1.45} button,input,select{font:inherit} button{cursor:pointer} .shell{display:grid;grid-template-columns:252px 1fr;min-height:100vh} aside{padding:27px 18px;border-right:1px solid var(--line);position:sticky;top:0;height:100vh;background:#12181b} .eyebrow{color:var(--accent);font-size:.72rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase} h1{font-size:1.35rem;line-height:1.14;margin:8px 0 7px;overflow-wrap:anywhere} .path{font:12px ui-monospace,monospace;color:var(--muted);overflow-wrap:anywhere} nav{display:grid;gap:4px;margin-top:34px} nav button{color:var(--muted);background:transparent;border:0;text-align:left;padding:10px 12px;border-radius:8px;font-weight:650} nav button:hover,nav button.active{background:var(--surface2);color:var(--ink)} .aside-note{border-top:1px solid var(--line);margin-top:24px;padding-top:17px;color:var(--muted);font-size:.78rem} main{max-width:1420px;width:100%;padding:34px 40px 70px;margin:auto} .top{display:flex;align-items:start;justify-content:space-between;gap:20px;margin-bottom:27px} h2{margin:4px 0 0;font-size:1.95rem;letter-spacing:-.035em} .generated{color:var(--muted);font-size:.8rem;text-align:right} .metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px} .metric,.panel,.record{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius)} .metric{padding:17px} .metric .label{color:var(--muted);font-size:.74rem;font-weight:750;text-transform:uppercase;letter-spacing:.06em} .metric .value{font-size:2rem;font-weight:760;letter-spacing:-.05em;margin-top:5px} .panel{padding:22px;margin-top:17px} .panel h3{margin:0 0 16px;font-size:1rem} .split{display:grid;grid-template-columns:1.2fr .8fr;gap:17px} .bar-row{display:grid;grid-template-columns:120px 1fr 32px;align-items:center;gap:10px;margin:9px 0;font-size:.87rem;color:var(--muted)} .bar{height:8px;background:#2a353b;border-radius:20px;overflow:hidden} .bar i{display:block;height:100%;background:var(--accent);border-radius:inherit} .actions{display:flex;gap:10px;flex-wrap:wrap} .action{border:1px solid var(--line);background:var(--surface2);color:var(--ink);padding:8px 10px;border-radius:8px;font-size:.82rem} .action:hover{border-color:var(--accent)} .toolbar{display:grid;grid-template-columns:minmax(0,1fr) 190px;gap:10px;margin:0 0 17px} input,select{width:100%;background:var(--surface);border:1px solid var(--line);border-radius:9px;padding:11px 12px;color:var(--ink)} .list{display:grid;gap:10px} .record{padding:16px 17px} .record-top{display:flex;align-items:start;justify-content:space-between;gap:12px} .record h3{font-size:1rem;margin:0;overflow-wrap:anywhere} .meta{color:var(--muted);font-size:.8rem;margin-top:6px;overflow-wrap:anywhere} .tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px} .tag{font-size:.74rem;background:#263238;color:#c9d4d0;padding:3px 7px;border-radius:20px;max-width:100%;overflow-wrap:anywhere} .status{font-size:.72rem;font-weight:800;text-transform:uppercase;padding:4px 7px;border-radius:20px;background:#24463a;color:#a6e6cb;white-space:nowrap} .status.completed{background:#24463a} .status.open,.status.incorrect{background:#532c31;color:#ffbdc0} .status.archived{background:#303a40;color:#b7c2c6} .preview{margin:12px 0 0;border-top:1px solid var(--line);padding-top:11px;color:var(--muted);font-size:.83rem;white-space:pre-wrap} .empty{padding:44px 20px;text-align:center;color:var(--muted);border:1px dashed var(--line);border-radius:var(--radius)} .hidden{display:none!important} .notice{padding:12px 14px;background:#1c302c;border:1px solid #31594c;color:#b8edd6;border-radius:9px;margin:0 0 16px;font-size:.86rem} @media(max-width:820px){.shell{display:block} aside{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)} nav{grid-template-columns:repeat(3,1fr);margin-top:15px} main{padding:23px 16px} .metrics{grid-template-columns:repeat(2,minmax(0,1fr))} .split{grid-template-columns:1fr} .top{display:block} .generated{text-align:left;margin-top:10px}} @media(max-width:460px){.toolbar{grid-template-columns:1fr} nav{grid-template-columns:repeat(2,1fr)}}
</style>
</head><body><div class="shell"><aside><div class="eyebrow">Local learning workspace</div><h1 id="workspaceName"></h1><div class="path" id="workspacePath"></div><nav><button class="active" data-view="overview">Overview</button><button data-view="topics">Topics</button><button data-view="paths">Learning paths</button><button data-view="sources">Content</button><button data-view="confusion">Confusion</button><button data-view="sessions">Sessions</button></nav><div class="aside-note">Open this file directly. It contains a read-only snapshot of workspace Markdown records. Regenerate it after studying or editing records.</div></aside><main><div class="top"><div><div class="eyebrow" id="viewEyebrow">Workspace snapshot</div><h2 id="viewTitle">Learning overview</h2></div><div class="generated">Generated <span id="generatedAt"></span><br><button class="action" id="copySummary">Copy summary</button></div></div><section id="overview"></section><section id="records" class="hidden"><div class="toolbar"><input id="search" placeholder="Search names, IDs, objectives, paths…"><select id="filter"><option value="all">All statuses</option></select></div><div id="results" class="list"></div></section></main></div>
<script>
const DATA=__PAYLOAD__; const $=s=>document.querySelector(s); const labels={overview:'Learning overview',topics:'Topics',paths:'Learning paths',sources:'Content library',confusion:'Confusion queue',sessions:'Study sessions'}; let view='overview';
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))} function nice(v){return String(v??'').replaceAll('-',' ')} function plural(n,w){return n===1?w:w+'s'}
function status(v){return `<span class="status ${esc(v)}">${esc(nice(v||'unknown'))}</span>`} function links(ids,map){return (ids||[]).map(id=>`<span class="tag">${esc(map[id]||id)}</span>`).join('')}
function metric(label,value){return `<div class="metric"><div class="label">${label}</div><div class="value">${value}</div></div>`} function bars(counts){const entries=Object.entries(counts||{});const max=Math.max(1,...entries.map(x=>x[1]));return entries.length?entries.map(([n,v])=>`<div class="bar-row"><span>${esc(nice(n))}</span><div class="bar"><i style="width:${v/max*100}%"></i></div><b>${v}</b></div>`).join(''):'<div class="empty">No evidence yet.</div>'}
function overview(){const s=DATA.summary,p=DATA.progress; $('#overview').innerHTML=`<div class="metrics">${metric('Sources',s.sources)}${metric('Topics',s.topics)}${metric('Questions answered',s.questions)}${metric('Open confusion',s.open_confusion)}</div><div class="split"><div class="panel"><h3>Learning evidence</h3>${bars(p.evaluations)}<div class="actions"><button class="action" onclick="go('confusion')">Review ${s.open_confusion} open confusion ${plural(s.open_confusion,'item')}</button><button class="action" onclick="go('topics')">Browse ${s.active_topics} active topics</button></div></div><div class="panel"><h3>Coverage</h3>${bars({active_topics:s.active_topics,completed_topics:s.completed_topics,active_paths:s.active_paths,sessions:s.sessions})}<p class="meta">Mastery is evidence-based, not an objective score. Use source-grounded sessions and the confusion queue to decide what to study next.</p></div></div><div class="panel"><h3>Quick read</h3><div class="notice">${s.sources?`This workspace contains ${s.sources} ${plural(s.sources,'source')}, ${s.topics} ${plural(s.topics,'topic')}, and ${s.paths} ${plural(s.paths,'path')}.`:'Ingest a source, then create topics and a learning path to populate this dashboard.'}</div>${bars(DATA.status_counts.sources)}</div>`; $('#overview').classList.remove('hidden'); $('#records').classList.add('hidden')}
function record(kind,item){const title=item.name||item.title||item.id;const st=item.status||item.extraction_status||'recorded';let tags='';if(kind==='topics')tags=links(item.source_ids,DATA.names.sources)+links(item.prerequisites,DATA.names.topics)+links(item.path_ids,DATA.names.paths);if(kind==='paths')tags=links(item.topic_ids,DATA.names.topics)+links(item.source_ids,DATA.names.sources);if(kind==='sources')tags=links(item.topic_ids,DATA.names.topics)+links(item.path_ids,DATA.names.paths)+(item.extraction_engines||[]).map(x=>`<span class="tag">${esc(x)}</span>`).join('');if(kind==='confusion')tags=links([item.topic_id],DATA.names.topics)+`<span class="tag">next: ${esc(item.next_review_at||'unscheduled')}</span>`;return `<article class="record" data-status="${esc(st)}"><div class="record-top"><div><h3>${esc(title)}</h3><div class="meta"><code>${esc(item.id||'')}</code> · ${esc(item.record_path||'')}</div></div>${status(st)}</div><div class="tags">${tags}</div>${item.body_preview?`<div class="preview">${esc(item.body_preview)}</div>`:''}</article>`}
function showRecords(kind){view=kind; $('#overview').classList.add('hidden'); $('#records').classList.remove('hidden'); $('#viewTitle').textContent=labels[kind]; $('#viewEyebrow').textContent='Queryable workspace records'; const values=DATA.records[kind]||[]; const statuses=[...new Set(values.map(x=>x.status||x.extraction_status||'recorded'))].sort(); $('#filter').innerHTML='<option value="all">All statuses</option>'+statuses.map(x=>`<option value="${esc(x)}">${esc(nice(x))}</option>`).join(''); $('#search').value=''; renderRecords()}
function renderRecords(){const query=$('#search').value.trim().toLowerCase(),filter=$('#filter').value;const values=(DATA.records[view]||[]).filter(x=>{const hay=JSON.stringify(x).toLowerCase();return (!query||hay.includes(query))&&(filter==='all'||(x.status||x.extraction_status||'recorded')===filter)}); $('#results').innerHTML=values.length?values.map(x=>record(view,x)).join(''):`<div class="empty">No matching ${labels[view].toLowerCase()}.</div>`}
function go(next){document.querySelector(`[data-view="${next}"]`).click()} window.go=go; document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-view]').forEach(x=>x.classList.remove('active'));b.classList.add('active');view=b.dataset.view;$('#viewTitle').textContent=labels[view];$('#viewEyebrow').textContent=view==='overview'?'Workspace snapshot':'Queryable workspace records';view==='overview'?overview():showRecords(view)}); $('#search').oninput=renderRecords;$('#filter').onchange=renderRecords; $('#workspaceName').textContent=DATA.workspace_name;$('#workspacePath').textContent=DATA.workspace_path;$('#generatedAt').textContent=new Date(DATA.generated_at).toLocaleString();$('#copySummary').onclick=async()=>{const s=DATA.summary;const text=`${DATA.workspace_name}: ${s.topics} topics (${s.completed_topics} completed), ${s.paths} paths, ${s.questions} questions, ${s.open_confusion} open confusion items.`;try{await navigator.clipboard.writeText(text);$('#copySummary').textContent='Copied'}catch{$('#copySummary').textContent='Copy unavailable'}};overview();
</script></body></html>'''.replace("__PAYLOAD__", payload).replace("__TITLE__", data["workspace_name"])

def generate_dashboard(workspace: Path, *, output: Path | None = None) -> dict[str, str]:
    """Write a directly-openable dashboard snapshot without changing learner records."""
    root = workspace.expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(root)
    destination = (output.expanduser().resolve() if output else root / "dashboard.html")
    atomic_write(destination, _page(dashboard_data(root)))
    return {"status": "generated", "dashboard": str(destination), "workspace": str(root)}
