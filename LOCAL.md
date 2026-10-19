# Local NetEase Music MCP

This local edition extends Rain's MIT-licensed server with the official MCP Python SDK's stdio transport. The MCP host starts and stops the process. Login state is stored locally; no cloud deployment or scheduled background service is required.

## Install and connect

Use Python 3.13. Create a virtual environment in the project and install `requirements-local.lock.txt`. The lock records the exact dependency versions used for this installation. `requirements-local.txt` expresses the supported direct dependency ranges.

```powershell
py -V:3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-local.lock.txt
codex mcp add netease-music-local -- <absolute-python-path> -u <absolute-local_mcp.py-path>
```

Set the entry's startup timeout to 30 seconds and tool timeout to 180 seconds when requesting large snapshots. `NETEASE_MCP_DATA_DIR` can select a different local data directory; the default is `.local` beside `local_mcp.py`.

Call `get_netease_login_status`, then `start_netease_qr_login` when needed. Open its loopback `login_url` on the same computer, scan with the NetEase Music app, and confirm. If required, complete the official interactive security challenge on that page. The challenge explicitly uses HTTPS even though the loopback page uses HTTP. Cookie values are never returned by these tools. Login attempts expire after ten minutes; an unfinished attempt cannot survive a process restart.

## Library tools

- `list_my_playlists(limit, offset)` returns structured pages, ownership, and special playlist types.
- `get_liked_songs(limit, offset)` identifies the owned `specialType=5` playlist and reads up to 500 entries from a complete ID snapshot. Song details are requested in batches of 50.
- `get_playlist_songs(playlist_id, limit, offset)` provides the same order and completeness guarantees for another playlist.
- `check_liked_song_ids(song_ids)` checks up to 500 recommendation candidates against the entire liked library, including likes older than the recent 500.
- The existing metadata search, song details, personalized daily recommendations, play rankings, recent plays and podcast reads remain available.

Missing songs retain their original positions with `found=false`; they are also listed in `missing_song_ids`. A `snapshot_id` hashes the complete ordered IDs so callers can detect changes across pages. Incomplete upstream ID lists are rejected. The adapter preserves server playlist order; exact like timestamps and manual reorder history remain unverified. Do not sort by numeric song ID or release date to infer recency.

Callers should save one snapshot, report selected/found/missing counts, and avoid combining pages with different snapshot IDs. Recommendation interpretation belongs to the calling assistant; the MCP does not claim to have listened to audio or independently classified every track.

Playlist lookup requests only one embedded track while retaining the full `trackIds` list. Song metadata is then fetched for the requested page. This keeps large liked libraries below the bounded response reader's limit. Incomplete ID lists still fail explicitly.

## Local access and data

The stdio tool catalog exposes music reads and login tools. Account mutation and logout tools are not exposed. The transient web listener binds only to loopback, accepts matching Host/Origin values, and serves only the original temporary login routes. Login URLs have high-entropy short-lived identifiers, and request paths are not logged.

`.local/session.sqlite3` contains sensitive login state. Keep the database and its backups local. Raw library exports, real environment configuration, logs and dependency directories are ignored by Git. The SQLite facade uses short independent transactions; the adapter refreshes its session cache before each tool invocation so another local MCP process's persisted login is observed. Do not run concurrent account-writing deployments against this database.

If uninstalling, remove the `netease-music-local` MCP configuration first. Preserve a backup of `.local` if the login is still needed. No Windows startup task, global player setting or external hosted service is installed.

An existing locally saved NetEase session can also be migrated with the user's authorization. Verify it against the fixed `https://music.163.com/api/nuser/account/get` endpoint and check the expected account before storing the normalized session through `SessionManager.save`. Back up an existing SQLite database with SQLite's backup API first. Never pass cookie contents as MCP arguments, command-line text, or log output. No cookie import tool is exposed to the model; login status and library reads work normally after the local migration. Reuse does not extend the upstream session's lifetime.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -u scripts/local_session.py
```

The interactive verification client performs a real MCP initialize/tools-list handshake and accepts newline-delimited tool requests. Example:

```json
{"tool":"get_netease_login_status"}
{"tool":"get_liked_songs","arguments":{"limit":500},"save_path":"<local-export-path>","summary":true}
{"exit":true}
```

`save_path` belongs to this local terminal client and is not an MCP server tool parameter. Automated tests use synthetic data; real account login and library access must be verified separately. NetEase Web interfaces are unofficial and may change or trigger official security checks.
