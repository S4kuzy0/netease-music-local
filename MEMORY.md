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

- Completed: dependencies installed and pinned, 131 upstream/local tests passed, pip check and compile passed, actual MCP handshake passed, Codex registered as `netease-music-local`, and unrelated MCP entries preserved exactly.
- Fixed two local integration issues: refresh persisted sessions before each call, and force the official challenge SDK to HTTPS on the HTTP loopback page. The latter was diagnosed from the official SDK's page-protocol default and the page's HTTPS-only CSP; a regression test failed before the fix and passed afterwards. Current served login HTML was checked for the explicit HTTPS option.
- Private source repository created and pushed; remote visibility and branch contents verified. The GitHub connector cannot access this new private repository, so repository operations use the user's existing Git credential helper without printing credentials.
- User skipped the renewed interactive login. Live account authentication remains incomplete.
- The user's other assistant had produced an existing library export. Its recent 500 IDs were checked against the exact first 500 of the full 4,268-ID playlist, and all 4,268 metadata IDs were checked against the full ordered ID list. Personal exports remain outside this source repository.
- Recommendation selection completed from that timestamped snapshot: 20 candidates checked against all liked IDs and exact title/artist matches, with all 20 separately reverified against public song metadata. No claim of audio review or new live account refresh.
- A direct DSH headless consultation was attempted but did not obtain a model answer because its official API route lacked credentials. The other assistant's actual project scripts and non-secret exports supplied the verified reading-route evidence instead. A follow-up question is being left in the shared handoff.
- Session DB, raw user library exports, logs, credentials, local configuration and backups must remain outside version control.
