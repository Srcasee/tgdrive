export const menu = [
  {name: '仪表盘', path: '#dashboard'},
  {name: 'Telegram', children: [['账号', '#telegram/accounts'], ['Dialogs', '#telegram/dialogs'], ['凭据', '#telegram/sessions']]},
  {name: '资源', children: [['来源', '#resources/sources'], ['文件', '#resources/files'], ['分类', '#resources/categories']]},
  {name: '扫描器', children: [['任务', '#scanner/tasks'], ['日志', '#scanner/logs'], ['设置', '#scanner/settings']]},
  {name: '下载', children: [['进行中', '#download/active'], ['历史', '#download/history']]},
  {name: '系统', children: [['配置', '#system/config'], ['API', '#system/api']]},
  {name: '回收站', path: '#recycle'},
];

let currentUser = null;

export function setMenuUser(user) {
  currentUser = user;
}

export function renderMenu(container, onNavigate) {
  container.replaceChildren();

  const brand = document.createElement('div');
  brand.className = 'menu-brand';
  brand.textContent = '管理后台';
  container.appendChild(brand);

  for (const item of menu) {
    if (!item.children) {
      const link = document.createElement('button');
      link.type = 'button';
      link.className = 'menu-item';
      link.dataset.path = item.path;
      link.textContent = item.name;
      link.onclick = () => onNavigate(item.path);
      container.appendChild(link);
      continue;
    }

    const group = document.createElement('section');
    group.className = 'menu-group';
    const header = document.createElement('button');
    header.type = 'button';
    header.className = 'menu-group-header';
    header.setAttribute('aria-expanded', 'false');
    const label = document.createElement('span');
    label.textContent = item.name;
    const arrow = document.createElement('span');
    arrow.className = 'menu-arrow';
    arrow.textContent = '▸';
    header.append(label, arrow);

    const children = document.createElement('div');
    children.className = 'menu-children';
    children.hidden = true;
    for (const [name, path] of item.children) {
      const child = document.createElement('button');
      child.type = 'button';
      child.className = 'menu-child';
      child.dataset.path = path;
      child.textContent = name;
      child.onclick = () => onNavigate(path);
      children.appendChild(child);
    }

    header.onclick = () => {
      const expanded = header.getAttribute('aria-expanded') === 'true';
      setGroupExpanded(group, !expanded);
    };

    group.append(header, children);
    container.appendChild(group);
  }

  const collapse = document.createElement('button');
  collapse.type = 'button';
  collapse.className = 'menu-collapse-all';
  collapse.textContent = '全部展开';
  collapse.onclick = () => {
    const groups = container.querySelectorAll('.menu-group');
    const shouldExpand = collapse.textContent === '全部展开';
    groups.forEach((group) => setGroupExpanded(group, shouldExpand));
    collapse.textContent = shouldExpand ? '全部收起' : '全部展开';
  };
  container.appendChild(collapse);
}

function setGroupExpanded(group, expanded) {
  const header = group.querySelector('.menu-group-header');
  const children = group.querySelector('.menu-children');
  const arrow = group.querySelector('.menu-arrow');
  header.setAttribute('aria-expanded', String(expanded));
  children.hidden = !expanded;
  arrow.textContent = expanded ? '▾' : '▸';
}

export function updateActiveMenu(path) {
  document.querySelectorAll('#menu [data-path]').forEach((item) => {
    item.classList.toggle('active', item.dataset.path === path);
  });

  document.querySelectorAll('#menu .menu-group').forEach((group) => {
    const activeChild = group.querySelector(`[data-path="${CSS.escape(path)}"]`);
    if (activeChild) setGroupExpanded(group, true);
  });
}
