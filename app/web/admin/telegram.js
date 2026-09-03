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

function panel(title) {
  const el = document.createElement('section');
  el.className = 'panel';
  el.innerHTML = `<h3>${escape(title)}</h3>`;
  return el;
}

async function renderAccounts(container) {
  for (const account of await loadAccounts()) {
    const item = panel(account.name || account.id);
    item.insertAdjacentHTML('beforeend', `<p>ID: ${escape(account.id)}</p>`);
    container.appendChild(item);
  }
}

async function setSourceEnabled(sourceId, enabled) {
  const response = await request(`/api/telegram/sources/${sourceId}/enabled`, {
    method: 'PUT',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({enabled})
  });
  if (!response.ok) throw new Error('更新 Source 状态失败');
}

async function deleteDialog(accountId, chatId) {
  const response = await request(`/api/telegram/accounts/${accountId}/dialogs/${chatId}`, {
    method: 'DELETE'
  });
  if (!response.ok) throw new Error('删除 Dialog 失败');
}

async function renderDialogs(container) {
  for (const account of await loadAccounts()) {
    const item = panel(account.name || account.id);
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
          const source = dialog.source || null;
          const enabled = Boolean(source?.enabled ?? dialog.enabled);

          row.innerHTML = `
            <strong>${escape(dialog.title || dialog.name || dialog.id)}</strong>
            <div>Type: ${escape(dialog.type || 'unknown')}</div>
            <div>Source: ${enabled ? 'Enabled' : 'Disabled'}</div>
          `;

          const actions = document.createElement('div');

          if (source) {
            const toggle = document.createElement('button');
            toggle.textContent = enabled ? '禁用' : '启用';
            toggle.onclick = async () => {
              try {
                await setSourceEnabled(source.id, !enabled);
                await button.onclick();
              } catch (e) {
                alert(e.message);
              }
            };
            actions.appendChild(toggle);
          }

          if (!enabled) {
            const remove = document.createElement('button');
            remove.textContent = '删除';
            remove.onclick = async () => {
              try {
                await deleteDialog(account.id, dialog.telegram_chat_id);
                await button.onclick();
              } catch (e) {
                alert(e.message);
              }
            };
            actions.appendChild(remove);
          }

          row.appendChild(actions);
          list.appendChild(row);
        }
      } catch (e) {
        list.textContent = e.message;
      }
    };

    item.append(button, list);
    container.appendChild(item);
  }
}

async function renderSessions(container) {
  for (const account of await loadAccounts()) {
    const item = panel(account.name || account.id);
    item.insertAdjacentHTML('beforeend', '<p>Session 状态由 Telegram client 管理。</p>');
    container.appendChild(item);
  }
}
