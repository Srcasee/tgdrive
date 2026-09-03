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

  if (section === 'dialogs') return renderDialogs(container);
  if (section === 'accounts') return renderAccounts(container);
  if (section === 'sessions') return renderSessions(container);
}

async function loadAccounts() {
  const response = await request('/api/telegram/accounts');
  if (!response.ok) throw new Error('加载 Telegram accounts 失败');
  return response.json();
}

function createPanel(title) {
  const panel = document.createElement('section');
  panel.className = 'panel';
  const h = document.createElement('h3');
  h.textContent = title;
  panel.appendChild(h);
  return panel;
}

async function renderAccounts(container) {
  const accounts = await loadAccounts();
  for (const account of accounts) {
    const panel = createPanel(account.name || account.id);
    panel.insertAdjacentHTML('beforeend', `<p>ID: ${escape(account.id)}</p>`);
    container.appendChild(panel);
  }
}

async function renderDialogs(container) {
  const accounts = await loadAccounts();

  for (const account of accounts) {
    const panel = createPanel(account.name || account.id);
    const list = document.createElement('div');
    const button = document.createElement('button');
    button.textContent = '加载 Dialogs';

    button.onclick = async () => {
      list.textContent = '加载中...';
      try {
        const response = await request(`/api/telegram/accounts/${account.id}/dialogs`);
        if (!response.ok) throw new Error('加载 dialogs 失败');
        const dialogs = await response.json();

        list.replaceChildren();
        for (const dialog of dialogs) {
          const row = document.createElement('div');
          row.className = 'panel';

          const title = dialog.title || dialog.name || dialog.id;
          const type = dialog.type || 'unknown';
          const enabled = dialog.enabled ? 'Enabled' : 'Disabled';

          row.innerHTML = `
            <strong>${escape(title)}</strong>
            <div>Type: ${escape(type)}</div>
            <div>Source: ${enabled}</div>
          `;

          list.appendChild(row);
        }
      } catch (error) {
        list.textContent = error.message;
      }
    };

    panel.append(button, list);
    container.appendChild(panel);
  }
}

async function renderSessions(container) {
  const accounts = await loadAccounts();

  for (const account of accounts) {
    const panel = createPanel(account.name || account.id);
    panel.insertAdjacentHTML('beforeend', '<p>Session 状态由 Telegram client 管理。</p>');
    container.appendChild(panel);
  }
}
