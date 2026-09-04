import { request } from './api.js';

function text(value) {
  return String(value ?? '');
}

function createPanel(title) {
  const panel = document.createElement('section');
  panel.className = 'panel';
  const heading = document.createElement('h3');
  heading.textContent = title;
  panel.appendChild(heading);
  return panel;
}

async function loadSources() {
  const response = await request('/api/telegram/sources');
  if (!response.ok) throw new Error('加载 Sources 失败');
  return response.json();
}

async function toggleSource(id, enabled) {
  const response = await request(`/api/telegram/sources/${id}/enabled`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({enabled})
  });
  if (!response.ok) throw new Error('更新 Source 状态失败');
}

async function loadCategories() {
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
}

async function renameCategory(id, name) {
  const response = await request(`/api/admin/categories/${id}`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name})
  });
  if (!response.ok) throw new Error('修改分类失败');
}

async function deleteCategory(id) {
  const response = await request(`/api/admin/categories/${id}`, {method: 'DELETE'});
  if (!response.ok) throw new Error('删除分类失败');
}

async function loadFiles() {
  const response = await request('/catalog?page=1&size=50');
  if (!response.ok) throw new Error('加载文件失败');
  const payload = await response.json();
  return payload.data?.items || [];
}

export async function renderResources(container, section = 'sources') {
  container.replaceChildren();
  const title = document.createElement('h2');
  title.textContent = `资源 / ${section}`;
  container.appendChild(title);

  if (section === 'sources') await renderSources(container);
  else if (section === 'files') await renderFiles(container);
  else if (section === 'categories') await renderCategories(container);
}

async function renderSources(container) {
  const list = document.createElement('div');
  container.appendChild(list);
  try {
    const sources = await loadSources();
    if (!sources.length) { list.textContent = '暂无 Source'; return; }
    for (const source of sources) {
      const panel = createPanel(text(source.name || source.telegram_chat_id));
      const state = document.createElement('p');
      state.textContent = `状态: ${source.enabled ? '运行中' : '已禁用'}`;
      const button = document.createElement('button');
      button.textContent = source.enabled ? '禁用' : '启用';
      button.onclick = async () => {
        button.disabled = true;
        try {
          await toggleSource(source.id, !source.enabled);
          await renderResources(container, 'sources');
        } catch (error) { alert(error.message); button.disabled = false; }
      };
      panel.append(state, button);
      list.appendChild(panel);
    }
  } catch (error) { list.textContent = error.message; }
}

async function renderFiles(container) {
  const list = document.createElement('div');
  container.appendChild(list);
  try {
    const files = await loadFiles();
    if (!files.length) { list.textContent = '暂无资源'; return; }
    for (const file of files) {
      const panel = createPanel(text(file.filename || `Resource #${file.id}`));
      const meta = document.createElement('p');
      meta.textContent = `大小: ${formatSize(file.size)} · Telegram 来源: ${file.source_count ?? 0}`;
      const download = document.createElement('a');
      download.href = `/resources/${file.id}/download`;
      download.textContent = '下载';
      download.setAttribute('download', '');
      panel.append(meta, download);
      list.appendChild(panel);
    }
  } catch (error) { list.textContent = error.message; }
}

async function renderCategories(container) {
  const panel = createPanel('分类管理');
  const form = document.createElement('form');
  form.className = 'toolbar';
  const input = document.createElement('input');
  input.placeholder = '新分类名称';
  input.maxLength = 100;
  input.required = true;
  const create = document.createElement('button');
  create.type = 'submit';
  create.textContent = '创建';
  form.append(input, create);
  panel.appendChild(form);

  const list = document.createElement('div');
  list.style.marginTop = '12px';
  panel.appendChild(list);
  container.appendChild(panel);

  async function refresh() {
    list.replaceChildren();
    const categories = await loadCategories();
    if (!categories.length) { list.textContent = '暂无分类'; return; }
    for (const category of categories) {
      const row = document.createElement('div');
      row.className = 'category-row';
      const name = document.createElement('span');
      name.textContent = category.name;
      const rename = document.createElement('button');
      rename.textContent = '修改';
      rename.onclick = async () => {
        const value = window.prompt('分类名称', category.name);
        if (!value || value.trim() === category.name) return;
        try { await renameCategory(category.id, value.trim()); await refresh(); }
        catch (error) { alert(error.message); }
      };
      const remove = document.createElement('button');
      remove.textContent = '删除';
      remove.className = 'danger';
      remove.onclick = async () => {
        if (!window.confirm(`确定删除分类“${category.name}”吗？`)) return;
        try { await deleteCategory(category.id); await refresh(); }
        catch (error) { alert(error.message); }
      };
      row.append(name, rename, remove);
      list.appendChild(row);
    }
  }

  form.onsubmit = async event => {
    event.preventDefault();
    const name = input.value.trim();
    if (!name) return;
    create.disabled = true;
    try { await createCategory(name); input.value = ''; await refresh(); }
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
