import { request } from './api.js';

async function init() {
  const root = document.getElementById('admin-app');
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

  root.innerHTML = `
    <h1>TGDrive Admin</h1>
    <nav>
      <a href="#dashboard">Dashboard</a>
      <a href="#telegram/dialogs">Dialogs</a>
      <a href="#resources/sources">Sources</a>
    </nav>
    <main id="admin-content"></main>
  `;
}

init();
