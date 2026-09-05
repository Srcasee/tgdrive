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

async function setAccountEnabled(accountId, enabled) {
  const response = await request(`/api/telegram/accounts/${accountId}/enabled`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({enabled}),
  });
  if (!response.ok) {
    let detail = '更新账号状态失败';
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

async function createSource(accountId, dialog) {
  const response = await request('/api/telegram/sources', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({account_id: accountId, telegram_chat_id: dialog.id, name: dialog.name || `Dialog #${dialog.id}`}),
  });
  if (!response.ok) {
    let detail = '创建 Source 失败';
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
}

async function setSourceEnabled(sourceId, enabled) {
  const response = await request(`/api/telegram/sources/${sourceId}/enabled`, {
    method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({enabled}),
  });
  if (!response.ok) throw new Error('更新 Source 状态失败');
}

async function deleteDialog(accountId, chatId) {
  const response = await request(`/api/telegram/accounts/${accountId}/dialogs/${chatId}`, {method: 'DELETE'});
  if (!response.ok) {
    let message = '删除 Dialog 失败';
    try { message = (await response.json()).detail || message; } catch (_) {}
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

function applyAccountRow(tr, account) {
  const values = [
    account.id,
    account.enabled ? '已启用' : '已禁用',
    account.server_address,
    account.port,
    account.session_name,
    account.telegram_user_id,
    account.telegram_username || account.username,
    account.telegram_phone,
  ];
  values.forEach((value, index) => { tr.children[index].textContent = text(value); });
}

async function renderAccounts(container) {
  const accounts = await loadAccounts();
  if (!accounts.length) { container.appendChild(panel('暂无 Telegram 账号')); return; }

  const wrap = panel('Telegram 账号');
  const el = document.createElement('table');
  el.className = 'admin-table admin-detail-table';
  el.innerHTML = '<thead><tr><th>数据库 ID</th><th>启用状态</th><th>服务器</th><th>端口</th><th>Session 名称</th><th>用户 ID</th><th>用户名</th><th>手机号</th><th>操作</th></tr></thead>';
  const body = document.createElement('tbody');

  for (const account of accounts) {
    const tr = document.createElement('tr');
    for (let i = 0; i < 8; i += 1) tr.appendChild(document.createElement('td'));
    applyAccountRow(tr, account);

    const action = document.createElement('td');
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.textContent = account.enabled ? '禁用账号' : '启用账号';
    toggle.onclick = async () => {
      toggle.disabled = true;
      try {
        const updated = await setAccountEnabled(account.id, !account.enabled);
        Object.assign(account, updated);
        applyAccountRow(tr, account);
        toggle.textContent = account.enabled ? '禁用账号' : '启用账号';
        if (updated.discovery_error) {
          alert(`账号已启用，但 Dialog discovery 失败：${updated.discovery_error}`);
        }
      } catch (error) {
        alert(error.message);
      } finally {
        toggle.disabled = false;
      }
    };
    action.appendChild(toggle);
    tr.appendChild(action);
    body.appendChild(tr);
  }
  el.appendChild(body);
  wrap.appendChild(el);
  container.appendChild(wrap);
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
    if (!account.enabled) { list.textContent = '账号已禁用，忽略 Dialogs。'; return; }
    if (!dialogs.length) { list.textContent = '暂无 Dialog；请先在“账号”中执行一次启用以触发 discovery。'; return; }
    const tableEl = document.createElement('table'); tableEl.className = 'admin-table';
    tableEl.innerHTML = '<thead><tr><th>名称</th><th>Chat ID</th><th>类型</th><th>Source</th><th>操作</th></tr></thead>';
    const body = document.createElement('tbody');
    for (const dialog of dialogs) {
      const tr = document.createElement('tr');
      tr.innerHTML = '<td></td><td></td><td></td><td></td><td></td>';
      tr.children[0].textContent = text(dialog.name, `Dialog #${dialog.id}`);
      tr.children[1].textContent = text(dialog.id);
      tr.children[2].textContent = text(dialog.entity_type, 'channel');
      tr.children[3].textContent = dialog.source_enabled ? '已启用' : '未启用';
      const actions = tr.lastElementChild; actions.className = 'actions';
      const toggle = document.createElement('button'); toggle.type = 'button'; toggle.textContent = dialog.source_enabled ? '禁用' : '启用';
      toggle.onclick = async () => {
        toggle.disabled = true;
        try {
          if (dialog.source_id != null) {
            await setSourceEnabled(dialog.source_id, !dialog.source_enabled);
            dialog.source_enabled = !dialog.source_enabled;
          } else {
            await createSource(account.id, dialog);
            dialog.source_enabled = true;
          }
          tr.children[3].textContent = dialog.source_enabled ? '已启用' : '未启用';
          toggle.textContent = dialog.source_enabled ? '禁用' : '启用';
          remove.disabled = dialog.source_enabled;
        } catch (error) { alert(error.message); }
        finally { toggle.disabled = false; }
      };
      actions.appendChild(toggle);
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '删除';
      remove.disabled = Boolean(dialog.source_enabled);
      remove.onclick = async () => {
        if (remove.disabled || !window.confirm('确定删除这个 Dialog 吗？')) return;
        remove.disabled = true;
        try { await deleteDialog(account.id, dialog.id); tr.remove(); }
        catch (error) { alert(error.message); remove.disabled = false; }
      };
      actions.appendChild(remove);
      body.appendChild(tr);
    }
    tableEl.appendChild(body); list.appendChild(tableEl);
  } catch (error) {
    list.textContent = `加载失败：${error.message}`;
  } finally {
    button.disabled = false;
  }
}

function renderCredentials(container) {
  const item = panel('MTProto API 凭据');
  const message = document.createElement('p'); message.textContent = '系统连接 Telegram MTProto 使用 TG_API_ID 与 TG_API_HASH。';
  const note = document.createElement('p'); note.className = 'meta'; note.textContent = '当前凭据由服务器配置管理，后端尚未提供在线修改 API。这里不伪造 Session 管理功能。';
  item.append(message, note); container.appendChild(item);
}
