"""Server MCP (Model Context Protocol) untuk Dashboard Layout Interior - pustaka standar Python.

Dua transport:
  * stdio  : python mcp_server.py           (Claude Desktop, Claude Code, Cursor, dll.)
  * HTTP   : POST http://localhost:8800/mcp (Streamable HTTP, stateless; disediakan server.py)

Protokol: JSON-RPC 2.0, method initialize / tools/list / tools/call / ping. Tool berasal dari ai_tools.py.
Konfigurasi Claude Desktop (claude_desktop_config.json):
  {"mcpServers": {"layout-interior": {"command": "python", "args": ["<path>/backend/mcp_server.py"]}}}
Claude Code:  claude mcp add layout-interior -- python "<path>/backend/mcp_server.py"
          atau claude mcp add --transport http layout-interior http://localhost:8800/mcp
"""
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import db  # noqa: E402
import ai_tools  # noqa: E402

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED = {"2024-11-05", "2025-03-26", "2025-06-18"}
SERVER_INFO = {"name": "layout-interior-pt-citius", "version": "1.0.0"}
INSTRUCTIONS = (
    "Server ini mengelola proyek Dashboard Layout Interior PT Citius: denah lantai, perangkat (kamera CCTV, stop kontak, "
    "panel MCB, port LAN, switch, modem, wifi router, meja, kursi), dinding, estimasi kabel, dan export PDF plan wiring. "
    "Mulai dengan list_projects, lalu get_project_summary. Posisi perangkat dipakai dalam meter dari sudut kiri-atas gambar denah."
)


def _result(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _error(id_, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": id_, "error": err}


def handle_message(msg):
    """Proses satu pesan JSON-RPC. Mengembalikan dict respons, atau None untuk notifikasi."""
    if not isinstance(msg, dict):
        return _error(None, -32600, "Invalid Request")
    method = msg.get("method")
    id_ = msg.get("id")
    params = msg.get("params") or {}
    is_notification = "id" not in msg
    try:
        if method == "initialize":
            ver = params.get("protocolVersion") or PROTOCOL_VERSION
            return _result(id_, {
                "protocolVersion": ver if ver in SUPPORTED else PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": INSTRUCTIONS,
            })
        if method in ("notifications/initialized", "notifications/cancelled", "notifications/roots/list_changed"):
            return None
        if method == "ping":
            return _result(id_, {})
        if method == "tools/list":
            return _result(id_, {"tools": ai_tools.tool_specs()})
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            try:
                out = ai_tools.call_tool(name, args)
                text = json.dumps(out, ensure_ascii=False, indent=1)
                res = {"content": [{"type": "text", "text": text}], "isError": False}
                if isinstance(out, dict):
                    res["structuredContent"] = out
                return _result(id_, res)
            except ai_tools.ToolError as e:
                return _result(id_, {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True})
        if method in ("resources/list", "resources/templates/list"):
            return _result(id_, {"resources": [], "resourceTemplates": []})
        if method == "prompts/list":
            return _result(id_, {"prompts": []})
        if is_notification:
            return None
        return _error(id_, -32601, f"Method not found: {method}")
    except Exception as e:  # noqa: BLE001
        traceback.print_exc(file=sys.stderr)
        if is_notification:
            return None
        return _error(id_, -32603, "Internal error", str(e))


def handle_payload(payload):
    """Payload JSON (dict atau list/batch) -> respons (dict, list, atau None)."""
    if isinstance(payload, list):
        out = [r for r in (handle_message(m) for m in payload) if r is not None]
        return out or None
    return handle_message(payload)


def serve_stdio():
    """Transport stdio: satu pesan JSON per baris di stdin, respons satu baris di stdout."""
    db.init()
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    for raw in stdin:
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line.decode("utf-8"))
        except ValueError:
            resp = _error(None, -32700, "Parse error")
        else:
            resp = handle_payload(payload)
        if resp is not None:
            stdout.write((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
            stdout.flush()


if __name__ == "__main__":
    serve_stdio()
