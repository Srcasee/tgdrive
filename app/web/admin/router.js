import { updateActiveMenu } from './layout.js';

const routes = {
  '#dashboard': (container) => renderDashboard(container),
  '#telegram/accounts': (container) => loadModule('./telegram.js', container, 'accounts'),
  '#telegram/dialogs': (container) => loadModule('./telegram.js', container, 'dialogs'),
  '#telegram/sessions': (container) => loadModule('./telegram.js', container, 'sessions'),
  '#resources/sources': (container) => loadModule('./resources.js', container, 'sources'),
  '#resources/files': (container) => loadModule('./resources.js', container, 'files'),
  '#resources/categories': (container) => loadModule('./resources.js', container, 'categories'),
  '#scanner/tasks': (container) => loadModule('./scanner.mjs', container, 'tasks'),
  '#scanner/logs': (container) => loadModule('./scanner.mjs', container, 'logs'),
  '#scanner/settings': (container) => loadModule('./scanner.mjs', container, 'settings'),
  '#download/active': (container) => loadModule('./download.js', container, 'active'),
  '#download/history': (container) => loadModule('./download.js', container, 'history'),
  '#system/config': (container) => renderPlaceholder(container, '系统 / 配置', '当前没有系统配置管理 API。'),
  '#system/api': (container) => renderPlaceholder(container, '系统 / API', '当前没有 API 管理 API。'),
  '#recycle': (container) => renderPlaceholder(container, '回收站', '回收站生命周期尚未接入后端。'),
};

function renderDashboard(container) {
  container.replaceChildren();
  const page = document.createElement('div'); page.className = 'admin-page';
  page.innerHTML = '<header class="admin-page-header"><div><h1>仪表盘</h1><p>TGDrive 管理后台</p></div></header><section class="panel"><h3>快速入口</h3><p class="admin-muted">从左侧导航进入 Telegram、资源、扫描器和下载管理。</p></section>';
  container.appendChild(page);
}

function renderPlaceholder(container, title, message) {
  container.replaceChildren();
  const page = document.createElement('div'); page.className = 'admin-page';
  const header = document.createElement('header'); header.className = 'admin-page-header';
  header.innerHTML = `<div><h1>${title}</h1></div>`;
  const panel = document.createElement('section'); panel.className = 'panel'; panel.textContent = message;
  page.append(header, panel); container.appendChild(page);
}

async function loadModule(path, container, section) {
  try {
    const module = await import(path);
    const renderer = path === './telegram.js' ? module.renderTelegram
      : path === './resources.js' ? module.renderResources
      : path === './scanner.mjs' ? module.renderScanner
      : module.renderDownload;
    if (typeof renderer !== 'function') throw new Error(`模块 ${path} 没有可用的渲染函数`);
    await renderer(container, section);
  } catch (error) {
    container.replaceChildren();
    const page = document.createElement('div'); page.className = 'admin-page';
    const box = document.createElement('div'); box.className = 'admin-error';
    box.textContent = `页面加载失败：${error.message}`;
    page.appendChild(box); container.appendChild(page);
    console.error(`Failed to load admin module ${path}`, error);
  }
}

export function navigate(path) { if (location.hash !== path) location.hash = path; }

export async function renderRoute(container, path = location.hash || '#dashboard') {
  const routePath = routes[path] ? path : '#dashboard';
  updateActiveMenu(routePath); await routes[routePath](container);
}

export function initRouter(container) {
  const update = () => renderRoute(container).catch((error) => {
    container.innerHTML = `<div class="admin-page"><div class="admin-error">页面加载失败：${error.message}</div></div>`;
    console.error('Admin route error', error);
  });
  window.addEventListener('hashchange', update); update();
}
