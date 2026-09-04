import { request } from './api.js';

function text(value, fallback = '-') {
  const result = String(value ?? '').trim();
  return result || fallback;
}

function panel(title) {
  const el = document.createElement('section');
  el.className = 'panel';
  const heading = document.createElement('h3');
  heading.textContent = title;
  el.appendChild(heading);
  return el;
}

async function loadAccounts() {
  const response = await request('/api/telegram/accounts');
  if (!response.ok) throw new Error('加载 Telegram 账号失败');
  return response.json();
}

async function loadDialogs(accountId) {
  const response = await request(`/api/telegram/accounts/${accountId}/dialogs`);
  if (!response.ok) throw new Error('加载 Dialogs 失败');
  return response.json();
}

async function setAccountEnabled(accountId, enabled) {
  const response = await request(`/api/telegram/accounts/${accountId}/enabled`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({enabled}),
  });
  if (!response.ok) throw new Error('更新账号状态失败');
}

async function setSourceEnabled(sourceId, enabled) {
  const response = await request(`/api/telegram/sources/${sourceId}/enabled`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({enabled}),
  });
  if (!response.ok) throw new Error('更新 Source 状态失败');
}

async function deleteDialog(accountId, chatId) {
  const response = await request(`/api/telegram/accounts/${accountId}/dialogs/${chatId}`, {method: 'DELETE'});
  if (!response.ok) {
    let message = '删除 Dialog 失败';
    try { const payload = await response.json(); if (payload.detail) message = payload.detail; } catch (_) {}
    throw new Error(message);
  }
}

export async function renderTelegram(container, section = 'dialogs') {
  container.replaceChildren();
  const title = document.createElement('h2');
  title.textContent = `Telegram / ${({accounts: '账号', dialogs: 'Dialogs', sessions: '会话'})[section] || section}`;
  container.appendChild(title);
  try {
    if (section === 'accounts') return await renderAccounts(container);
    if (section === 'dialogs') return await renderDialogs(container);
    if (section === 'sessions') return renderSessions(container);
  } catch (error) {
    const errorBox = document.createElement('div');
    errorBox.className = 'admin-error';
    errorBox.textContent = `加载失败：${error.message}`;
    container.appendChild(errorBox);
  }
}

async function renderAccounts(container) {
  const accounts = await loadAccounts();
  if (!accounts.length) { container.appendChild(panel('暂无 Telegram 账号')); return; }
  for (const account of accounts) {
    const item = panel(text(account.name, `账号 #${account.id}`));
    const info = document.createElement('p');
    info.textContent = `ID：${account.id} · 用户名：${text(account.username)} · 状态：${account.enabled ? '已启用' : '已禁用'}`;
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = account.enabled ? '禁用账号' : '启用账号';
    button.onclick = async () => {
      button.disabled = true;
      try {
        await setAccountEnabled(account.id, !account.enabled);
        await renderTelegram(container, 'accounts');
      } catch (error) { alert(error.message); button.disabled = false; }
    };
    item.append(info, button);
    container.appendChild(item);
  }
}

async function renderDialogs(container) {
  const accounts = await loadAccounts();
  if (!accounts.length) { container.appendChild(panel('暂无 Telegram 账号')); return; }
  for (const account of accounts) {
    const item = panel(text(account.name, `账号 #${account.id}`));
    const toolbar = document.createElement('div');
    toolbar.className = 'toolbar';
    const refresh = document.createElement('button');
    refresh.type = 'button';
    refresh.textContent = '刷新 Dialogs';
    const list = document.createElement('div');
    refresh.onclick = () => loadAndRenderDialogs(account, list, refresh);
    toolbar.appendChild(refresh);
    item.append(toolbar, list);
    container.appendChild(item);
    await loadAndRenderDialogs(account, list, refresh);
  }
}

async function loadAndRenderDialogs(account, list, button) {
  button.disabled = true;
  list.textContent = '加载中…';
  try {
    const dialogs = await loadDialogs(account.id);
    list.replaceChildren();
    if (!dialogs.length) { list.textContent = '暂无 Dialog'; return; }
    for (const dialog of dialogs) {
      const row = document.createElement('div');
      row.className = 'panel';
      const title = document.createElement('strong');
      title.textContent = text(dialog.title || dialog.name, `Dialog #${dialog.telegram_chat_id}`);
      const meta = document.createElement('div');
      meta.textContent = `类型：${text(dialog.type, 'unknown')} · 状态：${dialog.source_enabled ? '已启用' : '已禁用'}`;
      const actions = document.createElement('div');
      actions.className = 'toolbar';
      const sourceId = dialog.source_id;
      if (sourceId != null) {
        const toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.textContent = dialog.source_enabled ? '禁用' : '启用';
        toggle.onclick = async () => {
          toggle.disabled = true;
          try {
            await setSourceEnabled(sourceId, !dialog.source_enabled);
            await loadAndRenderDialogs(account, list, button);
          } catch (error) { alert(error.message); toggle.disabled = false; }
        };
        actions.appendChild(toggle);
      }
      const remove = document.createElement('button');
      remove.type = 'button';
      remove.textContent = '删除';
      remove.disabled = Boolean(dialog.source_enabled);
      remove.title = remove.disabled ? '请先禁用 Source' : '移入回收站';
      remove.onclick = async () => {
        if (remove.disabled || !window.confirm('确定删除这个 Dialog 吗？')) return;
        remove.disabled = true;
        try {
          await deleteDialog(account.id, dialog.telegram_chat_id);
          await loadAndRenderDialogs(account, list, button);
        } catch (error) { alert(error.message); remove.disabled = false; }
      };
      actions.appendChild(remove);
      row.append(title, meta, actions);
      list.appendChild(row);
    }
  } catch (error) {
    list.textContent = `加载失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function renderSessions(container) {
  const item = panel('Telegram 会话');
  item.appendChild(document.createTextNode('会话由 Telegram Client 管理。当前没有独立的 Session 管理 API。'));
  container.appendChild(item);
}
