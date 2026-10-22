"""Send a command to the MCP for Blender add-on socket (same protocol the MCP server uses).

usage: python3 mcp_send.py code step.py | shot out.png | get_scene_info
"""
import json, socket, sys

def send(cmd_type, params=None, port=9876, timeout=600):
    s = socket.create_connection(("localhost", port), timeout=timeout)
    s.sendall(json.dumps({"type": cmd_type, "params": params or {}}).encode())
    buf = b""
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
        try:
            return json.loads(buf.decode())
        except ValueError:
            continue
    return json.loads(buf.decode())

if __name__ == "__main__":
    if sys.argv[1] == "code":
        print(json.dumps(send("execute_code", {"code": open(sys.argv[2]).read()}), ensure_ascii=False)[:4000])
    elif sys.argv[1] == "shot":
        print(send("get_viewport_screenshot", {"max_size": 1200, "filepath": sys.argv[2], "format": "png"}))
    else:
        print(json.dumps(send(sys.argv[1]), ensure_ascii=False)[:4000])
