import { renderMenu } from './layout.js';
import { initRouter, navigate } from './router.js';

async function init() {
  const root = document.getElementById('content');
  if (!root) return;

  try {
    const response = await fetch('/auth/me');
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
  } catch (error) {
    root.textContent = `管理后台加载失败：${error.message}`;
    console.error('Admin initialization failed', error);
  }
}

function renderLayout() {
  const menu = document.getElementById('menu');
  const content = document.getElementById('content');
  if (!menu || !content) return;

  renderMenu(menu, navigate);
  initRouter(content);
}

autoInit();

function autoInit() {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, {once: true});
  } else {
    init();
  }
}
