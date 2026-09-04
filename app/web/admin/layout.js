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

  const brand = document.createElement('div');
  brand.className = 'menu-brand';
  const title = document.createElement('strong');
  title.textContent = 'TGDrive Admin';
  const subtitle = document.createElement('small');
  subtitle.textContent = '管理后台';
  brand.append(title, subtitle);
  container.appendChild(brand);

  for (const item of menu) {
    if (item.children) {
      const group = document.createElement('div');
      group.className = 'menu-group';
      const section = document.createElement('div');
      section.className = 'menu-section';
      section.textContent = item.name;
      group.appendChild(section);
      for (const [name, path] of item.children) {
        const child = document.createElement('div');
        child.className = 'menu-child';
        child.dataset.path = path;
        child.textContent = name;
        child.onclick = () => onNavigate(path);
        group.appendChild(child);
      }
      container.appendChild(group);
      continue;
    }

    const link = document.createElement('div');
    link.className = 'menu-item';
    link.dataset.path = item.path;
    link.textContent = item.name;
    link.onclick = () => onNavigate(item.path);
    container.appendChild(link);
  }
}

export function updateActiveMenu(path) {
  document.querySelectorAll('#menu [data-path]').forEach((item) => {
    item.classList.toggle('active', item.dataset.path === path);
  });
}
