const routes = {
  '#dashboard': (container) => {
    container.textContent = '仪表盘';
  },
  '#telegram/accounts': (container) => loadModule('./telegram.js', container, 'accounts'),
  '#telegram/dialogs': (container) => loadModule('./telegram.js', container, 'dialogs'),
  '#telegram/sessions': (container) => loadModule('./telegram.js', container, 'sessions'),
  '#resources/sources': (container) => loadModule('./resources.js', container, 'sources'),
  '#resources/files': (container) => loadModule('./resources.js', container, 'files'),
  '#resources/categories': (container) => loadModule('./resources.js', container, 'categories'),
  '#scanner/tasks': (container) => loadModule('./scanner.js', container, 'tasks'),
  '#scanner/logs': (container) => loadModule('./scanner.js', container, 'logs'),
  '#scanner/settings': (container) => loadModule('./scanner.js', container, 'settings'),
  '#download/active': (container) => loadModule('./download.js', container, 'active'),
  '#download/history': (container) => loadModule('./download.js', container, 'history'),
  '#system/config': (container) => {
    container.textContent = '系统 / 配置';
  },
  '#system/api': (container) => {
    container.textContent = '系统 / API';
  },
  '#recycle': (container) => {
    container.textContent = '回收站';
  },
};

async function loadModule(path, container, section) {
  try {
    const module = await import(path);
    const renderer = path === './telegram.js'
      ? module.renderTelegram
      : path === './resources.js'
        ? module.renderResources
        : path === './scanner.js'
          ? module.renderScanner
          : module.renderDownload;
    await renderer(container, section);
  } catch (error) {
    container.replaceChildren();
    const box = document.createElement('div');
    box.className = 'admin-error';
    box.textContent = `页面加载失败：${error.message}`;
    container.appendChild(box);
    console.error(`Failed to load admin module ${path}`, error);
  }
}

export function navigate(path) {
  if (location.hash !== path) location.hash = path;
}

export async function renderRoute(container, path = location.hash || '#dashboard') {
  const route = routes[path] || routes['#dashboard'];
  await route(container);
}

export function initRouter(container) {
  const update = () => {
    renderRoute(container).catch((error) => {
      container.textContent = `页面加载失败：${error.message}`;
      console.error('Admin route error', error);
    });
  };
  window.addEventListener('hashchange', update);
  update();
}
