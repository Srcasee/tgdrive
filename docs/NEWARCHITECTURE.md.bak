一、当前项目基础架构： Docker + PostgreSQL + MTProto
                      Internet
                          │
                    tgdrive Docker App
                          │
              ┌───────────┼───────────┐
              ↓           ↓           ↓
         PostgreSQL    MTProto      proxy（按需求）
                       Client      
              │           ↓
              │       Telegram
              ↓           ↓
          索引数据      各类功能
二、目标拆成以下目录结构：
app/ 
│
├── core/                    
│   └── app.py               #构建应用
│   └── lifecycle.py         #生命周期管理
├── api/                     #后端api接口集中管理或者分散到各个模块
│   └── 各种api          
├── dialog/                  #负责登录TG、获取dialogs
│   └── login.py
│   └── client.py
│   └── dialog_discovery.py
│   └── list_dialogs.py
│   └── check_sessions.py
├── scanner/                 #原架构职责
│   └── scanner.py 
│   └── scanner_manager.py
│   └── runtime_events.py
├── ingestion/               #原架构职责
│   └── identity.py
│   └── models.py
│   └── recognizer.py
│   └──Else
├── repositories/            #原架构职责
│   └── accounts.py
│   └── categories.py
│   └── Else
├── catalog/                 #原架构职责
│   └──api.py
│   └──repository.py
│   └──service.py
├── web/                     #管理和用户页面
│   └── Admin + 前端API 
│   └── User                 #或者用户也单独分出来，似乎是对应当前的auth模块
├──plugins/                  #插件管理
│   └── downloader/          #下载
│       └── downloader.py
│   └── delivery/            #下载交付用于下载、播放，放在app/plugins/或者放回app/
│      └── 
│   └── video/               #视频功能放在app/plugins/或者放回app/
│      └── 
│   └── proxy/               #网络代理插件
│      └── 
│   └── share/               #分享功能放在app/plugins/或者放回app/
│      └── 
1.“下载服务”独立出来
                 tgdrive
                    │
           ┌────────┴────────┐
           ↓                 ↓
   Main Server/API       Download API
           ↓                 ↓
       Docker App       Download Service
           ↓                 ↓
       Telegram           MTProto
           ↓                 ↓
      PostgreSQL          Telegram
                             
2.从 Docker Compose 开始就把服务逻辑分开：
docker-compose.yml
services:
  main:
    ...
  downloader:              #或者将downloader、video、share创建成一个container
    ...
  postgres:
    ...
  proxy:                   #保持现在的由管理员决定可选配置
    ...
    或者Scanner也创建一个container
3.一开始：全部运行在 Server A
                         Internet
                    ┌────────┴────────┐
                    ↓                 ↓
                 Web/API          Download
                    ↓                 ↓
              Main Server       Download Node 1
                    │            Download Node 2
                    │            Download Node 3
                    └────────┬────────┘
                             ↓
                        PostgreSQL
                             ↓
                         Telegram
                          MTProto
4.以后可以横向扩展：
                     Internet
              ┌─────────┴─────────┐
              ↓                   ↓
           Web/API           Download
              ↓                   ↓
         Main Server           下载节点
              │             ┌─────┼─────┐
              │             ↓     ↓     ↓
              │           D1?   D2?   D3?
              └─────────────┼─────┼─────┘
                            ↓
                       PostgreSQL
                            ↓
                         Telegram
以后可以把downloader这个容器搬到另外几台机器。
也就是说，一个下载节点可能非常简单：
download-node/
├── MTProto Client
├── HTTP Download API
├── Range 支持
├── 下载限速
└── Telegram Session
PostgreSQL 放在主服务就行
                    PostgreSQL
                        │
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
      Main API       Scanner       Download

三、下载速度优化：
1.Telegram 官方 upload.getFile 文档明确说明：普通下载时 offset / limit 有对齐要求；upload.getFile 可以返回整个文件或者文件的一部分；limit 最大不能超过 1 MB；单次请求不能跨越 1 MB chunk；可以并行下载多个文件；官方客户端会根据配置控制同一个 DC 的并发下载数；同时还有FLOOD_PREMIUM_WAIT_X；

2.Telegram 官方文件 API 文档明确给了“并发下载”建议，在同一个 DC 下载多个文件时，客户端应该根据：
small_queue_max_active_operations_count
large_queue_max_active_operations_count
限制并发数，小于/大于 20 MB 的文件使用不同的并发控制，且存在一个最佳并发区间。
                  例如20 GB 文件
          ┌──────────────┼──────────────┐
          ↓              ↓              ↓
       Chunk 0        Chunk 1        Chunk 2
        0-1MB         1-2MB          2-3MB
          └──────────────┼──────────────┘
                         ↓
                    HTTP Stream
                         ↓
                        用户
3.MTProto 本身还有“主连接”和“媒体连接”的区别：
Telegram 官方错误文档明确说：普通主 DC 的 main connection 通常只允许一个 MTProto session；而专门用于文件传输的 media DC sessions 可以并行建立。
官方文档明确说：Media DC 的文件传输 session 可以通过同一个 authorization key 建立多个并行 session。
Telegram 官方明确写：Opening an additional session requires no re-authorization: the client simply generates a new session_id over the existing authorization key.
（这个我没懂，当前代码工作时只会建立一个session可以复用，如何使用一个auth_key生成session-001、002、003有待研究）
Telegram 官方文件下载文档明确建议：
大型 upload.getFile 请求应该通过一个或多个独立 session + 独立 connection 来执行，不要和其他 API 方法混在一起。架构可以是：
              Account A  auth_key
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
       Media          Media         Media
      Session 1      Session 2      Session 3
          ↓             ↓             ↓
       Download       Download      Download

四、如果可以拆成“二”的架构，那么一键部署时对于TG凭证的管理：保存“主授权”
                       TG Auth Mgr  一次性登录
                                ↓
                         Account A Auth
                                │
                    encrypted TG auth加密存储
             ┌──────────────────┼──────────────────┐
             ↓                  ↓                  ↓
      Main Server           Downloader 1       Downloader 2
             │                  │                  │
        Main Session       Media Session 1    Media Session 2
             │                  └────────┬─────────┘
             │                           ↓
             │                     Telegram Media DC
             ↓                           ↓
        PostgreSQL                      文件
启动时：Container——读取 encrypted auth——创建自己的 MTProto media session——连接 Telegram。这样每个 Container 都拥有自己的 session。
一键部署的过程变成：1.第一次Telegram Setup——API ID:() API Hash:() Phone:()——Login
2.系统自动：创建 Account——保存加密授权——启动 container——创建各自Media Sessions——开始工作

五、数据库优化，很久的未来才考虑升级        
进一步优化成“搜索数据库”：
PostgreSQL
    │
    ├── B-tree
    ├── GIN
    ├── pg_trgm
    └── Full Text Search
例如：
CREATE EXTENSION pg_trgm;
CREATE INDEX idx_file_name_trgm
ON files USING gin (file_name gin_trgm_ops);
AI 搜索：PostgreSQL——pgvector
PostgreSQL
      ↓
pgvector
