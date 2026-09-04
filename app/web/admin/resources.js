import { request } from './api.js';

function text(value) { return String(value ?? ''); }
function panel(title) { const element = document.createElement('section'); element.className = 'panel'; const heading = document.createElement('h3'); heading.textContent = title; element.appendChild(heading); return element; }
function table(headers, rows) {
  const el = document.createElement('table'); el.className = 'admin-table';
  el.innerHTML = `<thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead>`;
  const body = document.createElement('tbody');
  for (const row of rows) { const tr = document.createElement('tr'); for (const value of row) { const td = document.createElement('td'); td.textContent = text(value); tr.appendChild(td); } body.appendChild(tr); }
  el.appendChild(body); return el;
}
async function listSources() { const response = await request('/api/telegram/sources'); if (!response.ok) throw new Error('加载 Sources 失败'); return response.json(); }
async function setSourceEnabled(id, enabled) { const response = await request(`/api/telegram/sources/${id}/enabled`, {method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled})}); if (!response.ok) { let d='更新 Source 状态失败'; try {d=(await response.json()).detail||d;} catch(_){} throw new Error(d); } return response.json(); }
async function listCategories() { const response = await request('/api/admin/categories'); if (!response.ok) throw new Error('加载分类失败'); return response.json(); }
async function createCategory(name) { const response = await request('/api/admin/categories',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})}); if(!response.ok) throw new Error(response.status===409?'分类已存在':'创建分类失败'); return response.json(); }
async function updateCategory(id,name) { const response=await request(`/api/admin/categories/${id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})}); if(!response.ok) throw new Error(response.status===404?'分类不存在':'修改分类失败'); return response.json(); }
async function removeCategory(id) { const response=await request(`/api/admin/categories/${id}`,{method:'DELETE'}); if(!response.ok) throw new Error(response.status===404?'分类不存在':'删除分类失败'); }
async function listFiles(page=1,size=50,categoryId='') { const params=new URLSearchParams({page:String(page),size:String(size)}); if(categoryId) params.set('category_id',String(categoryId)); const response=await request(`/catalog?${params}`); if(!response.ok) throw new Error('加载文件失败'); const payload=await response.json(); if(!payload.data) throw new Error('文件接口返回数据无效'); return payload.data; }
async function setResourceCategories(resourceId,categoryIds) { const response=await request(`/api/admin/resources/${resourceId}/categories`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({category_ids:categoryIds})}); if(!response.ok) throw new Error('保存资源分类失败'); return response.json(); }

export async function renderResources(container, section='sources') {
  container.replaceChildren(); const heading=document.createElement('h2'); heading.textContent=`资源 / ${section==='sources'?'来源':section==='files'?'文件':'分类'}`; container.appendChild(heading);
  if(section==='sources') return renderSources(container); if(section==='files') return renderFiles(container); if(section==='categories') return renderCategories(container);
}

async function renderSources(container) {
  const list=document.createElement('div'); container.appendChild(list);
  try {
    const sources=await listSources(); if(!sources.length){list.textContent='暂无已启用 Source。';return;}
    const wrap=panel('来源列表');
    const rows=sources.map(source=>[source.id,source.name||source.telegram_chat_id,source.account_name,source.telegram_chat_id,source.enabled?'运行中':'已禁用',source.scan_status||'idle']);
    const tableEl=table(['ID','名称','Telegram 账号','Chat ID','状态','扫描状态','操作'], rows.map(row=>[...row]));
    sources.forEach((source,index)=>{ const tr=tableEl.tBodies[0].rows[index]; const td=document.createElement('td'); const button=document.createElement('button'); button.type='button'; button.textContent=source.enabled?'禁用':'启用'; button.onclick=async()=>{button.disabled=true;try{await setSourceEnabled(source.id,!source.enabled);source.enabled=!source.enabled;tr.children[4].textContent=source.enabled?'运行中':'已禁用';button.textContent=source.enabled?'禁用':'启用';}catch(e){alert(e.message);}finally{button.disabled=false;}};td.appendChild(button);tr.appendChild(td); });
    wrap.appendChild(tableEl); list.appendChild(wrap);
  } catch(error){list.textContent=error.message;}
}

async function renderFiles(container) {
  const controls=document.createElement('div'); controls.className='toolbar';
  const category=document.createElement('select'); category.setAttribute('aria-label','分类过滤'); category.appendChild(new Option('全部分类',''));
  let categories=[]; try{categories=await listCategories(); for(const item of categories) category.appendChild(new Option(item.name,item.id));}catch(error){controls.textContent=error.message;container.appendChild(controls);return;}
  const list=document.createElement('div'); const pagination=document.createElement('div'); pagination.className='pagination'; container.append(controls,list,pagination);
  let page=1; const size=50;
  async function refresh(){ list.textContent='正在加载……'; try{const data=await listFiles(page,size,category.value); const files=data.items||[]; list.replaceChildren();
      const wrap=panel(`文件列表（${data.total||0} 项）`);
      const tableEl=document.createElement('table'); tableEl.className='admin-table'; tableEl.innerHTML='<thead><tr><th>ID</th><th>文件名</th><th>大小</th><th>类型</th><th>Telegram 来源</th><th>分类</th><th>操作</th></tr></thead>';
      const body=document.createElement('tbody');
      files.forEach(file=>{
        const tr=document.createElement('tr');
        [file.id,file.filename||`Resource #${file.id}`,formatSize(file.size),file.mime_type||'未知',file.source_count??0,(file.category_ids||[]).map(id=>categories.find(c=>Number(c.id)===Number(id))?.name).filter(Boolean).join('、')||'未分类'].forEach(value=>{const td=document.createElement('td');td.textContent=text(value);tr.appendChild(td);});
        const action=document.createElement('td'); action.className='actions';
        const download=document.createElement('a'); download.href=`/resources/${file.id}/download`; download.textContent='下载'; download.setAttribute('download','');
        const edit=document.createElement('button'); edit.type='button'; edit.textContent='分类'; edit.onclick=async()=>{const selected=prompt('输入分类 ID，多个分类用逗号分隔：',(file.category_ids||[]).join(','));if(selected===null)return;const ids=selected.split(',').map(v=>Number(v.trim())).filter(Number.isInteger);try{const result=await setResourceCategories(file.id,ids);file.category_ids=result.category_ids||ids;tr.children[5].textContent=file.category_ids.map(id=>categories.find(c=>Number(c.id)===Number(id))?.name).filter(Boolean).join('、')||'未分类';}catch(error){alert(error.message);}};
        action.append(download,edit); tr.appendChild(action); body.appendChild(tr);
      });
      if(files.length) tableEl.appendChild(body); else {const empty=document.createElement('tbody');empty.innerHTML='<tr><td colspan="7">暂无资源</td></tr>';tableEl.appendChild(empty);} wrap.appendChild(tableEl); list.appendChild(wrap);
      const pages=Math.max(1,Math.ceil((data.total||0)/size)); pagination.replaceChildren(); const previous=document.createElement('button'); previous.textContent='上一页';previous.disabled=page<=1;previous.onclick=()=>{page-=1;refresh();}; const label=document.createElement('span');label.textContent=`第 ${page} / ${pages} 页`; const next=document.createElement('button');next.textContent='下一页';next.disabled=page>=pages;next.onclick=()=>{page+=1;refresh();}; const jump=document.createElement('input');jump.type='number';jump.min='1';jump.max=String(pages);jump.value=String(page);jump.title='跳转页码';jump.style.width='90px';jump.onchange=()=>{const target=Math.min(pages,Math.max(1,Number(jump.value)||1));page=target;refresh();}; pagination.append(previous,label,jump,next);
    }catch(error){list.textContent=error.message;}}
  category.onchange=()=>{page=1;refresh();}; await refresh();
}

async function renderCategories(container) {
  const createPanel=panel('分类管理'); const form=document.createElement('form');form.className='toolbar';const input=document.createElement('input');input.placeholder='分类名称';input.maxLength=100;input.required=true;const create=document.createElement('button');create.type='submit';create.textContent='创建';form.append(input,create);createPanel.appendChild(form);container.appendChild(createPanel);
  const list=document.createElement('div');list.style.marginTop='12px';container.appendChild(list);
  async function refresh(){const categories=await listCategories();list.replaceChildren();if(!categories.length){list.textContent='暂无分类';return;}const wrap=panel(`分类列表（${categories.length} 项）`);const rows=categories.map(c=>[c.id,c.name]);const tableEl=table(['ID','分类名称','操作'],rows);categories.forEach((category,index)=>{const tr=tableEl.tBodies[0].rows[index];const td=document.createElement('td');const rename=document.createElement('button');rename.type='button';rename.textContent='修改';rename.onclick=async()=>{const value=prompt('分类名称',category.name);if(!value||value.trim()===category.name)return;try{await updateCategory(category.id,value.trim());await refresh();}catch(error){alert(error.message);}};const remove=document.createElement('button');remove.type='button';remove.className='danger';remove.textContent='删除';remove.onclick=async()=>{if(!confirm(`确定删除分类“${category.name}”吗？`))return;try{await removeCategory(category.id);await refresh();}catch(error){alert(error.message);}};td.className='actions';td.append(rename,remove);tr.appendChild(td);});wrap.appendChild(tableEl);list.appendChild(wrap);}
  form.onsubmit=async event=>{event.preventDefault();create.disabled=true;try{await createCategory(input.value.trim());input.value='';await refresh();}catch(error){alert(error.message);}finally{create.disabled=false;}};try{await refresh();}catch(error){list.textContent=error.message;}
}
function formatSize(size){if(!Number.isFinite(Number(size)))return'未知';const units=['B','KB','MB','GB','TB'];let value=Number(size),index=0;while(value>=1024&&index<units.length-1){value/=1024;index++;}return`${value.toFixed(index?2:0)} ${units[index]}`;}
