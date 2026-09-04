import { request } from './api.js';

function panel(title) {
  const el = document.createElement('section');
  el.className = 'panel';
  const heading = document.createElement('h3');
  heading.textContent = title;
  el.appendChild(heading);
  return el;
}

async function loadSources() {
  const response = await request('/api/telegram/sources');
  if (!response.ok) throw new Error('加载 Scanner 状态失败');
  return response.json();
}

export async function renderScanner(container, section = 'tasks') {
  container.replaceChildren();
  const title = document.createElement('h2');
  title.textContent = `扫描器 / ${section}`;
  container.appendChild(title);

  if (section === 'tasks') return renderTasks(container);
  if (section === 'logs') return renderLogs(container);
  return renderSettings(container);
}

async function renderTasks(container) {
  const list = document.createElement('div');
  container.appendChild(list);
  try {
    const sources = await loadSources();
    if (!sources.length) { list.textContent = '暂无 Source'; return; }
    for (const source of sources) {
      const item = panel(source.name || source.telegram_chat_id || `Source #${source.id}`);
      const status = document.createElement('p');
      const scanStatus = source.scan_status || (source.enabled ? '已启用' : '已禁用');
      status.textContent = `Source: ${source.enabled ? '启用' : '禁用'} · 扫描: ${scanStatus}`;
      item.appendChild(status);
      list.appendChild(item);
    }
  } catch (error) { list.textContent = error.message; }
}

function renderLogs(container) {
  const item = panel('扫描日志');
  item.appendChild(document.createTextNode('当前 Scanner 仅提供 Source 扫描状态，日志查看接口尚未提供。'));
  container.appendChild(item);
}

function renderSettings(container) {
  const item = panel('扫描设置');
  item.appendChild(document.createTextNode('扫描周期由服务器配置 SCAN_INTERVAL 控制。当前管理 API 未提供在线修改接口。'));
  container.appendChild(item);
}
