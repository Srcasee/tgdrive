const routes = {
  "#dashboard": "Dashboard",
  "#telegram/accounts": "Telegram Accounts",
  "#telegram/dialogs": "Telegram Dialogs",
  "#telegram/sessions": "Telegram Sessions",
  "#resources/sources": "Resources Sources",
  "#resources/files": "Resources Files",
  "#resources/categories": "Resources Categories",
  "#scanner/tasks": "Scanner Tasks",
  "#scanner/logs": "Scanner Logs",
  "#scanner/settings": "Scanner Settings",
  "#download/active": "Download Active",
  "#download/history": "Download History",
  "#system/config": "System Config",
  "#system/api": "System API",
  "#recycle": "Recycle Bin",
};

export function navigate(path) {
  location.hash = path;
}

export function renderRoute(container, path = location.hash || "#dashboard") {
  container.textContent = routes[path] || routes["#dashboard"];
}

export function initRouter(container) {
  const update = () => renderRoute(container);
  window.addEventListener("hashchange", update);
  update();
}
