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

export async function renderResources(container, section = 'sources') {
  container.replaceChildren();
  const title = document.createElement('h2');
  title.textContent = `资源 / ${section}`;
  container.appendChild(title);

  if (section === 'sources') {
    await renderSources(container);
    return;
  }

  if (section === 'files') {
    await renderFiles(container);
    return;
  }

  const panel = createPanel('分类管理');
  panel.appendChild(document.createTextNode('模块开发中'));
  container.appendChild(panel);
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

async function renderSources(container) {
  const list = document.createElement('div');
  container.appendChild(list);

  try {
    const sources = await loadSources();
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
          await renderSources(container);
        } catch (error) {
          alert(error.message);
          button.disabled = false;
        }
      };

      panel.append(state, button);
      list.appendChild(panel);
    }
  } catch (error) {
    list.textContent = error.message;
  }
}

async function loadFiles() {
  const response = await request('/catalog?page=1&size=50');
  if (!response.ok) throw new Error('加载文件失败');
  return response.json();
}

async function renderFiles(container) {
  const list = document.createElement('div');
  container.appendChild(list);

  try {
    const payload = await loadFiles();
    const files = payload.data?.items || payload.data || [];

    if (!files.length) {
      list.textContent = '暂无资源';
      return;
    }

    for (const file of files) {
      const panel = createPanel(text(file.filename || file.name || `Resource #${file.id}`));

      const meta = document.createElement('p');
      meta.textContent = `大小: ${file.size ?? '未知'} · ID: ${file.id}`;

      const source = document.createElement('p');
      source.textContent = `来源数量: ${file.source_count ?? 0}`;

      const download = document.createElement('a');
      download.href = `/resources/${file.id}/download`;
      download.textContent = '下载';

      panel.append(meta, source, download);
      list.appendChild(panel);
    }
  } catch (error) {
    list.textContent = error.message;
  }
}
