(() => {
  const panelId = "telegram-admin-panel";
  let initialized = false;

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

  function button(text, cls = "") {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = text;
    if (cls) b.className = cls;
    return b;
  }

  function panelMarkup() {
    return `<section id="${panelId}" class="panel hidden">
      <h2>Telegram 管理</h2>
      <div id="telegram-admin-status" class="status"></div>
      <button id="telegram-reconcile" type="button">立即同步 Dialog</button>
      <div id="telegram-dialogs-page"></div>
      <div id="telegram-sources-page"></div>
    </section>`;
  }

  async function refreshAdminState(accounts) {
    await loadDialogs(accounts);
    await loadSources();
  }

  async function loadAccounts() {
    const response = await request("/api/telegram/accounts");
    if (!response.ok) throw new Error("加载账号失败");
    const accounts = await response.json();
    await refreshAdminState(accounts);
  }

  async function loadDialogs(accounts) {
    const root = document.getElementById("telegram-dialogs-page");
    root.replaceChildren();
    for (const account of accounts) {
      const dialogs = await (await request(`/api/telegram/accounts/${account.id}/dialogs`)).json();
      const section = document.createElement("section");
      section.className = "panel";
      section.innerHTML = `<h3>${account.name || account.id}</h3>`;
      for (const dialog of dialogs) {
        const item = document.createElement("article");
        item.className = "card";
        item.innerHTML = `<div>${dialog.name || dialog.id}</div><div>${dialog.source_enabled ? "已启用" : "未启用"}</div>`;
        const actions = document.createElement("div");

        if (dialog.source_enabled && dialog.source_id) {
          const disable = button("禁用");
          disable.onclick = async () => {
            disable.disabled = true;
            const r = await request(`/api/telegram/sources/${dialog.source_id}/enabled`, {
              method: "PUT",
              headers: {"Content-Type":"application/json"},
              body: JSON.stringify({enabled:false})
            });
            if (!r.ok) throw new Error("禁用失败");
            setStatus("Source 已禁用");
            await loadAccounts();
          };
          actions.appendChild(disable);
        } else {
          const enable = button("启用");
          enable.onclick = async () => {
            enable.disabled = true;
            const r = await request("/api/telegram/sources", {
              method:"POST",
              headers:{"Content-Type":"application/json"},
              body:JSON.stringify({account_id:account.id, telegram_chat_id:dialog.id, name:dialog.name || String(dialog.id)})
            });
            if (!r.ok) throw new Error("启用失败");
            setStatus("Source 已启用，等待扫描");
            await loadAccounts();
          };
          actions.appendChild(enable);
        }

        if (!dialog.source_enabled) {
          const del = button("删除", "danger");
          del.onclick = async () => {
            if (!confirm("确认删除 Dialog？")) return;
            const r = await request(`/api/telegram/accounts/${account.id}/dialogs/${dialog.id}`, {method:"DELETE"});
            if (!r.ok) throw new Error("删除失败");
            item.remove();
          };
          actions.appendChild(del);
        }
        item.appendChild(actions);
        section.appendChild(item);
      }
      root.appendChild(section);
    }
  }

  async function loadSources() {
    const root = document.getElementById("telegram-sources-page");
    root.replaceChildren();
    const response = await request("/api/telegram/sources");
    if (!response.ok) return;
    const sources = await response.json();
    for (const source of sources) {
      const item = document.createElement("article");
      item.className = "card";
      item.textContent = `${source.name || source.telegram_chat_id} (${source.scan_status || "idle"})`;
      root.appendChild(item);
    }
  }

  async function reconcile() {
    await request("/api/telegram/reconcile", {method:"POST"});
    setStatus("已触发 Dialog 同步");
    await new Promise(r => setTimeout(r, 800));
    await loadAccounts();
  }

  async function init() {
    if (initialized) return;
    const app = document.getElementById("app-panel");
    if (!app) return;
    const me = await fetch("/auth/me");
    if (!me.ok) return;
    const user = await me.json();
    if (user.role !== "admin") return;
    initialized = true;
    app.insertAdjacentHTML("afterbegin", panelMarkup());
    document.getElementById(panelId).classList.remove("hidden");
    document.getElementById("telegram-reconcile").onclick = () => reconcile().catch(e => setStatus(e.message,true));
    await loadAccounts();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
