import { renderMenu, setMenuUser } from './layout.js';
import { initRouter, navigate } from './router.js';

async function getIdentity() {
  const response = await fetch('/auth/me', {cache: 'no-store'});
  if (!response.ok) return null;
  return response.json();
}

function renderLogin(root) {
  root.replaceChildren();
  document.getElementById('menu')?.replaceChildren();
  const header = document.getElementById('admin-header');
  if (header) header.hidden = true;

  const page = document.createElement('div');
  page.className = 'admin-login-page';
  page.innerHTML = `
    <section class="admin-login-card">
      <div class="admin-login-brand">管理后台</div>
      <h1>管理员登录</h1>
      <p class="admin-muted">登录后进入 TGDrive 管理后台。</p>
      <form class="admin-login-form">
        <label>用户名<input name="username" autocomplete="username" required></label>
        <label>密码<input name="password" type="password" autocomplete="current-password" required></label>
        <button type="submit">登录</button>
        <div class="admin-login-error" role="alert"></div>
      </form>
    </section>
  `;
  const form = page.querySelector('form');
  const button = form.querySelector('button');
  const error = form.querySelector('.admin-login-error');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    button.disabled = true;
    error.textContent = '';
    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          username: form.elements.username.value.trim(),
          password: form.elements.password.value,
        }),
      });
      if (!response.ok) {
        error.textContent = '登录失败，请检查用户名和密码。';
        return;
      }
      await init();
    } catch (err) {
      error.textContent = `登录失败：${err.message}`;
    } finally {
      button.disabled = false;
    }
  });
  root.appendChild(page);
  form.elements.username.focus();
}

function renderUserMenu(user) {
  const header = document.getElementById('admin-header');
  if (!header) return;
  header.hidden = false;
  header.replaceChildren();

  const wrapper = document.createElement('details');
  wrapper.className = 'admin-user-menu';

  const summary = document.createElement('summary');
  summary.textContent = user.username;

  const panel = document.createElement('div');
  panel.className = 'admin-user-dropdown';
  const name = document.createElement('div');
  name.className = 'admin-user-name';
  name.textContent = user.username;
  panel.appendChild(name);

  const logout = document.createElement('button');
  logout.type = 'button';
  logout.className = 'admin-logout-button';
  logout.textContent = '退出';
  logout.onclick = async () => {
    logout.disabled = true;
    try {
      const response = await fetch('/auth/logout', {method: 'POST'});
      if (!response.ok) throw new Error('退出失败');
      wrapper.open = false;
      await init();
    } catch (error) {
      logout.disabled = false;
      name.textContent = error.message;
    }
  };

  panel.appendChild(logout);
  wrapper.append(summary, panel);
  header.appendChild(wrapper);
}

async function init() {
  const root = document.getElementById('content');
  if (!root) return;

  try {
    const user = await getIdentity();
    if (!user) {
      document.body.classList.remove('admin-authenticated');
      renderLogin(root);
      return;
    }
    if (user.role !== 'admin') {
      document.body.classList.remove('admin-authenticated');
      document.getElementById('menu')?.replaceChildren();
      const header = document.getElementById('admin-header');
      if (header) header.hidden = true;
      root.innerHTML = '<div class="admin-page"><section class="panel"><h1>无管理员权限</h1><p class="admin-muted">当前账号不能访问管理后台。</p></section></div>';
      return;
    }
    renderLayout(user);
  } catch (error) {
    root.innerHTML = `<div class="admin-page"><div class="admin-error">管理后台加载失败：${error.message}</div></div>`;
    console.error('Admin initialization failed', error);
  }
}

function renderLayout(user) {
  const menu = document.getElementById('menu');
  const content = document.getElementById('content');
  if (!menu || !content) return;
  document.body.classList.add('admin-authenticated');
  setMenuUser(user);
  renderMenu(menu, navigate);
  renderUserMenu(user);
  initRouter(content);
}

autoInit();

function autoInit() {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, {once: true});
  } else {
    init();
  }
}
