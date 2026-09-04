import { request } from './api.js';

function text(value) {
  return String(value ?? '');
}

function panel(title) {
  const element = document.createElement('section');
  element.className = 'panel';
  const heading = document.createElement('h3');
  heading.textContent = title;
  element.appendChild(heading);
  return element;
}

async function listSources() {
  const response = await request('/api/telegram/sources');
  if (!response.ok) throw new Error('加载 Sources 失败');
  return response.json();
}

async function setSourceEnabled(id, enabled) {
  const response = await request(`/api/telegram/sources/${id}/enabled`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({enabled})
  });
  if (!response.ok) {
    let detail = '更新 Source 状态失败';
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}

async function listCategories() {
  const response = await request('/api/admin/categories');
  if (!response.ok) throw new Error('加载分类失败');
  return response.json();
}

async function createCategory(name) {
  const response = await request('/api/admin/categories', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name})
  });
  if (!response.ok) throw new Error(response.status === 409 ? '分类已存在' : '创建分类失败');
  return response.json();
}

async function updateCategory(id, name) {
  const response = await request(`/api/admin/categories/${id}`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name})
  });
  if (!response.ok) throw new Error(response.status === 404 ? '分类不存在' : '修改分类失败');
  return response.json();
}

async function removeCategory(id) {
  const response = await request(`/api/admin/categories/${id}`, {method: 'DELETE'});
  if (!response.ok) throw new Error(response.status === 404 ? '分类不存在' : '删除分类失败');
}

async function listFiles(page = 1, size = 50, categoryId = '') {
  const params = new URLSearchParams({page: String(page), size: String(size)});
  if (categoryId) params.set('category_id', String(categoryId));
  const response = await request(`/catalog?${params}`);
  if (!response.ok) throw new Error('加载文件失败');
  const payload = await response.json();
  if (!payload.data) throw new Error('文件接口返回数据无效');
  return payload.data;
}

async function setResourceCategories(resourceId, categoryIds) {
  const response = await request(`/api/admin/resources/${resourceId}/categories`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({category_ids: categoryIds})
  });
  if (!response.ok) throw new Error('保存资源分类失败');
  return response.json();
}

export async function renderResources(container, section = 'sources') {
  container.replaceChildren();
  const heading = document.createElement('h2');
  heading.textContent = `资源 / ${section === 'sources' ? '来源' : section === 'files' ? '文件' : '分类'}`;
  container.appendChild(heading);

  if (section === 'sources') return renderSources(container);
  if (section === 'files') return renderFiles(container);
  if (section === 'categories') return renderCategories(container);
}

async function renderSources(container) {
  const list = document.createElement('div');
  container.appendChild(list);
  try {
    const sources = await listSources();
    if (!sources.length) { list.textContent = '暂无已启用 Source。'; return; }
    for (const source of sources) {
      const item = panel(text(source.name || source.telegram_chat_id));
      const meta = document.createElement('p');
      meta.textContent = `账号: ${text(source.account_name)} · 状态: ${source.enabled ? '运行中' : '已禁用'} · 扫描: ${text(source.scan_status || 'idle')}`;
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = source.enabled ? '禁用' : '启用';
      button.onclick = async () => {
        button.disabled = true;
        try { await setSourceEnabled(source.id, !source.enabled); await renderResources(container, 'sources'); }
        catch (error) { alert(error.message); button.disabled = false; }
      };
      item.append(meta, button);
      list.appendChild(item);
    }
  } catch (error) { list.textContent = error.message; }
}

async function renderFiles(container) {
  const controls = document.createElement('div');
  controls.className = 'toolbar';
  const category = document.createElement('select');
  category.setAttribute('aria-label', '分类过滤');
  category.appendChild(new Option('全部分类', ''));
  try {
    for (const item of await listCategories()) category.appendChild(new Option(item.name, item.id));
  } catch (error) {
    controls.textContent = error.message;
    container.appendChild(controls);
    return;
  }
  const list = document.createElement('div');
  list.style.marginTop = '12px';
  const pagination = document.createElement('div');
  pagination.className = 'pagination';
  container.append(controls, list, pagination);

  let page = 1;
  const size = 50;
  async function refresh() {
    list.textContent = '正在加载……';
    try {
      const data = await listFiles(page, size, category.value);
      list.replaceChildren();
      const files = data.items || [];
      if (!files.length) list.textContent = '暂无资源';
      for (const file of files) {
        const item = panel(text(file.filename || `Resource #${file.id}`));
        const meta = document.createElement('p');
        meta.textContent = `大小: ${formatSize(file.size)} · ${text(file.mime_type || '未知类型')} · Telegram 来源: ${file.source_count ?? 0}`;
        item.appendChild(meta);
        const badges = document.createElement('div');
        for (const id of file.category_ids || []) {
          const found = (await listCategories()).find(c => Number(c.id) === Number(id));
          if (found) badges.appendChild(Object.assign(document.createElement('span'), {className: 'badge', textContent: found.name}));
        }
        if (badges.childElementCount) item.appendChild(badges);
        const actions = document.createElement('div');
        actions.className = 'actions';
        const download = document.createElement('a');
        download.href = `/resources/${file.id}/download`;
        download.textContent = '下载';
        download.setAttribute('download', '');
        actions.appendChild(download);
        const edit = document.createElement('button');
        edit.type = 'button';
        edit.textContent = '分类';
        edit.onclick = async () => {
          const categories = await listCategories();
          const selected = prompt('输入分类 ID，多个分类用逗号分隔：', (file.category_ids || []).join(','));
          if (selected === null) return;
          const ids = selected.split(',').map(v => Number(v.trim())).filter(Number.isInteger);
          try { await setResourceCategories(file.id, ids); await refresh(); }
          catch (error) { alert(error.message); }
        };
        actions.appendChild(edit);
        item.appendChild(actions);
        list.appendChild(item);
      }
      const pages = Math.max(1, Math.ceil((data.total || 0) / size));
      pagination.replaceChildren();
      const previous = document.createElement('button');
      previous.textContent = '上一页'; previous.disabled = page <= 1; previous.onclick = () => { page -= 1; refresh(); };
      const label = document.createElement('span'); label.textContent = `${page} / ${pages}`;
      const next = document.createElement('button');
      next.textContent = '下一页'; next.disabled = page >= pages; next.onclick = () => { page += 1; refresh(); };
      pagination.append(previous, label, next);
    } catch (error) { list.textContent = error.message; }
  }
  category.onchange = () => { page = 1; refresh(); };
  await refresh();
}

async function renderCategories(container) {
  const createPanel = panel('分类管理');
  const form = document.createElement('form');
  form.className = 'toolbar';
  const input = document.createElement('input'); input.placeholder = '分类名称'; input.maxLength = 100; input.required = true;
  const create = document.createElement('button'); create.type = 'submit'; create.textContent = '创建';
  form.append(input, create); createPanel.appendChild(form); container.appendChild(createPanel);
  const list = document.createElement('div'); list.style.marginTop = '12px'; container.appendChild(list);

  async function refresh() {
    const categories = await listCategories();
    list.replaceChildren();
    if (!categories.length) { list.textContent = '暂无分类'; return; }
    for (const category of categories) {
      const row = document.createElement('div'); row.className = 'category-row';
      const name = document.createElement('span'); name.textContent = category.name;
      const rename = document.createElement('button'); rename.type = 'button'; rename.textContent = '修改';
      rename.onclick = async () => {
        const value = prompt('分类名称', category.name);
        if (!value || value.trim() === category.name) return;
        try { await updateCategory(category.id, value.trim()); await refresh(); } catch (error) { alert(error.message); }
      };
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'danger'; remove.textContent = '删除';
      remove.onclick = async () => {
        if (!confirm(`确定删除分类“${category.name}”吗？`)) return;
        try { await removeCategory(category.id); await refresh(); } catch (error) { alert(error.message); }
      };
      row.append(name, rename, remove); list.appendChild(row);
    }
  }
  form.onsubmit = async event => {
    event.preventDefault(); create.disabled = true;
    try { await createCategory(input.value.trim()); input.value = ''; await refresh(); }
    catch (error) { alert(error.message); }
    finally { create.disabled = false; }
  };
  try { await refresh(); } catch (error) { list.textContent = error.message; }
}

function formatSize(size) {
  if (!Number.isFinite(Number(size))) return '未知';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let value = Number(size), index = 0;
  while (value >= 1024 && index < units.length - 1) { value /= 1024; index += 1; }
  return `${value.toFixed(index ? 2 : 0)} ${units[index]}`;
}
