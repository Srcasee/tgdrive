import { renderTelegram } from './telegram.js';

const routes = {
  "#dashboard": () => 'Dashboard',
  "#telegram/accounts": () => renderTelegram(document.getElementById('content'), 'accounts'),
  "#telegram/dialogs": () => renderTelegram(document.getElementById('content'), 'dialogs'),
  "#telegram/sessions": () => renderTelegram(document.getElementById('content'), 'sessions'),
  "#resources/sources": () => 'Resources Sources',
  "#resources/files": () => 'Resources Files',
  "#resources/categories": () => 'Resources Categories',
  "#scanner/tasks": () => 'Scanner Tasks',
  "#scanner/logs": () => 'Scanner Logs',
  "#scanner/settings": () => 'Scanner Settings',
  "#download/active": () => 'Download Active',
  "#download/history": () => 'Download History',
  "#system/config": () => 'System Config',
  "#system/api": () => 'System API',
  "#recycle": () => 'Recycle Bin',
};

export function navigate(path) {
  location.hash = path;
}

export function renderRoute(container, path = location.hash || '#dashboard') {
  const route = routes[path] || routes['#dashboard'];
  const result = route();
  if (typeof result === 'string') container.textContent = result;
}

export function initRouter(container) {
  const update = () => renderRoute(container);
  window.addEventListener('hashchange', update);
  update();
}
