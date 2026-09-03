import { request } from './api.js';

const menu = [
  ['Dashboard', '#dashboard'],
  ['Telegram', '#telegram'],
  ['Resources', '#resources'],
  ['Scanner', '#scanner'],
  ['Download', '#download'],
  ['System', '#system'],
  ['Recycle Bin', '#recycle']
];

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
  const menuBox = document.getElementById('menu');
  menuBox.replaceChildren();
  for (const [name, hash] of menu) {
    const item = document.createElement('div');
    item.className = 'menu-item';
    item.textContent = name;
    item.onclick = () => {
      location.hash = hash;
      renderPage(hash);
    };
    menuBox.appendChild(item);
  }
  renderPage(location.hash || '#dashboard');
}

function renderPage(hash) {
  const content = document.getElementById('content');
  const pages = {
    '#dashboard': 'Dashboard',
    '#telegram': 'Telegram',
    '#resources': 'Resources',
    '#scanner': 'Scanner',
    '#download': 'Download',
    '#system': 'System',
    '#recycle': 'Recycle Bin'
  };
  content.textContent = pages[hash] || 'Dashboard';
}

init();
