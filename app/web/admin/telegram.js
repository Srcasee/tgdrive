import { request } from './api.js';

function escape(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  }[c]));
}

export async function renderTelegram(container, section = 'dialogs') {
  container.replaceChildren();

  const title = document.createElement('h2');
  title.textContent = `Telegram / ${section}`;
  container.appendChild(title);

  if (section === 'dialogs') {
    await renderDialogs(container);
  } else if (section === 'accounts') {
    await renderAccounts(container);
  } else if (section === 'sessions') {
    await renderSessions(container);
  }
}

async function loadAccounts() {
  const response = await request('/api/telegram/accounts');
  if (!response.ok) throw new Error('加载 Telegram accounts 失败');
  return response.json();
}

async function renderAccounts(container) {
  const accounts = await loadAccounts();
  const list = document.createElement('div');

  for (const account of accounts) {
    const item = document.createElement('section');
    item.className = 'panel';
    item.innerHTML = `
      <h3>${escape(account.name || account.id)}</h3>
      <p>ID: ${escape(account.id)}</p>
    `;
    list.appendChild(item);
  }

  container.appendChild(list);
}

async function renderDialogs(container) {
  const accounts = await loadAccounts();
  const list = document.createElement('div');

  for (const account of accounts) {
    const item = document.createElement('section');
    item.className = 'panel';
    item.innerHTML = `
      <h3>${escape(account.name || account.id)}</h3>
      <p>Dialog 管理</p>
      <button type="button">加载 Dialogs</button>
      <div class="dialogs-list"></div>
    `;

    const button = item.querySelector('button');
    const target = item.querySelector('.dialogs-list');
    button.onclick = async () => {
      target.textContent = '加载中...';
      try {
        const response = await request(`/api/telegram/accounts/${account.id}/dialogs`);
        if (!response.ok) throw new Error('加载 dialogs 失败');
        const dialogs = await response.json();
        target.innerHTML = dialogs.map(dialog => `
          <div>
            ${escape(dialog.title || dialog.name || dialog.id)}
            (${escape(dialog.type || 'unknown')})
          </div>
        `).join('');
      } catch (error) {
        target.textContent = error.message;
      }
    };

    list.appendChild(item);
  }

  container.appendChild(list);
}

async function renderSessions(container) {
  const accounts = await loadAccounts();
  const list = document.createElement('div');

  for (const account of accounts) {
    const item = document.createElement('section');
    item.className = 'panel';
    item.innerHTML = `
      <h3>${escape(account.name || account.id)}</h3>
      <p>Session 状态</p>
    `;
    list.appendChild(item);
  }

  container.appendChild(list);
}
