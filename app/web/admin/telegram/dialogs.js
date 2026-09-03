(() => {
  window.TGDriveAdmin = window.TGDriveAdmin || {};
  window.TGDriveAdmin.dialogs = {
    async load(accounts, request, setStatus) {
      const root = document.getElementById("telegram-dialogs-page");
      if (!root) return;
      root.replaceChildren();
      for (const account of accounts) {
        const response = await request(`/api/telegram/accounts/${account.id}/dialogs`);
        const dialogs = await response.json();
        const section = document.createElement("section");
        section.className = "panel";
        section.innerHTML = `<h3>${account.name || account.id}</h3>`;
        for (const dialog of dialogs) {
          const item = document.createElement("article");
          item.className = "card";
          item.textContent = `${dialog.name || dialog.id} (${dialog.source_enabled ? "已启用" : "未启用"})`;
          section.appendChild(item);
        }
        root.appendChild(section);
      }
    }
  };
})();
