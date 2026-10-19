# NetEase Music Local MCP

本地运行的网易云音乐 MCP：**扫码登录、完整喜欢列表分页、歌曲元数据与推荐排重**。由 MCP 客户端通过 stdio 启停，无需部署云服务。

本项目基于 [Rainlxyl/netease-music-mcp-safe](https://github.com/Rainlxyl/netease-music-mcp-safe) 继续改造，后者派生自 [Vael-KY/netease-music-mcp](https://github.com/Vael-KY/netease-music-mcp)。上游 MIT 版权声明完整保留；原上游介绍见 [README.upstream.md](README.upstream.md)。本项目与网易公司无隶属或背书关系。

## 这个版本增加了什么

| 本地适配 | 行为 |
| --- | --- |
| 官方 Python MCP SDK / stdio | MCP 客户端在本机启动进程，无需公开 HTTP 服务 |
| 本地扫码页面 | 临时页面仅监听 loopback，登录状态存本地 SQLite，工具不返回 Cookie |
| 完整喜欢列表 | 识别本人 `specialType=5` 歌单，读取完整 ID 快照后分页取详情 |
| 顺序与缺失保留 | 按上游 ID 顺序返回，缺失歌曲保留位置和 `found=false` |
| 全库推荐排重 | `check_liked_song_ids` 检查整个喜欢库，不只最近一页 |
| 大歌单读取 | 请求一个内嵌条目保留全量 ID，详情分批读取，避免大响应截断 |

这里保留的是上游歌单顺序，不能据此推断精确收藏时间或手动重排历史。`snapshot_id` 可帮助发现两次分页间的歌单变化。

## 安装

需要 Python 3.13。Windows PowerShell：

```powershell
git clone https://github.com/S4kuzy0/netease-music-local.git
Set-Location netease-music-local
py -V:3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-local.lock.txt
```

锁文件为 Windows 已验证依赖快照。其他平台或需要重新解析依赖时，使用 `python -m pip install -r requirements-local.txt`；不要将 Windows 专属 `pywin32` 锁文件直接用于 Linux。运行依赖 Pillow、PyCryptodome、qrcode 与 MCP SDK，无 GPU 或数据库服务要求。

### 连接 MCP 客户端

将客户端的 stdio 命令设为虚拟环境 Python 的绝对路径，参数设为 `-B -u` 加 `local_mcp.py` 的绝对路径。Codex 示例：

```powershell
codex mcp add netease-music-local -- "<absolute-python-path>" -B -u "<absolute-local_mcp.py-path>"
```

环境变量 `NETEASE_MCP_DATA_DIR` 可指定独立本地状态目录。启动超时可设为 30 秒；大列表读取的工具超时可设为 180 秒。先核验 MCP 握手，再核验账号登录；只完成配置登记不代表工具已加载。

## 第一次使用

1. 调用 `get_netease_login_status`。
2. 如未登录，调用 `start_netease_qr_login`，在同一电脑打开返回的 `login_url`，用自己的网易云 App 扫码确认。遇到官方安全验证时由本人完成。
3. 调用 `get_liked_songs(limit=100, offset=0)`；每页最多 500 个位置。
4. 后续分页核对 `snapshot_id`、`missing_song_ids` 和计数。推荐前用 `check_liked_song_ids` 检查候选。

示例请求数据（由客户端调用相应工具）：

```json
{"name":"get_liked_songs","arguments":{"limit":100,"offset":0}}
```

`list_my_playlists`、`get_playlist_songs`、搜索、歌曲详情、日推和播放记录等读取继续可用。**本地 `local_mcp.py` 不暴露账号写入或退出登录工具，也不控制客户端播放。** 上游 `server.py` 的托管 HTTP/OAuth 与写工具是另外一条运行入口，不属于本地 stdio 工具集；其说明保存在上游文档中。

## 数据与限制

`.local/session.sqlite3` 含登录态，只保留本机；真实 `.env`、日志、库导出和状态备份不应上传。临时登录链接十分钟失效，进程重启后未完成登录需重新开始。每位使用者运行自己的实例并登录自己的账号。

接口使用非官方网易云 Web API，可能变化、触发安全验证或受到账号权限限制。本项目不提供音频下载，不宣称听过歌曲，不自动推断曲风或收藏时间。登录细节、数据边界及终端客户端说明见 [LOCAL.md](LOCAL.md)，上游安全说明见 [SECURITY.md](SECURITY.md)。

## 开发与验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -u scripts/local_session.py
```

自动测试使用合成数据；真实账号验证需另行执行，不属于 CI。交互客户端可用 `save_path` 本地保存结果，该字段不是服务端工具参数。实现决策与历史验证见 [项目记忆](MEMORY.md)。

## 许可

[MIT](LICENSE)。上游版权声明与许可条件继续保留；本地代码的许可不授予音乐、账号或第三方平台内容的额外权利。
