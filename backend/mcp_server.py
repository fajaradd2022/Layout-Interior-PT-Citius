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
import uuid

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


# ------------------------------------------------------------------ kontrol akses (pengaturan MCP + scope API key)
def allowed_tools(settings, key=None):
    names = [t["name"] for t in ai_tools.TOOLS]
    exp = settings.get("exposed_tools", "all")
    if exp != "all":
        names = [n for n in names if n in exp]
    if key and key.get("scopes"):
        names = [n for n in names if n in key["scopes"]]
    return names


def project_allowed(settings, pid):
    exp = settings.get("exposed_projects", "all")
    return exp == "all" or pid in exp


def call_tool_checked(name, args, settings, key=None):
    """Panggil tool dengan pengecekan tool yang diekspos, scope API key, dan proyek yang diekspos."""
    if name not in allowed_tools(settings, key):
        raise ai_tools.ToolError(f"tool '{name}' tidak diizinkan untuk klien ini")
    pid = (args or {}).get("project_id")
    if pid and not project_allowed(settings, pid):
        raise ai_tools.ToolError(f"proyek '{pid}' tidak diekspos ke klien MCP/AI")
    out = ai_tools.call_tool(name, args)
    exp = settings.get("exposed_projects", "all")
    if exp != "all":
        if name == "list_projects":
            out = [p for p in out if p["id"] in exp]
        elif name == "create_project" and isinstance(out, dict) and out.get("id"):
            db.set_settings({"exposed_projects": list(exp) + [out["id"]]})
    return out


def _result(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _error(id_, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": id_, "error": err}


def handle_message(msg, ctx=None):
    """Proses satu pesan JSON-RPC. Mengembalikan dict respons, atau None untuk notifikasi.

    ctx: {"transport": "stdio"|"http", "key": record API key|None, "session_id": str|None, "settings": dict}
    """
    ctx = ctx if ctx is not None else {"transport": "stdio", "key": None, "session_id": None}
    settings = ctx.get("settings") or db.get_settings()
    key = ctx.get("key")
    if not isinstance(msg, dict):
        return _error(None, -32600, "Invalid Request")
    method = msg.get("method")
    id_ = msg.get("id")
    params = msg.get("params") or {}
    is_notification = "id" not in msg
    try:
        if method == "initialize":
            ver = params.get("protocolVersion") or PROTOCOL_VERSION
            info = params.get("clientInfo") or {}
            sid = ctx.get("session_id") or uuid.uuid4().hex[:16]
            ctx["session_id"] = sid
            ctx["new_session"] = sid
            db.upsert_client(sid, info.get("name") or "unknown", str(info.get("version") or ""), ctx.get("transport", "http"),
                             (key or {}).get("id"))
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
        if ctx.get("session_id"):
            db.touch_client(ctx["session_id"], (key or {}).get("id"))
        if method == "tools/list":
            allowed = set(allowed_tools(settings, key))
            return _result(id_, {"tools": [t for t in ai_tools.tool_specs() if t["name"] in allowed]})
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments") or {}
            try:
                out = call_tool_checked(name, args, settings, key)
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


def handle_payload(payload, ctx=None):
    """Payload JSON (dict atau list/batch) -> respons (dict, list, atau None)."""
    if isinstance(payload, list):
        out = [r for r in (handle_message(m, ctx) for m in payload) if r is not None]
        return out or None
    return handle_message(payload, ctx)


def serve_stdio():
    """Transport stdio: satu pesan JSON per baris di stdin, respons satu baris di stdout."""
    db.init()
    settings = db.get_settings()
    if not settings.get("enabled", True):
        sys.stderr.write("MCP dinonaktifkan di pengaturan aplikasi (Settings > Instance-level MCP).\n")
    ctx = {"transport": "stdio", "key": None, "session_id": None, "settings": settings}
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
            ctx["settings"] = db.get_settings()   # pengaturan bisa berubah dari aplikasi saat server berjalan
            if not ctx["settings"].get("enabled", True) and isinstance(payload, dict) and "id" in payload and payload.get("method") != "initialize":
                resp = _error(payload.get("id"), -32000, "MCP dinonaktifkan di pengaturan aplikasi")
            else:
                resp = handle_payload(payload, ctx)
        if resp is not None:
            stdout.write((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
            stdout.flush()


if __name__ == "__main__":
    serve_stdio()
