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
  if (!response.ok) throw new Error(`加载 Scanner 状态失败（HTTP ${response.status}）`);
  const data = await response.json();
  if (!Array.isArray(data)) throw new Error('Scanner 状态接口返回数据无效');
  return data;
}

export async function renderScanner(container, section = 'tasks') {
  container.replaceChildren();
  const page = document.createElement('div');
  page.className = 'admin-page';
  const title = document.createElement('h1');
  title.textContent = `扫描器 / ${section === 'tasks' ? '任务' : section === 'logs' ? '日志' : '设置'}`;
  page.appendChild(title);
  container.appendChild(page);

  if (section === 'tasks') return renderTasks(page);
  if (section === 'logs') return renderLogs(page);
  if (section === 'settings') return renderSettings(page);
}

async function renderTasks(container) {
  const toolbar = document.createElement('div'); toolbar.className = 'toolbar';
  const refresh = document.createElement('button'); refresh.type = 'button'; refresh.textContent = '刷新状态';
  const list = document.createElement('div'); list.style.marginTop = '12px';
  toolbar.appendChild(refresh); container.append(toolbar, list);
  async function load() {
    refresh.disabled = true; list.textContent = '正在加载……';
    try {
      const sources = await loadSources(); list.replaceChildren();
      if (!sources.length) { list.textContent = '暂无已启用 Source。'; return; }
      for (const source of sources) {
        const item = panel(source.name || source.telegram_chat_id || `Source #${source.id}`);
        const status = document.createElement('p'); status.textContent = `状态：${source.enabled ? '已启用' : '已禁用'} · 扫描：${source.scan_status || 'idle'}`;
        const note = document.createElement('p'); note.className = 'meta'; note.textContent = '扫描任务由 Source 生命周期驱动。';
        item.append(status, note); list.appendChild(item);
      }
    } catch (error) { list.textContent = `加载失败：${error.message}`; }
    finally { refresh.disabled = false; }
  }
  refresh.onclick = load; await load();
}

function renderLogs(container) {
  const item = panel('扫描日志');
  item.appendChild(document.createTextNode('当前后端没有 Scanner 日志查询 API，因此不伪造日志数据。')); container.appendChild(item);
}

function renderSettings(container) {
  const item = panel('扫描设置');
  item.appendChild(document.createTextNode('扫描周期由服务器端 SCAN_INTERVAL 配置控制。当前没有在线修改 API。')); container.appendChild(item);
}
