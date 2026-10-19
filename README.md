# tgdrive

<p align="center">
  <strong>基于Telegram的个人无限存储解决方案！</strong><br>
  将 Telegram 中的文件媒体整理成可搜索的资源目录，并通过 Web 界面和 HTTP API 浏览、分享与下载。
</p>

<p align="center">
  <a href="https://github.com/Srcasee/tgdrive/releases"><img src="https://img.shields.io/github/v/release/Srcasee/tgdrive?display_name=tag" alt="GitHub Release"></a>
  <a href="https://github.com/Srcasee/tgdrive"><img src="https://img.shields.io/github/stars/Srcasee/tgdrive?style=flat" alt="GitHub Stars"></a>
  <a href="https://github.com/Srcasee/tgdrive/issues"><img src="https://img.shields.io/github/issues/Srcasee/tgdrive" alt="Issues"></a>
  <a href="https://github.com/Srcasee/tgdrive/commits/main"><img src="https://img.shields.io/github/last-commit/Srcasee/tgdrive/main" alt="Last Commit"></a>
</p>

---

## 📖 项目简介

**tgdrive 是一个以 Telegram 为唯一文件内容后端的文件目录与交付系统。**

它会发现已授权 Telegram 账号可访问的群组和频道，将管理员明确启用的数据源纳入扫描流程，把 Telegram 消息中的媒体整理为逻辑资源，再提供目录浏览、搜索、分类、分享链接和下载能力。

```text
Telegram 账号 / 群组 / 频道
          │
          ▼
   对话元数据发现
          │
          ▼
   管理员选择数据源
          │
          ▼
   Scanner 扫描媒体元数据
          │
          ▼
   逻辑资源 / 分类 / 搜索
          │
          ▼
      Web UI / HTTP API
          │
          ▼
       下载与分享
```

> **设计边界：** Telegram 是唯一的文件内容后端。多个 Telegram 账号用于访问与冗余，不代表支持多个存储供应商。本项目不是 S3、WebDAV 或 Google Drive 的通用存储适配层。

## ✨ 主要功能

- **Telegram 多账号会话**：可分别登录和管理多个 Telegram 账号。
- **数据源由管理员显式启用**：先发现对话元数据，再由管理员选择要扫描的群组或频道。
- **资源目录与搜索**：将媒体整理为逻辑资源，支持目录浏览、搜索和分类。
- **资源交付**：通过 HTTP 接口下载或流式读取资源，并提供 HEAD 检查接口。
- **分享链接**：为资源创建分享链接；重新生成会使之前的有效链接失效，管理员可撤销链接，也可设置 UTC 过期时间。
- **Web 管理界面**：提供用户 Web UI 与管理员控制台。
- **PostgreSQL 元数据存储**：保存资源目录、分类和数据源状态；Telegram 仍负责保存文件内容。
- **可选代理**：可按需启用独立的 sing-box 代理服务；默认不启用。

## 🚀 快速部署

### 环境要求

- Linux 服务器或其他可运行 Docker 的主机
- 生产配置1H2G即可，若选自行编译镜像内存需4G及以上
- Docker Engine 与 Docker Compose 插件
- Telegram账号及 API 凭据：TG_API_ID、TG_API_HASH（可从 [my.telegram.org](https://my.telegram.org) 获取）
- 能够持久化保存应用数据的磁盘空间
  
此项目流量吞吐瓶颈依赖网络环境及带宽，已提供可选的代理配置，推荐无网络限制的高带宽服务器

### 1. 获取项目并启动

当前部署脚本会从本地源码构建 Core 镜像，并启动 PostgreSQL 与 Core 服务：

```bash
git clone https://github.com/Srcasee/tgdrive.git
cd tgdrive
chmod +x deploy.sh
./deploy.sh
```

首次运行时，脚本会检查 Docker 环境、构建 Core 镜像、创建持久化目录，并在缺少 .env 时交互式收集必要配置、生成部署密钥。请妥善保存生成的管理员凭据。

检查服务状态：

```bash
docker compose ps
docker compose logs --tail=100 tgdrive
```

默认 Web 服务端口为 **8080**。部署完成后访问：

- 用户界面：`http://服务器IP:8080/`
- 管理员控制台：`http://服务器IP:8080/admin`

> 当前仓库的 Compose 配置使用本机的 tgdrive:latest 镜像，deploy.sh 负责构建该镜像。不要假定 GHCR 上已经存在可直接拉取的 tgdrive Core 镜像；请以仓库发布页和后续发布配置为准。

### 2. 登录 Telegram 账号

在 Core 服务健康后，使用脚本登录账号：

```bash
./login-account.sh default +1234567890
# 其他账号可使用不同名称
./login-account.sh account2 +861234567890
```

将示例手机号替换为你自己的号码。按照 Telegram 的交互提示完成授权；不要把验证码、会话文件或账号凭据提交到 Git 仓库。

登录脚本会在交互登录期间暂停正在运行的 Core，以避免 Telegram SQLite session 文件锁冲突；结束后会按原状态恢复 Core 服务。

### 3. 启用 Telegram 数据源

1. 打开 `http://服务器IP:8080/admin` 并使用管理员账号登录。
2. 进入 **Telegram → Dialogs**，等待已授权账号的对话元数据同步。
3. 找到需要纳入目录的群组或频道，明确执行 **Enable**。
4. 启用后会创建或重新启用对应的 Source，Scanner 才会开始处理该数据源。
5. 在目录/资源管理页面确认资源已出现，并按需分类、搜索、分享或下载。

**对话发现本身只读取元数据，不会自动扫描所有消息文件。** 打开对话列表也不会启动扫描；只有管理员启用相应 Source 后，该数据源才会进入扫描流程。

## 🌐 可选代理

默认直接连接 Telegram。只有网络环境确有需要时才配置代理，并建议在 Telegram 登录之前完成设置。

1. 根据 .env.example 编辑 .env，设置 TG_PROXY_ENABLED=true 并填写所需的 TG_PROXY_* 参数。
2. 按项目提供的示例配置准备本地 config.json。
3. 启动可选代理服务：

```bash
docker compose --profile proxy up -d
docker compose --profile proxy ps
docker compose --profile proxy logs --tail=100 proxy
```

代理使用单独的 sing-box 镜像，不是 tgdrive Core 镜像。请确认主机可以访问所配置的镜像仓库；如果修改了代理配置，可按需重启 Core 或通过管理员操作重新连接 Telegram。

## 🧭 使用说明与文档

| 文档 | 内容 |
| --- | --- |
| [架构说明](docs/ARCHITECTURE.md) | 项目边界、资源模型与架构约束 |
| [项目状态](docs/PROJECT-STATUS.md) | 已实现能力、验证记录、已知问题与开发优先级 |
| [部署脚本](deploy.sh) | 新服务器初始化流程 |
| [Compose 配置](docker-compose.yml) | Core、PostgreSQL、登录与可选代理服务 |
| [环境变量模板](.env.example) | Telegram、数据库、认证及代理配置项 |
| [原始 README 归档](docs/README.md) | 本次重写前的 README 完整副本 |

## 🔌 Core API

常用资源接口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /catalog | 获取资源目录 |
| GET | /catalog/search?q=... | 搜索资源 |
| GET | /catalog/{resource_id} | 获取资源详情 |
| GET | /resources/{resource_id}/download | 下载资源 |
| HEAD | /resources/{resource_id}/download | 检查下载响应 |
| GET | /resources/{resource_id}/stream | 流式读取资源 |
| HEAD | /resources/{resource_id}/stream | 检查流式响应 |
| POST | /resources/{resource_id}/share | 创建或轮换分享链接 |

创建分享链接时，可以传入可选的 UTC 过期时间：

```http
POST /resources/{resource_id}/share
Content-Type: application/json

{
  "expires_at": "2027-01-01T00:00:00Z"
}
```

不传过期时间则创建默认永久有效的链接。分享链接是每个资源的全局单一有效链接：重新创建或轮换会使旧 token 失效。匿名访问使用 GET /share/{token}；管理员可通过 DELETE /api/admin/shares/{share_id} 撤销链接。

更多 Telegram 账号、对话、Source 与分类管理接口，请参考代码和 [项目状态文档](docs/PROJECT-STATUS.md)。

## 🏗️ 技术栈

- **后端**：Python 3.12、FastAPI、Uvicorn、Telethon
- **前端**：Vue 3、Vite、TypeScript 生态与 pnpm
- **数据库**：PostgreSQL
- **部署**：Docker、Docker Compose
- **可选网络代理**：sing-box

## 🧑‍💻 本地开发与测试

安装后端开发依赖并运行测试：

```bash
pip install -r requirements-dev.txt
pytest -q
```

前端开发：

```bash
pnpm --dir frontend install
pnpm --dir frontend dev
```

构建生产前端：

```bash
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build:prod
```

生产 Docker 镜像通过根目录的 Dockerfile 构建前端资源，并将其与 Python Core 一起打包。

## 🔐 安全与数据备份

- **不要提交敏感信息**：.env、Telegram session 文件、验证码、API Hash、管理员密码和代理凭据都应保密。
- **保管好部署配置**：.env 包含认证和数据库连接所需的关键配置，请限制文件权限。
- **定期备份**：至少备份 data/ 与 .env，并确保备份可恢复。
- **谨慎开放端口**：默认 Web 服务端口为 8080；部署到公网时请结合防火墙、HTTPS 反向代理和强密码策略。
- **先验证再升级**：升级前备份数据库与配置，并确认新版本的迁移和兼容要求。

## 📌 项目状态

tgdrive 正在持续开发。当前实现包括 Telegram 账号会话、对话元数据发现、Source 管理、资源目录/搜索/分类、分享链接以及基础下载交付。吞吐量基准测试、多账号下载性能与故障切换验证、Topic 到分类映射等仍有待完善。

功能实现状态和验证范围会变化，请查看 [PROJECT-STATUS.md](docs/PROJECT-STATUS.md)，不要仅依据 README 中的概述判断某项能力已在所有环境下验证。

## 🤝 参与贡献

欢迎通过 [Issues](https://github.com/Srcasee/tgdrive/issues) 报告问题、提交功能建议，或通过 Pull Request 参与开发。提交前请尽量说明复现步骤、运行环境和相关日志，并移除所有密钥、账号信息及个人数据。

## 📄 许可证

请以仓库中实际提供的许可证文件为准；如仓库尚未包含明确的根目录许可证，请在使用、分发或修改前先向项目维护者确认。
