import { renderMenu } from './layout.js';
import { initRouter, navigate } from './router.js';

async function init() {
  const response = await fetch('/auth/me');
  const root = document.getElementById('content');

  if (!response.ok) {
    root.textContent = '需要登录';
    return;
  }

  const user = await response.json();
  if (user.role !== 'admin') {
    root.textContent = '无管理员权限';
    return;
  }

  renderLayout();
}

function renderLayout() {
  const menu = document.getElementById('menu');
  const content = document.getElementById('content');

  renderMenu(menu, navigate);
  initRouter(content);
}

init();
