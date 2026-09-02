(() => {
  const panelId = "telegram-admin-panel";
  let initialized = false;

  function panelMarkup() {
    return `
      <section id="${panelId}" class="panel hidden">
        <h2>Telegram 管理</h2>
        <div id="telegram-admin-status" class="status"></div>
        <div class="telegram-admin-layout">
          <aside class="telegram-admin-sidebar">
            <button id="telegram-nav-dialogs" class="telegram-nav active" type="button">Dialogs</button>
            <button id="telegram-nav-sources" class="telegram-nav" type="button">Source</button>
            <button id="telegram-reconcile" class="telegram-nav" type="button">立即同步</button>
          </aside>
          <div class="telegram-admin-content">
            <div id="telegram-dialogs-page"></div>
            <div id="telegram-sources-page" class="hidden"></div>
          </div>
        </div>
      </section>`;
  }

  function injectStyles() {
    if (document.getElementById("telegram-admin-styles")) return;
    const style = document.createElement("style");
    style.id = "telegram-admin-styles";
    style.textContent = `
      .telegram-admin-layout { display:grid; grid-template-columns:160px minmax(0,1fr); gap:18px; margin-top:12px; }
      .telegram-admin-sidebar { display:flex; flex-direction:column; gap:8px; border-right:1px solid color-mix(in srgb, CanvasText 15%, transparent); padding-right:12px; }
      .telegram-nav { text-align:left; width:100%; }
      .telegram-nav.active { font-weight:700; }
      .telegram-admin-content { min-width:0; }
      .telegram-dialog-actions { display:flex; gap:8px; flex-wrap:wrap; }
      @media (max-width:700px) {
        .telegram-admin-layout { grid-template-columns:1fr; }
        .telegram-admin-sidebar { border-right:0; border-bottom:1px solid color-mix(in srgb, CanvasText 15%, transparent); padding:0 0 12px; flex-direction:row; }
        .telegram-nav { width:auto; }
      }
    `;
    document.head.appendChild(style);
  }

  async function request(url, options = {}) {
    const response = await fetch(url, options);
    if (response.status === 401) throw new Error("authentication required");
    return response;
  }

  function setStatus(message, error = false) {
    const box = document.getElementById("telegram-admin-status");
    if (!box) return;
    box.textContent = message || "";
    box.className = error ? "status error" : "status";
  }

  function showPage(page) {
    const dialogs = document.getElementById("telegram-dialogs-page");
    const sources = document.getElementById("telegram-sources-page");
    const navDialogs = document.getElementById("telegram-nav-dialogs");
    const navSources = document.getElementById("telegram-nav-sources");
    if (!dialogs || !sources) return;
    const isDialogs = page === "dialogs";
    dialogs.classList.toggle("hidden", !isDialogs);
    sources.classList.toggle("hidden", isDialogs);
    navDialogs?.classList.toggle("active", isDialogs);
    navSources?.classList.toggle("active", !isDialogs);
  }

  function button(text, className = "") {
    const el = document.createElement("button");
    el.type = "button";
    el.textContent = text;
    if (className) el.className = className;
    return el;
  }

  async function setSourceEnabled(sourceId, enabled, item) {
    const buttons = item.querySelectorAll("button");
    buttons.forEach(b => b.disabled = true);
    try {
      const response = await request(`/api/telegram/sources/${sourceId}/enabled`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
      });
      if (!response.ok) throw new Error(enabled ? "启用 Source 失败" : "禁用 Source 失败");
      setStatus(enabled ? "Source 已启用，Scanner 将立即处理。" : "Source 已禁用，Scanner 已停止处理该来源。 ");
      await loadAccounts();
    } catch (error) {
      setStatus(error.message, true);
      buttons.forEach(b => b.disabled = false);
    }
  }

  async function enableDialog(account, dialog, item) {
    const buttons = item.querySelectorAll("button");
    buttons.forEach(b => b.disabled = true);
    try {
      const response = await request("/api/telegram/sources", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ account_id: account.id, telegram_chat_id: dialog.id, name: dialog.name || String(dialog.id) }),
      });
      if (!response.ok) {
        let detail = "启用 Source 失败";
        try { const payload = await response.json(); if (payload.detail) detail = payload.detail; } catch (_) {}
        throw new Error(detail);
      }
      setStatus(`已启用：${dialog.name || dialog.id}，Scanner 将立即启动。`);
      await loadAccounts();
    } catch (error) {
      setStatus(error.message, true);
      buttons.forEach(b => b.disabled = false);
    }
  }

  async function deleteDialog(account, dialog, item) {
    if (!window.confirm(`确定删除 Dialog“${dialog.name || dialog.id}”吗？这会同时删除对应 Source 配置。`)) return;
    const buttons = item.querySelectorAll("button");
    buttons.forEach(b => b.disabled = true);
    try {
      const response = await request(`/api/telegram/accounts/${account.id}/dialogs/${dialog.id}`, { method: "DELETE" });
      if (!response.ok) {
        let detail = "删除 Dialog 失败";
        try { const payload = await response.json(); if (payload.detail) detail = payload.detail; } catch (_) {}
        throw new Error(detail);
      }
      setStatus(`已删除 Dialog：${dialog.name || dialog.id}`);
      await loadAccounts();
    } catch (error) {
      setStatus(error.message, true);
      buttons.forEach(b => b.disabled = false);
    }
  }

  function renderDialog(root, account, dialog) {
    const item = document.createElement("article");
    item.className = "card";
    const title = document.createElement("div");
    title.className = "filename";
    title.textContent = dialog.name || `Chat ${dialog.id}`;
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `id=${dialog.id} · type=${dialog.entity_type || "unknown"}${dialog.username ? ` · @${dialog.username}` : ""}${dialog.is_group ? " · group" : ""}${dialog.is_channel ? " · channel" : ""}`;
    const badges = document.createElement("div");
    badges.className = "badges";
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = dialog.source_enabled ? "已启用 Source" : "未启用";
    badges.appendChild(badge);
    const actions = document.createElement("div");
    actions.className = "telegram-dialog-actions";

    if (dialog.source_enabled && dialog.source_id) {
      const disable = button("禁用");
      disable.onclick = () => setSourceEnabled(dialog.source_id, false, item);
      actions.appendChild(disable);
    } else {
      const enable = button("启用");
      enable.onclick = () => enableDialog(account, dialog, item);
      actions.appendChild(enable);
    }

    const del = button("删除", "danger");
    del.onclick = () => deleteDialog(account, dialog, item);
    actions.appendChild(del);
    item.append(title, meta, badges, actions);
    root.appendChild(item);
  }

  async function loadDialogs(accounts) {
    const root = document.getElementById("telegram-dialogs-page");
    root.replaceChildren();
    for (const account of accounts) {
      const card = document.createElement("section");
      card.className = "panel";
      const title = document.createElement("h3");
      title.textContent = `${account.name || "Account"} · ${account.username || "未设置 username"}`;
      card.appendChild(title);
      if (!account.enabled) {
        const note = document.createElement("div");
        note.className = "meta";
        note.textContent = "账号未启用。";
        card.appendChild(note);
      } else {
        try {
          const response = await request(`/api/telegram/accounts/${account.id}/dialogs`);
          if (!response.ok) throw new Error("加载 Dialogs 失败");
          const dialogs = await response.json();
          const grid = document.createElement("div");
          grid.className = "grid";
          for (const dialog of dialogs) renderDialog(grid, account, dialog);
          if (!dialogs.length) grid.textContent = "没有可配置的资源群组 / 频道。";
          card.appendChild(grid);
        } catch (error) {
          const note = document.createElement("div");
          note.className = "error";
          note.textContent = error.message;
          card.appendChild(note);
        }
      }
      root.appendChild(card);
    }
  }

  async function deleteSource(sourceId, name, item) {
    if (!window.confirm(`确定删除 Source“${name}”吗？`)) return;
    item.querySelectorAll("button").forEach(b => b.disabled = true);
    try {
      const response = await request(`/api/telegram/sources/${sourceId}`, { method: "DELETE" });
      if (!response.ok) throw new Error("删除 Source 失败");
      setStatus(`已删除 Source：${name}`);
      await loadAccounts();
    } catch (error) {
      setStatus(error.message, true);
      item.querySelectorAll("button").forEach(b => b.disabled = false);
    }
  }

  async function loadSources() {
    const root = document.getElementById("telegram-sources-page");
    root.replaceChildren();
    const response = await request("/api/telegram/sources");
    if (!response.ok) throw new Error("加载 Source 失败");
    const sources = await response.json();
    if (!sources.length) {
      root.textContent = "暂无已启用 Source。请在 Dialogs 页点击“启用”。";
      return;
    }
    const grid = document.createElement("div");
    grid.className = "grid";
    for (const source of sources) {
      const item = document.createElement("article");
      item.className = "card";
      const title = document.createElement("div");
      title.className = "filename";
      title.textContent = source.name || String(source.telegram_chat_id);
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = `account=${source.account_name || source.account_id} · chat_id=${source.telegram_chat_id} · status=${source.scan_status || "idle"}`;
      const actions = document.createElement("div");
      actions.className = "actions";
      const disable = button("禁用");
      disable.onclick = () => setSourceEnabled(source.id, false, item);
      const del = button("删除", "danger");
      del.onclick = () => deleteSource(source.id, source.name || source.telegram_chat_id, item);
      actions.append(disable, del);
      item.append(title, meta, actions);
      grid.appendChild(item);
    }
    root.appendChild(grid);
  }

  async function loadAccounts() {
    setStatus("正在刷新 Telegram Dialogs / Source……");
    const response = await request("/api/telegram/accounts");
    if (!response.ok) throw new Error("加载 Telegram 账号失败");
    const accounts = await response.json();
    await loadDialogs(accounts);
    await loadSources();
    setStatus("Telegram 管理信息已刷新。", false);
  }

  async function reconcile() {
    const buttonEl = document.getElementById("telegram-reconcile");
    buttonEl.disabled = true;
    try {
      const response = await request("/api/telegram/reconcile", { method: "POST" });
      if (!response.ok) throw new Error("触发同步失败");
      setStatus("已触发 Telegram reconciliation，正在同步 Dialogs……");
      await new Promise(resolve => setTimeout(resolve, 800));
      await loadAccounts();
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      buttonEl.disabled = false;
    }
  }

  async function init() {
    if (initialized) return;
    const appPanel = document.getElementById("app-panel");
    if (!appPanel || appPanel.classList.contains("hidden")) return;
    const me = await fetch("/auth/me");
    if (!me.ok) return;
    const user = await me.json();
    if (user.role !== "admin") return;
    initialized = true;
    injectStyles();
    appPanel.insertAdjacentHTML("afterbegin", panelMarkup());
    document.getElementById(panelId).classList.remove("hidden");
    document.getElementById("telegram-nav-dialogs").addEventListener("click", () => showPage("dialogs"));
    document.getElementById("telegram-nav-sources").addEventListener("click", () => showPage("sources"));
    document.getElementById("telegram-reconcile").addEventListener("click", () => reconcile().catch(error => setStatus(error.message, true)));
    await loadAccounts();
  }

  function watchLoginState() {
    const appPanel = document.getElementById("app-panel");
    if (!appPanel) return;
    const observer = new MutationObserver(() => init().catch(console.error));
    observer.observe(appPanel, { attributes: true, attributeFilter: ["class"] });
    init().catch(console.error);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", watchLoginState);
  else watchLoginState();
})();
