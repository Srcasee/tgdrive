import { request } from './api.js';

function text(value) { return String(value ?? ''); }
function panel(title) { const element = document.createElement('section'); element.className = 'panel'; const heading = document.createElement('h3'); heading.textContent = title; element.appendChild(heading); return element; }
function table(headers, rows) { const el = document.createElement('table'); el.className = 'admin-table'; el.innerHTML = `<thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>`; const body = document.createElement('tbody'); for (const row of rows) { const tr = document.createElement('tr'); for (const value of row) { const td = document.createElement('td'); td.textContent = text(value); tr.appendChild(td); } body.appendChild(tr); } el.appendChild(body); return el; }
async function listSources() { const response = await request('/api/telegram/sources'); if (!response.ok) throw new Error('加载 Sources 失败'); return response.json(); }
async function setSourceEnabled(id, enabled) { const response = await request(`/api/telegram/sources/${id}/enabled`, {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled})}); if (!response.ok) { let d='更新 Source 状态失败'; try {d=(await response.json()).detail||d;} catch(_){} throw new Error(d); } return response.json(); }
async function listCategories() { const response = await request('/api/admin/categories'); if (!response.ok) throw new Error('加载分类失败'); return response.json(); }
async function createCategory(name) { const response = await request('/api/admin/categories',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})}); if(!response.ok) throw new Error(response.status===409?'分类已存在':'创建分类失败'); return response.json(); }
async function updateCategory(id,name) { const response=await request(`/api/admin/categories/${id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})}); if(!response.ok) throw new Error(response.status===404?'分类不存在':'修改分类失败'); return response.json(); }
async function removeCategory(id) { const response=await request(`/api/admin/categories/${id}`,{method:'DELETE'}); if(!response.ok) throw new Error(response.status===404?'分类不存在':'删除分类失败'); }
async function listFiles(page=1,size=50,categoryId='',sort='id',order='desc') { const params=new URLSearchParams({page:String(page),size:String(size),sort,order}); if(categoryId) params.set('category_id',String(categoryId)); const response=await request(`/catalog?${params}`); if(!response.ok) throw new Error('加载文件失败'); const payload=await response.json(); if(!payload.data) throw new Error('文件接口返回数据无效'); return payload.data; }
async function setResourceCategories(resourceId,categoryIds) { const response=await request(`/api/admin/resources/${resourceId}/categories`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({category_ids:categoryIds})}); if(!response.ok) throw new Error('保存资源分类失败'); return response.json(); }

export async function renderResources(container, section='sources') {
  container.replaceChildren();
  if(section==='sources') { const heading=document.createElement('h2'); heading.textContent='资源 / 来源'; container.appendChild(heading); return renderSources(container); }
  if(section==='files') { const heading=document.createElement('h2'); heading.textContent='资源 / 文件'; container.appendChild(heading); return renderFiles(container); }
  if(section==='categories') { const heading=document.createElement('h2'); heading.textContent='资源 / 分类'; container.appendChild(heading); return renderCategories(container); }
}

async function renderSources(container) {
  const list=document.createElement('div'); container.appendChild(list);
  try {
    const sources=await listSources(); if(!sources.length){list.textContent='暂无已启用 Source。';return;}
    const wrap=panel('来源列表');
    const rows=sources.map(source=>[source.id,source.name||source.telegram_chat_id,source.account_name,source.telegram_chat_id,source.enabled?'运行中':'已禁用',source.scan_status||'idle']);
    const tableEl=table(['ID','名称','Telegram 账号','Chat ID','状态','扫描状态','操作'], rows);
    sources.forEach((source,index)=>{ const tr=tableEl.tBodies[0].rows[index]; const td=document.createElement('td'); const button=document.createElement('button'); button.type='button'; button.textContent=source.enabled?'禁用':'启用'; button.onclick=async()=>{button.disabled=true;try{await setSourceEnabled(source.id,!source.enabled);source.enabled=!source.enabled;tr.children[4].textContent=source.enabled?'运行中':'已禁用';button.textContent=source.enabled?'禁用':'启用';}catch(e){alert(e.message);}finally{button.disabled=false;}};td.appendChild(button);tr.appendChild(td); });
    wrap.appendChild(tableEl); list.appendChild(wrap);
  } catch(error){list.textContent=error.message;}
}

function createColumnResizer(th, table, index) {
  const handle=document.createElement('span'); handle.className='column-resizer'; handle.title='拖动调整列宽';
  let startX=0,startWidth=0;
  handle.onmousedown=event=>{event.preventDefault();startX=event.clientX;startWidth=th.getBoundingClientRect().width;const move=e=>{const width=Math.max(70,startWidth+e.clientX-startX); th.style.width=`${width}px`; for(const row of table.tBodies[0]?.rows||[]) row.cells[index].style.width=`${width}px`; localStorage.setItem(`tgdrive-admin-col-${index}`,String(width));};const up=()=>{document.removeEventListener('mousemove',move);document.removeEventListener('mouseup',up);};document.addEventListener('mousemove',move);document.addEventListener('mouseup',up);};
  th.appendChild(handle);
  const saved=Number(localStorage.getItem(`tgdrive-admin-col-${index}`)); if(saved>=70) th.style.width=`${saved}px`;
}

async function renderFiles(container) {
  const controls=document.createElement('div'); controls.className='toolbar files-toolbar';
  const category=document.createElement('select'); category.setAttribute('aria-label','分类过滤'); category.appendChild(new Option('全部分类',''));
  let categories=[]; try{categories=await listCategories(); for(const item of categories) category.appendChild(new Option(item.name,item.id));}catch(error){controls.textContent=error.message;container.appendChild(controls);return;}
  const actionBar=document.createElement('div'); actionBar.className='selection-toolbar';
  const selectedLabel=document.createElement('span'); selectedLabel.className='meta';
  const classify=document.createElement('button'); classify.type='button'; classify.textContent='批量分类';
  const download=document.createElement('button'); download.type='button'; download.textContent='批量下载';
  const clear=document.createElement('button'); clear.type='button'; clear.textContent='清空选择';
  actionBar.append(selectedLabel,classify,download,clear);
  controls.append(category,actionBar); container.appendChild(controls);
  const list=document.createElement('div'); const pagination=document.createElement('div'); pagination.className='pagination'; container.append(list,pagination);
  const contextMenu=document.createElement('div'); contextMenu.className='table-context-menu'; contextMenu.hidden=true; document.body.appendChild(contextMenu);
  const selected=new Set(); let page=1; const size=50; let sort='id'; let order='desc';
  const closeMenu=()=>{contextMenu.hidden=true;}; document.addEventListener('click',closeMenu);
  function updateSelectionUI(tableEl, files) {
    const checks=[...tableEl.querySelectorAll('tbody input[type="checkbox"]')]; const selectedOnPage=files.filter(file=>selected.has(Number(file.id))).length;
    selectedLabel.textContent=`已选择 ${selected.size} 项${selectedOnPage!==files.length?'（本页 '+selectedOnPage+' 项）':''}`;
    classify.disabled=selected.size===0; download.disabled=selected.size===0; clear.disabled=selected.size===0;
    const master=tableEl.querySelector('thead input[type="checkbox"]'); if(master){master.checked=files.length>0&&selectedOnPage===files.length;master.indeterminate=selectedOnPage>0&&selectedOnPage<files.length;}
    checks.forEach(check=>{check.checked=selected.has(Number(check.dataset.id));});
  }
  function showContextMenu(event,file) {
    event.preventDefault(); event.stopPropagation(); const id=Number(file.id); if(!selected.has(id)){selected.clear();selected.add(id);} contextMenu.replaceChildren();
    for(const [label,action] of [['分类',()=>editCategories([file])],['下载',()=>downloadFiles([file])],['取消选择',()=>{selected.delete(id);refresh()}]]){const button=document.createElement('button');button.type='button';button.textContent=label;button.onclick=()=>{closeMenu();action();};contextMenu.appendChild(button);}
    contextMenu.hidden=false; contextMenu.style.left=`${Math.min(event.clientX,window.innerWidth-170)}px`; contextMenu.style.top=`${Math.min(event.clientY,window.innerHeight-150)}px`;
  }
  function editCategories(files){const value=prompt('输入分类 ID，多个分类用逗号分隔：',(files[0]?.category_ids||[]).join(','));if(value===null)return;const ids=value.split(',').map(v=>Number(v.trim())).filter(Number.isInteger);return Promise.all(files.map(async file=>{const result=await setResourceCategories(file.id,ids);file.category_ids=result.category_ids||ids;})).then(refresh).catch(error=>alert(error.message));}
  function downloadFiles(files){for(const file of files){const link=document.createElement('a');link.href=`/resources/${file.id}/download`;link.download='';document.body.appendChild(link);link.click();link.remove();}}
  classify.onclick=()=>editCategories([...selected].map(id=>currentFiles.find(file=>Number(file.id)===id)).filter(Boolean));
  download.onclick=()=>downloadFiles([...selected].map(id=>currentFiles.find(file=>Number(file.id)===id)).filter(Boolean));
  clear.onclick=()=>{selected.clear();refresh();};
  category.onchange=()=>{page=1;refresh();};
  let currentFiles=[];
  async function refresh(){ list.textContent='正在加载……'; try{const data=await listFiles(page,size,category.value,sort,order); currentFiles=data.items||[]; list.replaceChildren();
      const wrap=panel(`文件列表（${data.total||0} 项）`); const tableEl=document.createElement('table'); tableEl.className='admin-table admin-resource-table';
      const columns=[['','',false],['ID','id',true],['文件名','filename',true],['大小','size',true],['类型','mime_type',true],['来源','source_count',true],['分类','',false],['状态','',false],['操作','',false]];
      const head=document.createElement('thead'); const headRow=document.createElement('tr');
      columns.forEach(([label,key,sortable],index)=>{const th=document.createElement('th');if(index===0){const check=document.createElement('input');check.type='checkbox';check.setAttribute('aria-label','全选');check.onclick=()=>{const allOnPage=currentFiles.every(file=>selected.has(Number(file.id)));currentFiles.forEach(file=>{const id=Number(file.id);if(allOnPage)selected.delete(id);else selected.add(id);});updateSelectionUI(tableEl,currentFiles);};th.appendChild(check);}else{th.textContent=label;if(sortable){th.className='sortable';th.dataset.sort=key;th.title='点击排序';th.onclick=()=>{if(sort===key)order=order==='asc'?'desc':'asc';else{sort=key;order=key==='id'?'desc':'asc';}refresh();};if(sort===key)th.append(` ${order==='asc'?'▲':'▼'}`);}}createColumnResizer(th,tableEl,index);headRow.appendChild(th);}); head.appendChild(headRow); tableEl.appendChild(head);
      const body=document.createElement('tbody');
      currentFiles.forEach(file=>{const tr=document.createElement('tr');tr.dataset.id=file.id;tr.onclick=e=>{if(e.target.closest('button,a,input'))return;const id=Number(file.id);selected.has(id)?selected.delete(id):selected.add(id);updateSelectionUI(tableEl,currentFiles);};tr.oncontextmenu=e=>showContextMenu(e,file);
        const checkTd=document.createElement('td');const check=document.createElement('input');check.type='checkbox';check.dataset.id=file.id;check.checked=selected.has(Number(file.id));check.setAttribute('aria-label',`选择 ${file.filename||file.id}`);check.onclick=e=>{e.stopPropagation();const id=Number(file.id);check.checked?selected.add(id):selected.delete(id);updateSelectionUI(tableEl,currentFiles);};checkTd.appendChild(check);tr.appendChild(checkTd);
        for(const value of [file.id,file.filename||`Resource #${file.id}`,formatSize(file.size),file.mime_type||'未知',file.source_count??0]){const td=document.createElement('td');td.textContent=text(value);tr.appendChild(td);}
        const categoryTd=document.createElement('td');categoryTd.textContent=(file.category_ids||[]).map(id=>categories.find(c=>Number(c.id)===Number(id))?.name).filter(Boolean).join('、')||'未分类';tr.appendChild(categoryTd);
        const statusTd=document.createElement('td');const status=document.createElement('span');status.className='status-icon';status.textContent=Number(file.source_count)>0?'●':'○';status.title=Number(file.source_count)>0?'有可用来源':'暂无可用来源';statusTd.appendChild(status);tr.appendChild(statusTd);
        const action=document.createElement('td');action.className='actions';const link=document.createElement('a');link.href=`/resources/${file.id}/download`;link.textContent='下载';link.setAttribute('download','');const edit=document.createElement('button');edit.type='button';edit.textContent='分类';edit.onclick=()=>editCategories([file]);action.append(link,edit);tr.appendChild(action);body.appendChild(tr);});
      if(!currentFiles.length){const empty=document.createElement('tr');const td=document.createElement('td');td.colSpan=columns.length;td.textContent='暂无资源';empty.appendChild(td);body.appendChild(empty);} tableEl.appendChild(body);wrap.appendChild(tableEl);list.appendChild(wrap);updateSelectionUI(tableEl,currentFiles);
      const pages=Math.max(1,Math.ceil((data.total||0)/size));pagination.replaceChildren();const previous=document.createElement('button');previous.textContent='上一页';previous.disabled=page<=1;previous.onclick=()=>{page-=1;refresh();};const label=document.createElement('span');label.textContent=`第 ${page} / ${pages} 页`;const next=document.createElement('button');next.textContent='下一页';next.disabled=page>=pages;next.onclick=()=>{page+=1;refresh();};const jump=document.createElement('input');jump.type='number';jump.min='1';jump.max=String(pages);jump.value=String(page);jump.title='跳转页码';jump.style.width='90px';jump.onchange=()=>{page=Math.min(pages,Math.max(1,Number(jump.value)||1));refresh();};pagination.append(previous,label,jump,next);
    }catch(error){list.textContent=error.message;}}
  try{await refresh();}finally{contextMenu.remove();document.removeEventListener('click',closeMenu);}
}

async function renderCategories(container) {
  const createPanel=panel('分类管理'); const form=document.createElement('form');form.className='toolbar';const input=document.createElement('input');input.placeholder='分类名称';input.maxLength=100;input.required=true;const create=document.createElement('button');create.type='submit';create.textContent='创建';form.append(input,create);createPanel.appendChild(form);container.appendChild(createPanel);
  const list=document.createElement('div');list.style.marginTop='12px';container.appendChild(list);
  async function refresh(){const categories=await listCategories();list.replaceChildren();if(!categories.length){list.textContent='暂无分类';return;}const wrap=panel(`分类列表（${categories.length} 项）`);const rows=categories.map(c=>[c.id,c.name]);const tableEl=table(['ID','分类名称','操作'],rows);categories.forEach((category,index)=>{const tr=tableEl.tBodies[0].rows[index];const td=document.createElement('td');const rename=document.createElement('button');rename.type='button';rename.textContent='修改';rename.onclick=async()=>{const value=prompt('分类名称',category.name);if(!value||value.trim()===category.name)return;try{await updateCategory(category.id,value.trim());await refresh();}catch(error){alert(error.message);}};const remove=document.createElement('button');remove.type='button';remove.className='danger';remove.textContent='删除';remove.onclick=async()=>{if(!confirm(`确定删除分类“${category.name}”吗？`))return;try{await removeCategory(category.id);await refresh();}catch(error){alert(error.message);}};td.className='actions';td.append(rename,remove);tr.appendChild(td);});wrap.appendChild(tableEl);list.appendChild(wrap);}
  form.onsubmit=async event=>{event.preventDefault();create.disabled=true;try{await createCategory(input.value.trim());input.value='';await refresh();}catch(error){alert(error.message);}finally{create.disabled=false;}};try{await refresh();}catch(error){list.textContent=error.message;}
}
function formatSize(size){if(!Number.isFinite(Number(size)))return'未知';const units=['B','KB','MB','GB','TB'];let value=Number(size),index=0;while(value>=1024&&index<units.length-1){value/=1024;index++;}return`${value.toFixed(index?2:0)} ${units[index]}`;}
