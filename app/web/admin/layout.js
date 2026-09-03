export const menu = [
  {
    name: "Dashboard",
    path: "#dashboard",
  },
  {
    name: "Telegram",
    children: [
      ["Accounts", "#telegram/accounts"],
      ["Dialogs", "#telegram/dialogs"],
      ["Sessions", "#telegram/sessions"],
    ],
  },
  {
    name: "Resources",
    children: [
      ["Sources", "#resources/sources"],
      ["Files", "#resources/files"],
      ["Categories", "#resources/categories"],
    ],
  },
  {
    name: "Scanner",
    children: [
      ["Tasks", "#scanner/tasks"],
      ["Logs", "#scanner/logs"],
      ["Settings", "#scanner/settings"],
    ],
  },
  {
    name: "Download",
    children: [
      ["Active", "#download/active"],
      ["History", "#download/history"],
    ],
  },
  {
    name: "System",
    children: [
      ["Config", "#system/config"],
      ["API", "#system/api"],
    ],
  },
  {
    name: "Recycle Bin",
    path: "#recycle",
  },
];

export function renderMenu(container, onNavigate) {
  container.replaceChildren();

  for (const item of menu) {
    const title = document.createElement("div");
    title.className = "menu-item";
    title.textContent = item.name;
    container.appendChild(title);

    if (item.children) {
      for (const [name, path] of item.children) {
        const child = document.createElement("div");
        child.className = "menu-child";
        child.textContent = name;
        child.onclick = () => onNavigate(path);
        container.appendChild(child);
      }
    } else {
      title.onclick = () => onNavigate(item.path);
    }
  }
}
