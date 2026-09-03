(() => {
  window.TGDriveAdmin = window.TGDriveAdmin || {};

  function button(text, cls = "") {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = text;
    if (cls) b.className = cls;
    return b;
  }

  window.TGDriveAdmin.dialogs = {
    async load(accounts, request, setStatus, refreshSources) {
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
          item.innerHTML = `<div>${dialog.name || dialog.id}</div><div>${dialog.source_enabled ? "已启用" : "未启用"}</div>`;

          const actions = document.createElement("div");

          if (dialog.source_enabled && dialog.source_id) {
            const disable = button("禁用");
            disable.onclick = async () => {
              const r = await request(`/api/telegram/sources/${dialog.source_id}/enabled`, {
                method: "PUT",
                headers: {"Content-Type":"application/json"},
                body: JSON.stringify({enabled:false})
              });
              if (!r.ok) throw new Error("禁用失败");
              setStatus("Source 已禁用");
              await refreshSources();
            };
            actions.appendChild(disable);
          } else {
            const enable = button("启用");
            enable.onclick = async () => {
              const r = await request("/api/telegram/sources", {
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({account_id:account.id, telegram_chat_id:dialog.id, name:dialog.name || String(dialog.id)})
              });
              if (!r.ok) throw new Error("启用失败");
              setStatus("Source 已启用，等待扫描");
              await refreshSources();
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
  };
})();
