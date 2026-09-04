import { request } from './api.js';

function formatBytes(value) {
  const size = Number(value || 0);
  if (size < 1024) return `${size} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let current = size;
  for (const unit of units) {
    current /= 1024;
    if (current < 1024 || unit === 'TB') return `${current.toFixed(1)} ${unit}`;
  }
  return `${size} B`;
}

function formatTime(value) {
  if (!value) return '-';
  return new Date(Number(value) * 1000).toLocaleString('zh-CN');
}

function statusText(status) {
  return ({
    active: '进行中',
    completed: '已完成',
    failed: '失败',
  })[status] || status || '-';
}

function renderTable(container, rows, history) {
  if (!rows.length) {
    container.innerHTML = `<div class="admin-empty">${history ? '暂无下载记录' : '当前没有进行中的下载'}</div>`;
    return;
  }

  const table = document.createElement('table');
  table.className = 'admin-table';
  const head = history
    ? ['文件名', '大小', '状态', '已传输', '开始时间', '完成时间', '用户']
    : ['文件名', '大小', '状态', '已传输', '开始时间', '用户'];
  table.innerHTML = `<thead><tr>${head.map((item) => `<th>${item}</th>`).join('')}</tr></thead>`;

  const body = document.createElement('tbody');
  rows.forEach((row) => {
    const values = history
      ? [row.filename, formatBytes(row.size), statusText(row.status), formatBytes(row.bytes_transferred), formatTime(row.started_at), formatTime(row.completed_at), row.created_by || '-']
      : [row.filename, formatBytes(row.size), statusText(row.status), formatBytes(row.bytes_transferred), formatTime(row.started_at), row.created_by || '-'];
    const tr = document.createElement('tr');
    tr.innerHTML = values.map((value) => `<td>${String(value).replace(/[&<>\"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;' }[char]))}</td>`).join('');
    body.appendChild(tr);
  });
  table.appendChild(body);
  container.appendChild(table);
}

async function load(path, container, history) {
  container.innerHTML = '<div class="admin-loading">加载中…</div>';
  try {
    const response = await request(path);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const rows = await response.json();
    container.innerHTML = '';
    renderTable(container, rows, history);
  } catch (error) {
    container.innerHTML = `<div class="admin-error">加载失败：${error.message}</div>`;
  }
}

export function renderDownload(container, page) {
  const history = page === 'history';
  container.innerHTML = `
    <section class="admin-section">
      <div class="admin-section-header">
        <div>
          <h1>${history ? '下载历史' : '正在下载'}</h1>
          <p>${history ? '查看已完成和失败的下载记录。' : '查看当前正在进行的下载。'}</p>
        </div>
        <button class="admin-button" type="button" data-refresh>刷新</button>
      </div>
      <div data-download-table></div>
    </section>
  `;

  const table = container.querySelector('[data-download-table]');
  const refresh = () => load(history ? '/api/admin/downloads/history' : '/api/admin/downloads/active', table, history);
  container.querySelector('[data-refresh]').addEventListener('click', refresh);
  refresh();
}
