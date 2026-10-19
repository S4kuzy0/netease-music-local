"""Local stdio adapter using the official MCP SDK and Rain's NetEase backend."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import secrets
import threading
from http.server import ThreadingHTTPServer
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("NETEASE_MCP_DATA_DIR", str(ROOT / ".local"))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
os.environ.update({
    "MCP_READ_ONLY": "true",
    "MCP_STORAGE_PATH": str(DATA / "session.sqlite3"),
    "MCP_HOST": "127.0.0.1",
    "MCP_ACCESS_TOKEN": secrets.token_urlsafe(32),
    "MCP_PUBLIC_URL": "",
    "MCP_OAUTH_PASSWORD": "",
    "MCP_ALLOWED_ORIGIN": "",
    "MCP_DEFAULT_TIMEZONE": "Asia/Shanghai",
})

import server as upstream
import library_tools
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

LOGIN_SERVER: ThreadingHTTPServer | None = None
LOGIN_LOCK = threading.Lock()


class LocalLoginHandler(upstream.MCPHandler):
    """Expose only the upstream temporary login routes on the loopback socket."""

    def _allowed(self) -> bool:
        port = self.server.server_address[1]
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origin = self.headers.get("Origin")
        if self.headers.get("Host") not in hosts or (origin and origin not in {f"http://{host}" for host in hosts}):
            self.send_error(403)
            return False
        if not self.path.startswith("/netease/login/"):
            self.send_error(404)
            return False
        return True

    def do_GET(self) -> None:
        if self._allowed():
            super().do_GET()

    def do_POST(self) -> None:
        if self._allowed():
            super().do_POST()

    def log_message(self, format: str, *args: Any) -> None:
        # Login URLs carry short-lived capability tokens; never log the request path.
        return


def start_local_login() -> dict[str, Any]:
    global LOGIN_SERVER
    result = json.loads(upstream.start_netease_qr_login())
    with LOGIN_LOCK:
        if LOGIN_SERVER is None:
            LOGIN_SERVER = ThreadingHTTPServer(("127.0.0.1", 0), LocalLoginHandler)
            LOGIN_SERVER.daemon_threads = True
            threading.Thread(target=LOGIN_SERVER.serve_forever, daemon=True).start()
        port = LOGIN_SERVER.server_address[1]
    result["login_url"] = f"http://127.0.0.1:{port}/netease/login/{result['login_id']}"
    result["instructions"] = "Open login_url on this computer, then scan and confirm using your NetEase Music app."
    return result


def tool_schema(name: str, description: str, properties: dict, required: list | None = None) -> dict:
    return {
        "name": name, "description": description,
        "inputSchema": {"type": "object", "properties": properties, "required": required or [], "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True},
    }


PAGE = {
    "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100},
    "offset": {"type": "integer", "minimum": 0, "default": 0},
}
TOOLS = [dict(tool) for tool in upstream.READ_TOOLS if tool["name"] not in {"logout_netease", "list_my_playlists", "get_playlist_songs"}]
TOOLS.extend([
    tool_schema("list_my_playlists", "List one page of the user's playlists, including ownership and specialType.", {
        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 100},
        "offset": PAGE["offset"],
    }),
    tool_schema("get_playlist_songs", "Read up to 500 ordered playlist entries; retain missing entries in their original positions.", {
        "playlist_id": {"type": "integer", "minimum": 1}, **PAGE,
    }, ["playlist_id"]),
    tool_schema("get_liked_songs", "Read the owned liked playlist in upstream order, up to 500 entries. Exact liked-at chronology is unverified; preserve order and missing entries.", PAGE),
    tool_schema("check_liked_song_ids", "Check candidates against the complete liked library, so recommendations exclude all already-liked tracks.", {
        "song_ids": {"type": "array", "minItems": 1, "maxItems": 500, "items": {"type": "integer", "minimum": 1}},
    }, ["song_ids"]),
])
SCHEMAS = {tool["name"]: tool for tool in TOOLS}


def invoke(name: str, arguments: dict[str, Any]) -> Any:
    upstream._session_manager().refresh_from_storage()
    if name == "start_netease_qr_login":
        return start_local_login()
    custom = {
        "list_my_playlists": library_tools.list_playlists,
        "get_playlist_songs": library_tools.read_playlist,
        "get_liked_songs": library_tools.get_liked_songs,
        "check_liked_song_ids": library_tools.check_liked_song_ids,
    }
    if name in custom:
        return custom[name](**arguments)
    value = upstream.call_tool(name, arguments)
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return {"text": value}


app = Server("netease-music-local", version="1.0.0", instructions=(
    "Use get_netease_login_status first; if unauthenticated start_netease_qr_login and let the human scan. "
    "Never request or print cookies. Read get_liked_songs in bounded pages or a 500-entry snapshot; preserve "
    "upstream order, missing entries, and snapshot_id. Exact like timestamps are unverified. "
    "Use check_liked_song_ids to exclude already-liked recommendations. No account write tools are exposed."
))


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [types.Tool(**tool) for tool in TOOLS]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
    if name not in SCHEMAS:
        raise ValueError("Unknown or unavailable tool.")
    try:
        value = await asyncio.to_thread(invoke, name, arguments)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(value, ensure_ascii=False))],
            structuredContent=value if isinstance(value, dict) else {"result": value},
        )
    except (upstream.NetEaseError, ValueError, PermissionError) as exc:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=upstream._redact_secrets(str(exc)))], isError=True,
        )


async def main() -> None:
    upstream.validate_startup()
    try:
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())
    finally:
        if LOGIN_SERVER:
            LOGIN_SERVER.shutdown()
            LOGIN_SERVER.server_close()


if __name__ == "__main__":
    asyncio.run(main())
