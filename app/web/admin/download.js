import { request } from './api.js';

const ACTIVE_PATH='/api/admin/downloads/active'; const HISTORY_PATH='/api/admin/downloads/history';
function formatBytes(value){const size=Number(value);if(!Number.isFinite(size)||size<0)return'-';if(size<1024)return`${size} B`;const units=['KB','MB','GB','TB'];let current=size;for(const unit of units){current/=1024;if(current<1024||unit==='TB')return`${current.toFixed(1)} ${unit}`;}return'-';}
function formatTime(value){if(value===null||value===undefined||value==='')return'-';const timestamp=Number(value);if(!Number.isFinite(timestamp))return'-';const date=new Date(timestamp*1000);return Number.isNaN(date.getTime())?'-':date.toLocaleString('zh-CN');}
function statusText(status){return({active:'进行中',completed:'已完成',failed:'失败'})[status]||status||'-';}
function escapeHtml(value){return String(value??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));}
async function deleteRecord(id){const response=await request(`/api/admin/downloads/${id}`,{method:'DELETE'});if(!response.ok){let detail='删除下载记录失败';try{detail=(await response.json()).detail||detail;}catch(_){}throw new Error(detail);}}
function renderTable(container,rows,history,onDelete){
  if(!rows.length){container.innerHTML=`<div class="admin-empty">${history?'暂无下载记录':'当前没有进行中的下载'}</div>`;return;}
  const table=document.createElement('table');table.className='admin-table';
  const head=history?['文件名','大小','状态','已传输','开始时间','完成时间','用户','操作']:['文件名','大小','状态','已传输','开始时间','用户','操作'];
  table.innerHTML=`<thead><tr>${head.map(i=>`<th>${i}</th>`).join('')}</tr></thead>`;
  const body=document.createElement('tbody');
  for(const row of rows){const values=history?[row.filename,formatBytes(row.size),statusText(row.status),formatBytes(row.bytes_transferred),formatTime(row.started_at),formatTime(row.completed_at),row.created_by||'-']:[row.filename,formatBytes(row.size),statusText(row.status),formatBytes(row.bytes_transferred),formatTime(row.started_at),row.created_by||'-'];const tr=document.createElement('tr');tr.innerHTML=values.map(v=>`<td>${escapeHtml(v)}</td>`).join('');const td=document.createElement('td');const remove=document.createElement('button');remove.type='button';remove.className='danger';remove.textContent='删除';remove.onclick=async()=>{if(!confirm(`确定删除下载记录“${row.filename||row.id}”吗？`))return;remove.disabled=true;try{await onDelete(row.id);tr.remove();if(!body.children.length)container.replaceChildren();}catch(error){alert(error.message);remove.disabled=false;}};td.appendChild(remove);tr.appendChild(td);body.appendChild(tr);}
  table.appendChild(body);container.appendChild(table);
}
async function load(path,container,history){container.innerHTML='<div class="admin-loading">加载中…</div>';try{const response=await request(path);if(!response.ok)throw new Error(`HTTP ${response.status}`);const rows=await response.json();if(!Array.isArray(rows))throw new Error('下载接口返回数据格式无效');container.replaceChildren();renderTable(container,rows,history,deleteRecord);}catch(error){container.innerHTML=`<div class="admin-error">加载失败：${escapeHtml(error.message)}</div>`;}}
export function renderDownload(container,page){const history=page==='history';container.innerHTML=`<section class="admin-section"><div class="admin-section-header"><div><h1>${history?'下载历史':'正在下载'}</h1><p>${history?'查看已完成和失败的下载记录。':'查看当前正在进行的下载。取消客户端传输后，服务端会将该记录标记为失败并从这里消失。'}</p></div><button class="admin-button" type="button" data-refresh>刷新</button></div><div data-download-table></div></section>`;const table=container.querySelector('[data-download-table]');const refresh=()=>load(history?HISTORY_PATH:ACTIVE_PATH,table,history);container.querySelector('[data-refresh]').addEventListener('click',refresh);refresh();}
