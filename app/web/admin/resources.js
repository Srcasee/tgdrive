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

  const panel = createPanel(section === 'files' ? '文件管理' : '分类管理');
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
