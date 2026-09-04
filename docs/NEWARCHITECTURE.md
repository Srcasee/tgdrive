app/ 
│
├── core/                    
│   └── app.py               #构建应用
│   └── lifecycle.py         #生命周期管理
├── api/                     #api接口管理
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
│   └── Admin + API 
│   └── User
├──plugins/                  #插件管理
│   └── downloader/          #下载
│       └── downloader.py
│   └── delivery/            #下载交付
│      └── 
│   └── video/               #视频功能
│      └── 
│   └── proxy/               #网络代理插件
│      └── 
│   └── share/               #分享功能
│      └── 
