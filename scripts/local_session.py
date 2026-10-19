"""Keep an actual MCP stdio session alive for terminal-driven local setup and reads."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parameters = StdioServerParameters(command=sys.executable, args=[str(root / "local_mcp.py")], cwd=str(root))
    async with stdio_client(parameters) as streams:
        async with ClientSession(*streams) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            print(json.dumps({"ready": True, "server": initialized.serverInfo.model_dump(), "tools": [tool.name for tool in tools.tools]}), flush=True)
            while line := await asyncio.to_thread(sys.stdin.readline):
                try:
                    request = json.loads(line)
                    if request.get("exit"):
                        break
                    result = await session.call_tool(request["tool"], request.get("arguments", {}))
                    payload = result.structuredContent
                    if payload is None:
                        payload = {"content": [item.model_dump() for item in result.content]}
                    if path := request.get("save_path"):
                        destination = Path(path).resolve()
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                    if request.get("summary") and isinstance(payload, dict) and "songs" in payload:
                        payload = {**{key: value for key, value in payload.items() if key not in {"songs", "selected_song_ids"}}, "sample_songs": payload["songs"][:5], "saved_path": path}
                    print(json.dumps({"tool": request["tool"], "is_error": bool(result.isError), "result": payload}, ensure_ascii=False), flush=True)
                except Exception as exc:
                    print(json.dumps({"client_error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
