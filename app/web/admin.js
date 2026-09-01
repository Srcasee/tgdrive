(() => {
  const panelId = "telegram-admin-panel";
  let initialized = false;

  function panelMarkup() {
    return `
      <section id="${panelId}" class="panel hidden">
        <h2>Telegram Source 管理</h2>
        <div id="telegram-admin-status" class="status"></div>
        <div class="toolbar" style="margin-top:12px">
          <button id="telegram-refresh" type="button">刷新 Dialogs / Source</button>
          <button id="telegram-tab-dialogs" type="button">Dialogs</button>
          <button id="telegram-tab-sources" type="button">Source</button>
        </div>
        <div id="telegram-dialogs-panel" style="margin-top:12px"></div>
        <div id="telegram-sources-panel" style="margin-top:12px;display:none"></div>
      </section>`;
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

  function showTab(tab) {
    const dialogs = document.getElementById("telegram-dialogs-panel");
    const sources = document.getElementById("telegram-sources-panel");
    if (!dialogs || !sources) return;
    const showDialogs = tab === "dialogs";
    dialogs.style.display = showDialogs ? "" : "none";
    sources.style.display = showDialogs ? "none" : "";
  }

  async function loadDialogs(accounts) {
    const root = document.getElementById("telegram-dialogs-panel");
    root.replaceChildren();
    for (const account of accounts) {
      const card = document.createElement("div");
      card.className = "card";
      const title = document.createElement("h3");
      title.textContent = `${account.name || "Account"} · ${account.username || "未设置 username"}`;
      card.appendChild(title);

      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = `account_id=${account.id} · ${account.enabled ? "已启用" : "已禁用"}`;
      card.appendChild(meta);

      const box = document.createElement("div");
      box.className = "grid";
      box.style.marginTop = "10px";
      card.appendChild(box);

      if (!account.enabled) {
        const note = document.createElement("div");
        note.className = "meta";
        note.textContent = "账号未启用。";
        box.appendChild(note);
      } else {
        try {
          const response = await request(`/api/telegram/accounts/${account.id}/dialogs`);
          if (!response.ok) throw new Error("加载 Dialogs 失败");
          const dialogs = await response.json();
          for (const dialog of dialogs) renderDialog(box, account, dialog);
          if (!dialogs.length) box.textContent = "没有可配置的资源群组 / 频道。";
        } catch (error) {
          const note = document.createElement("div");
          note.className = "error";
          note.textContent = error.message;
          box.appendChild(note);
        }
      }
      root.appendChild(card);
    }
  }

  function renderDialog(root, account, dialog) {
    const item = document.createElement("div");
    item.className = "card";

    const title = document.createElement("div");
    title.className = "filename";
    title.textContent = dialog.name || `Chat ${dialog.id}`;
    item.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `id=${dialog.id} · type=${dialog.entity_type || "unknown"}${dialog.username ? ` · @${dialog.username}` : ""}${dialog.is_group ? " · group" : ""}${dialog.is_channel ? " · channel" : ""}`;
    item.appendChild(meta);

    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = "资源候选";
    item.appendChild(badge);

    const add = document.createElement("button");
    add.type = "button";
    add.textContent = "配置为 Source";
    add.onclick = async () => {
      add.disabled = true;
      try {
        const response = await request("/api/telegram/sources", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            account_id: account.id,
            telegram_chat_id: dialog.id,
            name: dialog.name || String(dialog.id),
          }),
        });
        if (!response.ok) {
          let detail = "创建 Source 失败";
          try { const payload = await response.json(); if (payload.detail) detail = payload.detail; } catch (_) {}
          throw new Error(detail);
        }
        add.textContent = "Source 已配置";
        setStatus(`已配置 Source：${dialog.name || dialog.id}`);
        await loadSources();
      } catch (error) {
        setStatus(error.message, true);
        add.disabled = false;
      }
    };
    item.appendChild(add);
    root.appendChild(item);
  }

  async function loadSources() {
    const root = document.getElementById("telegram-sources-panel");
    root.replaceChildren();
    const response = await request("/api/telegram/sources");
    if (!response.ok) throw new Error("加载 Source 失败");
    const sources = await response.json();
    if (!sources.length) {
      root.textContent = "暂无已启用 Source。请在 Dialogs 页配置资源群组 / 频道。";
      return;
    }
    for (const source of sources) {
      const item = document.createElement("div");
      item.className = "card";
      const title = document.createElement("div");
      title.className = "filename";
      title.textContent = source.name || String(source.telegram_chat_id);
      item.appendChild(title);
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = `account=${source.account_name || source.account_id} · chat_id=${source.telegram_chat_id} · status=${source.scan_status || "idle"}`;
      item.appendChild(meta);
      root.appendChild(item);
    }
  }

  async function loadAccounts() {
    setStatus("正在加载 Telegram Dialogs / Source……");
    const response = await request("/api/telegram/accounts");
    if (!response.ok) throw new Error("加载 Telegram 账号失败");
    const accounts = await response.json();
    await loadDialogs(accounts);
    await loadSources();
    setStatus("Telegram Dialogs / Source 已刷新。", false);
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
    appPanel.insertAdjacentHTML("afterbegin", panelMarkup());
    document.getElementById(panelId).classList.remove("hidden");
    document.getElementById("telegram-refresh").addEventListener("click", () => loadAccounts().catch(error => setStatus(error.message, true)));
    document.getElementById("telegram-tab-dialogs").addEventListener("click", () => showTab("dialogs"));
    document.getElementById("telegram-tab-sources").addEventListener("click", () => showTab("sources"));
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
