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
  const data = await response.json();
  if (!Array.isArray(data)) throw new Error('Scanner 状态接口返回数据无效');
  return data;
}

export async function renderScanner(container, section = 'tasks') {
  container.replaceChildren();
  const title = document.createElement('h2');
  title.textContent = `扫描器 / ${section === 'tasks' ? '任务' : section === 'logs' ? '日志' : '设置'}`;
  container.appendChild(title);

  if (section === 'tasks') return renderTasks(container);
  if (section === 'logs') return renderLogs(container);
  if (section === 'settings') return renderSettings(container);
  const item = panel('页面不存在');
  item.appendChild(document.createTextNode('未知的 Scanner 页面。'));
  container.appendChild(item);
}

async function renderTasks(container) {
  const toolbar = document.createElement('div');
  toolbar.className = 'toolbar';
  const refresh = document.createElement('button');
  refresh.type = 'button';
  refresh.textContent = '刷新状态';
  toolbar.appendChild(refresh);
  const list = document.createElement('div');
  list.style.marginTop = '12px';
  container.append(toolbar, list);

  async function load() {
    refresh.disabled = true;
    list.textContent = '正在加载……';
    try {
      const sources = await loadSources();
      list.replaceChildren();
      if (!sources.length) {
        list.textContent = '暂无已启用 Source。';
        return;
      }
      for (const source of sources) {
        const item = panel(source.name || source.telegram_chat_id || `Source #${source.id}`);
        const status = document.createElement('p');
        status.textContent = `状态：${source.enabled ? '已启用' : '已禁用'}`;
        item.appendChild(status);
        const note = document.createElement('p');
        note.className = 'meta';
        note.textContent = 'Scanner 任务由 Source 生命周期驱动，此页面仅显示当前 Source 状态。';
        item.appendChild(note);
        list.appendChild(item);
      }
    } catch (error) {
      list.textContent = error.message;
    } finally {
      refresh.disabled = false;
    }
  }

  refresh.onclick = load;
  await load();
}

function renderLogs(container) {
  const item = panel('扫描日志');
  const message = document.createElement('p');
  message.textContent = '当前后端没有 Scanner 日志查询 API，因此这里不伪造日志数据。';
  item.appendChild(message);
  const note = document.createElement('p');
  note.className = 'meta';
  note.textContent = '如需日志，请查看服务器容器日志。后续提供真实日志 API 后再接入此页面。';
  item.appendChild(note);
  container.appendChild(item);
}

function renderSettings(container) {
  const item = panel('扫描设置');
  const message = document.createElement('p');
  message.textContent = '当前扫描周期由服务器端 SCAN_INTERVAL 配置控制。';
  item.appendChild(message);
  const note = document.createElement('p');
  note.className = 'meta';
  note.textContent = '当前没有 Scanner 设置 API，因此本页面不提供虚假的在线修改功能。';
  item.appendChild(note);
  container.appendChild(item);
}
