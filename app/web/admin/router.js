import { renderTelegram } from './telegram.js';
import { renderResources } from './resources.js';

const routes = {
  '#dashboard': (container) => { container.textContent = 'Dashboard'; },
  '#telegram/accounts': (container) => renderTelegram(container, 'accounts'),
  '#telegram/dialogs': (container) => renderTelegram(container, 'dialogs'),
  '#telegram/sessions': (container) => renderTelegram(container, 'sessions'),
  '#resources/sources': (container) => renderResources(container, 'sources'),
  '#resources/files': (container) => renderResources(container, 'files'),
  '#resources/categories': (container) => renderResources(container, 'categories'),
  '#scanner/tasks': (container) => { container.textContent = 'Scanner Tasks'; },
  '#scanner/logs': (container) => { container.textContent = 'Scanner Logs'; },
  '#scanner/settings': (container) => { container.textContent = 'Scanner Settings'; },
  '#download/active': (container) => { container.textContent = 'Download Active'; },
  '#download/history': (container) => { container.textContent = 'Download History'; },
  '#system/config': (container) => { container.textContent = 'System Config'; },
  '#system/api': (container) => { container.textContent = 'System API'; },
  '#recycle': (container) => { container.textContent = 'Recycle Bin'; },
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
