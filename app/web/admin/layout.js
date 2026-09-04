export const menu = [
  { name: '仪表盘', path: '#dashboard' },
  { name: 'Telegram', children: [['账号', '#telegram/accounts'], ['Dialogs', '#telegram/dialogs'], ['会话', '#telegram/sessions']] },
  { name: '资源', children: [['来源', '#resources/sources'], ['文件', '#resources/files'], ['分类', '#resources/categories']] },
  { name: '扫描器', children: [['任务', '#scanner/tasks'], ['日志', '#scanner/logs'], ['设置', '#scanner/settings']] },
  { name: '下载', children: [['进行中', '#download/active'], ['历史', '#download/history']] },
  { name: '系统', children: [['配置', '#system/config'], ['API', '#system/api']] },
  { name: '回收站', path: '#recycle' },
];

export function renderMenu(container, onNavigate) {
  container.replaceChildren();
  for (const item of menu) {
    const title = document.createElement('div');
    title.className = 'menu-item';
    title.textContent = item.name;
    container.appendChild(title);
    if (item.children) {
      for (const [name, path] of item.children) {
        const child = document.createElement('div');
        child.className = 'menu-child';
        child.textContent = name;
        child.onclick = () => onNavigate(path);
        container.appendChild(child);
      }
    } else {
      title.onclick = () => onNavigate(item.path);
    }
  }
}
