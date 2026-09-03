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

  function panelMarkup() {
    return `<section id="${panelId}" class="panel hidden">
      <h2>Telegram 管理</h2>
      <div id="telegram-admin-status" class="status"></div>
      <button id="telegram-reconcile" type="button">立即同步 Dialog</button>
      <div id="telegram-dialogs-page"></div>
      <div id="telegram-sources-page"></div>
    </section>`;
  }

  async function refreshSources() {
    await window.TGDriveAdmin.sources.load(request);
  }

  async function refreshAdminState(accounts) {
    await window.TGDriveAdmin.dialogs.load(accounts, request, setStatus, refreshSources);
    await refreshSources();
  }

  async function loadAccounts() {
    const response = await request("/api/telegram/accounts");
    if (!response.ok) throw new Error("加载账号失败");
    const accounts = await response.json();
    await refreshAdminState(accounts);
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
