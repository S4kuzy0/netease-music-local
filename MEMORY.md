# Local NetEase MCP project memory

## Confirmed scope — 2026-10-19, Asia/Shanghai

- User selected Rainlxyl/netease-music-mcp-safe as the implementation base and authorized local installation, Codex integration, account login, reading the most recent 500 liked tracks, and personalized new-song recommendations.
- Upstream baseline: `39c995e89498f3044fb964f89f275ecf6b46b0b7` (MIT).
- Preserve all existing unrelated MCP configurations. No account playlist or like mutations are required.
- Local adapter uses the official MCP Python SDK over stdio. Account state persists in ignored `.local/session.sqlite3`; a transient loopback-only login page exists only while its MCP process is alive.
- `library_tools.py` identifies the owned `specialType=5` playlist, retains complete upstream ID order and missing positions, batches details in groups of 50, and checks recommendation candidates against the entire liked library.
- Upstream playlist order is preserved. Exact like timestamps and manual reorder history are not currently verified; never fabricate them.
- Original hosted HTTP implementation remains available as upstream reference. Local entry point is `local_mcp.py`.

## Verification and remaining work

- Completed: dependencies installed and pinned, 132 upstream/local tests passed, pip check and compile passed, actual MCP handshake passed, Codex registered as `netease-music-local`, and unrelated MCP entries preserved exactly.
- Fixed two local integration issues: refresh persisted sessions before each call, and force the official challenge SDK to HTTPS on the HTTP loopback page. The latter was diagnosed from the official SDK's page-protocol default and the page's HTTPS-only CSP; a regression test failed before the fix and passed afterwards. Current served login HTML was checked for the explicit HTTPS option.
- Private source repository created and pushed; remote visibility and branch contents verified. The GitHub connector cannot access this new private repository, so repository operations use the user's existing Git credential helper without printing credentials.
- The user subsequently authorized reusing the other assistant's existing locally saved NetEase session. Verified it live against the account endpoint, matched the expected account, backed up the local SQLite database, and saved only the normalized session. Native Codex MCP login status now confirms authentication; native get_liked_songs successfully returned 500 records with no missing positions. No new QR scan was needed.
- Real library access exposed a truncated JSON bug: requesting excessive embedded tracks returned a response larger than the bounded reader. Playlist lookup now requests one embedded track, retains every trackId, and fetches selected metadata separately. The new regression failed before the fix and passed afterwards. Both the SDK client and the native Codex tool completed live reads and full-library candidate exclusion.
- The existing MCP connection initially retained old Python code. Adding Python's -B flag to the saved local launcher caused this host to refresh the connection; the native tool was then verified against the updated implementation. No Codex app restart or unrelated configuration change was performed. This observed refresh is not a general hot-reload guarantee for other hosts.
- The user's other assistant had produced an existing library export. Its recent 500 IDs were checked against the exact first 500 of the full 4,268-ID playlist, and all 4,268 metadata IDs were checked against the full ordered ID list. Personal exports remain outside this source repository.
- Earlier snapshot-only phase: 20 candidates were checked against all liked IDs and exact title/artist matches, with all 20 separately reverified against public song metadata. That phase had no audio review or new live account refresh.
- Current recommendation phase: the native MCP completed fresh full-library exclusion for ten new selections. Five were originally released within the last year and five use pre-2006 recordings. All candidate artist IDs were absent from the full metadata export, whose complete ordered IDs still matched the fresh live playlist. Dates and versions were checked against external release sources; this is not an audio-review claim.
- A direct DSH headless consultation was attempted but did not obtain a model answer because its official API route lacked credentials. The other assistant's actual project scripts and non-secret exports supplied the verified reading-route evidence instead. A follow-up question is being left in the shared handoff.
- Session DB, raw user library exports, logs, credentials, local configuration and backups must remain outside version control.
