import { request } from './api.js';

function escape(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

export async function renderTelegram(container, section = 'dialogs') {
  container.innerHTML = '';

  const title = document.createElement('h2');
  title.textContent = `Telegram / ${section}`;
  container.appendChild(title);

  if (section === 'dialogs') {
    await renderDialogs(container);
    return;
  }

  container.insertAdjacentHTML('beforeend', `<p>${escape(section)} 管理模块</p>`);
}

async function renderDialogs(container) {
  const status = document.createElement('div');
  status.textContent = '加载 Dialogs...';
  container.appendChild(status);

  try {
    const response = await request('/api/telegram/accounts');
    if (!response.ok) throw new Error('加载 Telegram accounts 失败');

    const accounts = await response.json();
    const list = document.createElement('div');
    list.innerHTML = '';

    for (const account of accounts) {
      const item = document.createElement('section');
      item.className = 'panel';
      item.innerHTML = `<h3>${escape(account.name || account.id)}</h3><p>Account ID: ${escape(account.id)}</p>`;
      list.appendChild(item);
    }

    status.remove();
    container.appendChild(list);
  } catch (error) {
    status.textContent = error.message;
  }
}
