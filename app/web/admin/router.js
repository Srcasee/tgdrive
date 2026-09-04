import { renderTelegram } from './telegram.js';
import { renderResources } from './resources.js';
import { renderScanner } from './scanner.js';
import { renderDownload } from './download.js';

const routes = {
  '#dashboard': (container) => { container.textContent = 'Dashboard'; },
  '#telegram/accounts': (container) => renderTelegram(container, 'accounts'),
  '#telegram/dialogs': (container) => renderTelegram(container, 'dialogs'),
  '#telegram/sessions': (container) => renderTelegram(container, 'sessions'),
  '#resources/sources': (container) => renderResources(container, 'sources'),
  '#resources/files': (container) => renderResources(container, 'files'),
  '#resources/categories': (container) => renderResources(container, 'categories'),
  '#scanner/tasks': (container) => renderScanner(container, 'tasks'),
  '#scanner/logs': (container) => renderScanner(container, 'logs'),
  '#scanner/settings': (container) => renderScanner(container, 'settings'),
  '#download/active': (container) => renderDownload(container, 'active'),
  '#download/history': (container) => renderDownload(container, 'history'),
  '#system/config': (container) => { container.textContent = '系统 / 配置'; },
  '#system/api': (container) => { container.textContent = '系统 / API'; },
  '#recycle': (container) => { container.textContent = '回收站'; },
};

export function navigate(path) {
  location.hash = path;
}

export function renderRoute(container, path = location.hash || '#dashboard') {
  const route = routes[path] || routes['#dashboard'];
  route(container);
}

export function initRouter(container) {
  const update = () => renderRoute(container);
  window.addEventListener('hashchange', update);
  update();
}
