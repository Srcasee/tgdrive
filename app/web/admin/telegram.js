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

function table(headers, rows) {
  const el = document.createElement('table');
  el.className = 'admin-table admin-detail-table';
  el.innerHTML = `<thead><tr>${headers.map((h) => `<th>${h}</th>`).join('')}</tr></thead>`;
  const body = document.createElement('tbody');
  for (const row of rows) {
    const tr = document.createElement('tr');
    for (const value of row) {
      const td = document.createElement('td');
      td.textContent = text(value);
      tr.appendChild(td);
    }
    body.appendChild(tr);
  }
  el.appendChild(body);
  return el;
}

async function loadAccounts() {
  const response = await request('/api/telegram/accounts');
  if (!response.ok) throw new Error('加载 Telegram 账号失败');
  return response.json();
}

async function loadAccountInfo(accountId) {
  const response = await request(`/api/telegram/accounts/${accountId}/info`);
  if (!response.ok) {
    let detail = '加载账号详细信息失败';
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
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
  const page = document.createElement('div'); page.className = 'admin-page';
  const header = document.createElement('header'); header.className = 'admin-page-header';
  header.innerHTML = `<div><h1>Telegram / ${labels[section] || section}</h1></div>`;
  page.appendChild(header); container.appendChild(page);
  try {
    if (section === 'accounts') return await renderAccounts(page);
    if (section === 'dialogs') return await renderDialogs(page);
    if (section === 'sessions') return renderCredentials(page);
  } catch (error) {
    const box = document.createElement('div'); box.className = 'admin-error'; box.textContent = `加载失败：${error.message}`; page.appendChild(box);
  }
}

async function renderAccounts(container) {
  const accounts = await loadAccounts();
  if (!accounts.length) { container.appendChild(panel('暂无 Telegram 账号')); return; }
  const wrap = panel('Telegram 账号');
  const list = document.createElement('div');
  for (const account of accounts) {
    const row = document.createElement('section'); row.className = 'account-detail-row';
    const actions = document.createElement('div'); actions.className = 'actions';
    const toggle = document.createElement('button'); toggle.type = 'button'; toggle.textContent = account.enabled ? '禁用账号' : '启用账号';
    const details = document.createElement('button'); details.type = 'button'; details.textContent = '刷新账号信息';
    const detailBox = document.createElement('div'); detailBox.className = 'detail-box';
    const summary = table(['字段', '值'], [
      ['数据库 ID', account.id], ['名称', account.name], ['用户名', account.username], ['启用状态', account.enabled ? '已启用' : '已禁用'],
    ]);
    detailBox.appendChild(summary);
    toggle.onclick = async () => {
      toggle.disabled = true;
      try {
        await setAccountEnabled(account.id, !account.enabled);
        account.enabled = !account.enabled;
        toggle.textContent = account.enabled ? '禁用账号' : '启用账号';
        summary.querySelector('tbody tr:nth-child(4) td:last-child').textContent = account.enabled ? '已启用' : '已禁用';
        detailBox.classList.remove('account-info-error');
      } catch (error) { alert(error.message); }
      finally { toggle.disabled = false; }
    };
    details.onclick = async () => {
      details.disabled = true; details.textContent = '读取中…';
      try {
        const info = await loadAccountInfo(account.id);
        const tg = info.telegram || {};
        detailBox.replaceChildren(table(['类别', '字段', '值'], [
          ['数据库', 'ID', info.id], ['数据库', '名称', info.name], ['数据库', '用户名', info.username], ['数据库', '启用', info.enabled ? '是' : '否'],
          ['运行时', '连接', info.connected ? '已连接' : '未连接'], ['运行时', 'DC ID', info.dc_id], ['运行时', '服务器', info.server_address], ['运行时', '端口', info.port], ['运行时', 'Session 名称', info.session_name],
          ['Telegram', '用户 ID', tg.id], ['Telegram', '名字', tg.first_name], ['Telegram', '姓氏', tg.last_name], ['Telegram', '用户名', tg.username], ['Telegram', '手机号', tg.phone], ['Telegram', '语言', tg.lang_code], ['Telegram', '状态类型', tg.status],
          ['Telegram', 'Bot', tg.bot ? '是' : '否'], ['Telegram', 'Premium', tg.premium ? '是' : '否'], ['Telegram', 'Verified', tg.verified ? '是' : '否'], ['Telegram', 'Restricted', tg.restricted ? '是' : '否'], ['Telegram', 'Scam', tg.scam ? '是' : '否'], ['Telegram', 'Fake', tg.fake ? '是' : '否'], ['Telegram', 'Support', tg.support ? '是' : '否'],
        ]));
      } catch (error) {
        detailBox.textContent = error.message;
        detailBox.classList.add('account-info-error');
      } finally { details.disabled = false; details.textContent = '刷新账号信息'; }
    };
    actions.append(toggle, details); row.append(summary, actions, detailBox); list.appendChild(row);
  }
  wrap.appendChild(list); container.appendChild(wrap);
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
    const tableEl = document.createElement('table'); tableEl.className = 'admin-table';
    tableEl.innerHTML = '<thead><tr><th>名称</th><th>Chat ID</th><th>类型</th><th>Source</th><th>操作</th></tr></thead>';
    const body = document.createElement('tbody');
    for (const dialog of dialogs) {
      const tr = document.createElement('tr');
      const sourceId = dialog.source_id;
      const status = () => `${dialog.source_enabled ? '已启用' : '未启用'}`;
      tr.innerHTML = `<td></td><td>${text(dialog.id)}</td><td>${text(dialog.entity_type, 'channel')}</td><td>${status()}</td><td></td>`;
      tr.firstElementChild.textContent = text(dialog.name, `Dialog #${dialog.id}`);
      const actions = tr.lastElementChild; actions.className = 'actions';
      const toggle = document.createElement('button'); toggle.type = 'button'; toggle.textContent = dialog.source_enabled ? '禁用' : '启用';
      toggle.onclick = async () => {
        toggle.disabled = true;
        try {
          if (sourceId != null) {
            await setSourceEnabled(sourceId, !dialog.source_enabled);
            dialog.source_enabled = !dialog.source_enabled;
          } else {
            await createSource(account.id, dialog);
            dialog.source_enabled = true;
          }
          tr.children[3].textContent = status();
          toggle.textContent = dialog.source_enabled ? '禁用' : '启用';
          remove.disabled = dialog.source_enabled; remove.title = remove.disabled ? '请先禁用 Source' : '删除 Dialog';
        } catch (error) { alert(error.message); }
        finally { toggle.disabled = false; }
      };
      actions.appendChild(toggle);
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '删除'; remove.disabled = Boolean(dialog.source_enabled); remove.title = remove.disabled ? '请先禁用 Source' : '删除 Dialog';
      remove.onclick = async () => {
        if (remove.disabled || !window.confirm('确定删除这个 Dialog 吗？')) return;
        remove.disabled = true;
        try { await deleteDialog(account.id, dialog.id); tr.remove(); }
        catch (error) { alert(error.message); remove.disabled = false; }
      };
      actions.appendChild(remove); body.appendChild(tr);
    }
    tableEl.appendChild(body); list.appendChild(tableEl);
  } catch (error) { list.textContent = `加载失败：${error.message}`; }
  finally { button.disabled = false; }
}

function renderCredentials(container) {
  const item = panel('MTProto API 凭据');
  const message = document.createElement('p'); message.textContent = '系统连接 Telegram MTProto 使用 TG_API_ID 与 TG_API_HASH。';
  const note = document.createElement('p'); note.className = 'meta'; note.textContent = '当前凭据由服务器配置管理，后端尚未提供在线修改 API。这里不伪造 Session 管理功能。';
  item.append(message, note); container.appendChild(item);
}
