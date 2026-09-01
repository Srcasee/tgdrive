(() => {
  const panelId = "telegram-admin-panel";

  function panelMarkup() {
    return `
      <section id="${panelId}" class="panel hidden">
        <h2>Telegram Source 管理</h2>
        <div id="telegram-admin-status" class="status"></div>
        <div class="toolbar" style="margin-top:12px">
          <button id="telegram-refresh" type="button">刷新账号 / Dialogs</button>
        </div>
        <div id="telegram-accounts" style="margin-top:12px"></div>
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

  async function loadAccounts() {
    setStatus("正在加载 Telegram 账号和 Dialogs……");
    const response = await request("/api/telegram/accounts");
    if (!response.ok) throw new Error("加载 Telegram 账号失败");
    const accounts = await response.json();
    const root = document.getElementById("telegram-accounts");
    root.replaceChildren();

    if (!accounts.length) {
      root.textContent = "暂无 Telegram 账号，请先执行 login-account.sh。";
      setStatus("");
      return;
    }

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

      const dialogBox = document.createElement("div");
      dialogBox.className = "grid";
      dialogBox.style.marginTop = "10px";
      card.appendChild(dialogBox);

      if (!account.enabled) {
        const note = document.createElement("div");
        note.className = "meta";
        note.textContent = "账号未启用，无法配置 Source。";
        dialogBox.appendChild(note);
      } else {
        try {
          const response = await request(`/api/telegram/accounts/${account.id}/dialogs`);
          if (!response.ok) throw new Error("加载 Dialogs 失败");
          const dialogs = await response.json();
          for (const dialog of dialogs) renderDialog(dialogBox, account, dialog);
          if (!dialogs.length) dialogBox.textContent = "没有已刷新的 Dialog。";
        } catch (error) {
          const note = document.createElement("div");
          note.className = "error";
          note.textContent = error.message;
          dialogBox.appendChild(note);
        }
      }
      root.appendChild(card);
    }
    setStatus("Telegram Dialogs 已刷新。", false);
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

    if (dialog.is_group || dialog.is_channel) {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = "资源候选";
      item.appendChild(badge);
    }

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
      } catch (error) {
        setStatus(error.message, true);
        add.disabled = false;
      }
    };
    item.appendChild(add);
    root.appendChild(item);
  }

  async function init() {
    const appPanel = document.getElementById("app-panel");
    if (!appPanel || document.getElementById(panelId)) return;

    const me = await fetch("/auth/me");
    if (!me.ok) return;
    const user = await me.json();
    if (user.role !== "admin") return;

    appPanel.insertAdjacentHTML("afterbegin", panelMarkup());
    document.getElementById(panelId).classList.remove("hidden");
    document.getElementById("telegram-refresh").addEventListener("click", () => loadAccounts().catch(error => setStatus(error.message, true)));
    await loadAccounts();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => init().catch(console.error));
  else init().catch(console.error);
})();
