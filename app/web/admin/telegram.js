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
  const response = await request(`/api/telegram/accounts/${accountId}/enabled`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({enabled})});
  if (!response.ok) throw new Error('更新账号状态失败');
}

async function createSource(accountId, dialog) {
  const response = await request('/api/telegram/sources', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({account_id: accountId, telegram_chat_id: dialog.id, name: dialog.name || `Dialog #${dialog.id}`})});
  if (!response.ok) {
    let detail = '创建 Source 失败';
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
}

async function setSourceEnabled(sourceId, enabled) {
  const response = await request(`/api/telegram/sources/${sourceId}/enabled`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({enabled})});
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
  const labels = {accounts: '账号', dialogs: 'Dialogs', sessions: '凭据'};
  const page = document.createElement('div');
  page.className = 'admin-page';
  const header = document.createElement('header');
  header.className = 'admin-page-header';
  header.innerHTML = `<div><h1>Telegram / ${labels[section] || section}</h1></div>`;
  page.appendChild(header);
  container.appendChild(page);
  try {
    if (section === 'accounts') return await renderAccounts(page);
    if (section === 'dialogs') return await renderDialogs(page);
    if (section === 'sessions') return renderCredentials(page);
  } catch (error) {
    const box = document.createElement('div');
    box.className = 'admin-error';
    box.textContent = `加载失败：${error.message}`;
    page.appendChild(box);
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
    button.type = 'button'; button.textContent = account.enabled ? '禁用账号' : '启用账号';
    button.onclick = async () => { button.disabled = true; try { await setAccountEnabled(account.id, !account.enabled); await renderTelegram(container, 'accounts'); } catch (error) { alert(error.message); button.disabled = false; } };
    item.append(info, button); container.appendChild(item);
  }
}

async function renderDialogs(container) {
  const accounts = await loadAccounts();
  if (!accounts.length) { container.appendChild(panel('暂无 Telegram 账号')); return; }
  for (const account of accounts) {
    const item = panel(text(account.name, `账号 #${account.id}`));
    const toolbar = document.createElement('div'); toolbar.className = 'toolbar';
    const refresh = document.createElement('button'); refresh.type = 'button'; refresh.textContent = '刷新 Dialogs';
    const list = document.createElement('div');
    refresh.onclick = () => loadAndRenderDialogs(account, list, refresh);
    toolbar.appendChild(refresh); item.append(toolbar, list); container.appendChild(item);
    await loadAndRenderDialogs(account, list, refresh);
  }
}

async function loadAndRenderDialogs(account, list, button) {
  button.disabled = true; list.textContent = '加载中…';
  try {
    const dialogs = await loadDialogs(account.id);
    list.replaceChildren();
    if (!dialogs.length) { list.textContent = '暂无 Dialog'; return; }
    for (const dialog of dialogs) {
      const row = document.createElement('section'); row.className = 'panel dialog-row';
      const title = document.createElement('strong'); title.textContent = text(dialog.name, `Dialog #${dialog.id}`);
      const meta = document.createElement('div'); meta.className = 'meta';
      meta.textContent = `Chat ID：${dialog.id} · 类型：${text(dialog.entity_type, 'channel')} · Source：${dialog.source_enabled ? '已启用' : '未启用'}`;
      const actions = document.createElement('div'); actions.className = 'toolbar';
      const sourceId = dialog.source_id;
      const toggle = document.createElement('button'); toggle.type = 'button';
      toggle.textContent = dialog.source_enabled ? '禁用' : '启用';
      toggle.onclick = async () => {
        toggle.disabled = true;
        try {
          if (sourceId != null) await setSourceEnabled(sourceId, !dialog.source_enabled);
          else await createSource(account.id, dialog);
          await loadAndRenderDialogs(account, list, button);
        } catch (error) { alert(error.message); toggle.disabled = false; }
      };
      actions.appendChild(toggle);
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '删除';
      remove.disabled = Boolean(dialog.source_enabled);
      remove.title = remove.disabled ? '请先禁用 Source' : '删除 Dialog';
      remove.onclick = async () => {
        if (remove.disabled || !window.confirm('确定删除这个 Dialog 吗？')) return;
        remove.disabled = true;
        try { await deleteDialog(account.id, dialog.id); await loadAndRenderDialogs(account, list, button); }
        catch (error) { alert(error.message); remove.disabled = false; }
      };
      actions.appendChild(remove); row.append(title, meta, actions); list.appendChild(row);
    }
  } catch (error) { list.textContent = `加载失败：${error.message}`; }
  finally { button.disabled = false; }
}

function renderCredentials(container) {
  const item = panel('MTProto API 凭据');
  const message = document.createElement('p');
  message.textContent = '系统连接 Telegram MTProto 使用 TG_API_ID 与 TG_API_HASH。';
  const note = document.createElement('p'); note.className = 'meta';
  note.textContent = '当前凭据由服务器配置管理，后端尚未提供在线修改 API。这里不伪造 Session 管理功能。';
  item.append(message, note); container.appendChild(item);
}
