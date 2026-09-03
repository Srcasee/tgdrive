(() => {
  window.TGDriveAdmin = window.TGDriveAdmin || {};

  window.TGDriveAdmin.sources = {
    async load(request) {
      const root = document.getElementById("telegram-sources-page");
      if (!root) return;
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
  };
})();
