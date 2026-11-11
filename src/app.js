const COLORS = {programming:'var(--cyan)', economics:'var(--lime)', design:'var(--pink)', marketing:'var(--amber)', science:'var(--violet)', world:'var(--blue)'};
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let busyJob = null;

function toast(msg){ const t=$('toast'); t.textContent=msg; t.hidden=false; clearTimeout(toast.h); toast.h=setTimeout(()=>t.hidden=true,6000); }
async function api(path, body){
  const opt = body===undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)};
  const r = await fetch(path, opt); const j = await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(j.error || ('HTTP '+r.status));
  return j;
}

async function loadStatus(){
  try{
    const s = await api('/api/status');
    $('busy').textContent = s.busy ? 'працює' + (s.queued ? ' (+'+s.queued+')' : '') : 'вільний';
    $('dot').className = 'dot' + (s.busy ? ' busy' : '');
    $('reportTime').textContent = s.report_time || 'немає';
    $('lastFetch').textContent = s.last_fetch ? s.last_fetch.slice(0,16).replace('T',' ') : '—';
    const items = [['Усього', s.total, 'var(--text)'], ...Object.entries(s.categories).map(([c,n]) => [c, n, COLORS[c]])];
    $('stats').innerHTML = items.map(([l,n,c]) => `<div class="stat" style="--c:${c}"><div class="n">${n}</div><div class="l">${esc(l)}</div></div>`).join('');
    if(!$('model').options.length){
      $('model').innerHTML = s.models.map(m => `<option value="${esc(m)}"${m===s.default_model?' selected':''}>${esc(m)}</option>`).join('');
    }
    if(s.unclassified) $('stats').insertAdjacentHTML('beforeend', `<div class="stat" style="--c:var(--amber)"><div class="n">${s.unclassified}</div><div class="l">без категорії</div></div>`);
  }catch(e){ $('busy').textContent = 'немає зв’язку'; }
}

function renderDigest(text){
  const sections = text.split(/^## /m).slice(1);
  if(!sections.length){ $('cards').innerHTML = '<div class="empty">Дайджест порожній.</div>'; return; }
  $('cards').innerHTML = sections.map(sec => {
    const lines = sec.split('\n'); const head = lines.shift().trim();
    const cat = head.split(' ')[0].toLowerCase(); const color = COLORS[cat] || 'var(--cyan)';
    const items = []; let cur = null; const notes = [];
    for(const raw of lines){
      const line = raw.trimEnd(); if(!line.trim()) continue;
      const m = line.match(/^\d+\.\s+(.*)$/);
      if(m){ cur = {t:m[1], s:[], u:null}; items.push(cur); }
      else if(cur && /^\s*https?:\/\/\S+$/.test(line)) cur.u = line.trim();
      else if(cur) cur.s.push(line.trim());
      else notes.push(line.trim());
    }
    const body = items.map(it => {
      const title = esc(it.t).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
      const link = it.u && /^https?:\/\//.test(it.u) ? `<a href="${esc(it.u)}" target="_blank" rel="noopener noreferrer">${esc(it.u)}</a>` : '';
      return `<div class="item"><div class="t">${title}</div>${it.s.length?`<div class="s">${esc(it.s.join(' '))}</div>`:''}${link}</div>`;
    }).join('') || '<div class="empty">Немає новин.</div>';
    const note = notes.length ? `<div class="note">${esc(notes.join(' ').replace(/^_+|_+$/g, ''))}</div>` : '';
    return `<article class="card" style="--c:${color}"><h3>${esc(head)}</h3>${note}${body}</article>`;
  }).join('');
}

async function loadDigest(){
  try{
    const d = await api('/api/digest');
    if(d.text) renderDigest(d.text);
    else $('cards').innerHTML = '<div class="empty">Дайджесту ще немає. Натисніть «Перебудувати дайджест».</div>';
  }catch(e){ toast(e.message); }
}

async function poll(id, onEvents, since=0){
  for(;;){
    const j = await api(`/api/jobs/${id}?since=${since}`);
    since = j.next; if(j.events.length) onEvents(j.events);
    if(j.status==='done' || j.status==='error') return j;
    await new Promise(r => setTimeout(r, 1200));
  }
}
function setBusy(on){ for(const id of ['btnAsk','btnRebuild','btnIngest']) $(id).disabled = on; }

async function refresh(ingest){
  setBusy(true); const log=$('refreshLog'); log.hidden=false; log.textContent='Виконується…';
  try{
    const {id} = await api('/api/refresh', {ingest});
    const j = await poll(id, ev => ev.forEach(e => { if(e.kind==='status') log.textContent = e.text; }));
    log.textContent = j.status==='error' ? 'Помилка: '+j.error : (j.result.log || 'Готово.');
    await Promise.all([loadDigest(), loadStatus()]);
  }catch(e){ toast(e.message); log.hidden=true; }
  finally{ setBusy(false); }
}

function addEvent(e){
  const term = $('term'); if(term.querySelector('.empty')) term.innerHTML='';
  let html;
  if(e.kind==='status') html = `<div class="ev status"><span class="tag">система</span>${esc(e.text)}</div>`;
  else if(e.role==='model') html = `<div class="ev model"><span class="tag">модель</span>${esc(e.text.trim()||'(порожньо)')}</div>`;
  else if(e.role==='tool') html = `<div class="ev tool"><span class="tag">${esc(e.tool)}</span>(${esc(e.arg)})<span class="obs">${esc((e.result||'').slice(0,600))}</span></div>`;
  else html = `<div class="ev err"><span class="tag">примітка</span>${esc(e.text||'')}</div>`;
  term.insertAdjacentHTML('beforeend', html); term.scrollTop = term.scrollHeight;
}

async function ask(question, model){
  setBusy(true); $('answer').innerHTML=''; $('term').innerHTML='<div class="empty">У черзі…</div>';
  try{
    const {id} = await api('/api/ask', {question, model});
    const j = await poll(id, ev => ev.forEach(addEvent));
    if(j.status==='error'){ $('answer').innerHTML = `<div class="answer bad"><h4>Помилка</h4>${esc(j.error)}</div>`; }
    else {
      const r = j.result; const bad = !r.finished;
      $('answer').innerHTML = `<div class="answer${bad?' bad':''}"><h4>${bad?'Агент не завершив відповідь':'Відповідь'}</h4>${esc(r.answer||'(порожньо)')}<div class="hint">${r.steps} кроків · ${r.seconds} с</div></div>`;
    }
  }catch(e){ toast(e.message); }
  finally{ setBusy(false); loadStatus(); }
}

const tabs = ['digest','agent'];
tabs.forEach(t => $('tab-'+t).addEventListener('click', () => {
  tabs.forEach(x => { $('tab-'+x).setAttribute('aria-selected', x===t); $('p-'+x).hidden = x!==t; });
}));
$('btnRebuild').onclick = () => refresh(false);
$('btnIngest').onclick = () => refresh(true);
$('askForm').addEventListener('submit', ev => { ev.preventDefault(); const q=$('q').value.trim(); if(q) ask(q, $('model').value); });
const EXAMPLES = ['Give me a summary of today\'s world news','Find news about Israel','Що нового в дизайні? Покажи заголовки.','Hi!'];
$('examples').innerHTML = EXAMPLES.map(e => `<button type="button">${esc(e)}</button>`).join('');
$('examples').addEventListener('click', e => { if(e.target.tagName==='BUTTON'){ $('q').value = e.target.textContent; $('q').focus(); } });

loadStatus(); loadDigest(); setInterval(loadStatus, 8000);
