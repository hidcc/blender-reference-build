"""Minimal OBS WebSocket v5 client (stdlib only) to control recording from scripts.

usage: python3 obs_control.py [--host H] [--port P] [--password PW] COMMAND [ARG]
commands: status | start | stop | pause | resume | scene NAME | chapter NAME | version
The password defaults to $OBS_WS_PASSWORD (OBS: Tools > WebSocket Server Settings).
"""
import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import uuid


class OBSError(RuntimeError):
    pass


class OBS:
    def __init__(self, host="localhost", port=4455, password=None, timeout=10):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self._handshake(host, port)
        hello = self._recv_json()
        if hello.get("op") != 0:
            raise OBSError(f"unexpected hello: {hello}")
        ident = {"rpcVersion": hello["d"].get("rpcVersion", 1)}
        auth = hello["d"].get("authentication")
        if auth:
            if not password:
                raise OBSError("OBS requires a password: set OBS_WS_PASSWORD or pass --password")
            secret = base64.b64encode(hashlib.sha256((password + auth["salt"]).encode()).digest()).decode()
            ident["authentication"] = base64.b64encode(
                hashlib.sha256((secret + auth["challenge"]).encode()).digest()).decode()
        self._send_json({"op": 1, "d": ident})
        try:
            msg = self._recv_json()
        except (OBSError, OSError):
            msg = {}
        if msg.get("op") != 2:
            raise OBSError("auth failed (wrong password?)")

    # -- websocket framing -------------------------------------------------
    def _handshake(self, host, port):
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET / HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
               f"Sec-WebSocket-Protocol: obswebsocket.json\r\n\r\n")
        self.sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise OBSError("connection closed during handshake")
            resp += chunk
        head, self._buf = resp.split(b"\r\n\r\n", 1)
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise OBSError(f"websocket upgrade refused: {head[:80]!r}")
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest())
        if accept not in head:
            raise OBSError("bad Sec-WebSocket-Accept")

    def _read(self, n):
        while len(self._buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise OBSError("connection closed")
            self._buf += chunk
        data, self._buf = self._buf[:n], self._buf[n:]
        return data

    def _send_json(self, obj):
        payload = json.dumps(obj).encode()
        head = bytearray([0x81])
        n = len(payload)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.sock.sendall(bytes(head) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def _recv_json(self):
        while True:
            b1, b2 = self._read(2)
            op, n = b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            mask = self._read(4) if b2 & 0x80 else None
            data = self._read(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if op == 0x8:
                raise OBSError("OBS closed the connection")
            if op == 0x9:  # ping -> pong
                continue
            if op == 0x1:
                return json.loads(data.decode())

    # -- requests ----------------------------------------------------------
    def request(self, rtype, data=None):
        rid = str(uuid.uuid4())
        self._send_json({"op": 6, "d": {"requestType": rtype, "requestId": rid, "requestData": data or {}}})
        while True:
            msg = self._recv_json()
            if msg.get("op") == 7 and msg["d"].get("requestId") == rid:
                st = msg["d"]["requestStatus"]
                if not st.get("result"):
                    raise OBSError(f"{rtype} failed: {st.get('comment') or st.get('code')}")
                return msg["d"].get("responseData") or {}

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def run(cmd, arg=None, **kw):
    obs = OBS(**kw)
    try:
        if cmd == "status":
            s = obs.request("GetRecordStatus")
            scene = obs.request("GetCurrentProgramScene").get("currentProgramSceneName")
            return {"recording": s.get("outputActive"), "paused": s.get("outputPaused"),
                    "timecode": s.get("outputTimecode"), "scene": scene}
        if cmd == "start":
            return obs.request("StartRecord")
        if cmd == "stop":
            return obs.request("StopRecord")  # {"outputPath": ...}
        if cmd == "pause":
            return obs.request("PauseRecord")
        if cmd == "resume":
            return obs.request("ResumeRecord")
        if cmd == "scene":
            return obs.request("SetCurrentProgramScene", {"sceneName": arg})
        if cmd == "chapter":
            return obs.request("CreateRecordChapter", {"chapterName": arg})
        if cmd == "version":
            return obs.request("GetVersion")
        raise OBSError(f"unknown command {cmd}")
    finally:
        obs.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command")
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=4455)
    ap.add_argument("--password", default=os.environ.get("OBS_WS_PASSWORD"))
    a = ap.parse_args()
    try:
        print(json.dumps(run(a.command, a.arg, host=a.host, port=a.port, password=a.password), ensure_ascii=False))
    except ConnectionRefusedError:
        sys.exit("OBS not reachable: is OBS open with Tools > WebSocket Server Settings enabled?")
    except OBSError as e:
        sys.exit(f"OBS error: {e}")


if __name__ == "__main__":
    main()
