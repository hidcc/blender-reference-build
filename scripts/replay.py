"""Replay saved build steps (steps/NN_name.py) in the live Blender for a clean recorded take.

usage: python3 replay.py STEPS_DIR [--from NN] [--to NN] [--setup] [--hold SEC]
                         [--obs] [--scene NAME] [--dry-run]

Each step is sent through the MCP for Blender add-on socket, then replay waits until the
viewport shots queued by hslib.shots() have finished, holds, and moves on.
"""
import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_send import send  # noqa: E402

BUSY = "import bpy\nns = bpy.app.driver_namespace\nprint('BUSY' if ns.get('hs_timer') or ns.get('hs_shots') else 'IDLE')"


def run_code(code, port):
    r = send("execute_code", {"code": code}, port=port)
    if r.get("status") != "success":
        raise RuntimeError(r.get("message") or r)
    return str((r.get("result") or {}).get("result", ""))


def wait_idle(port, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if "IDLE" in run_code(BUSY, port):
            return True
        time.sleep(0.5)
    return False


def steps(directory):
    out = []
    for name in sorted(os.listdir(directory)):
        m = re.match(r"^(\d{2})_.+\.py$", name)
        if m:
            out.append((m.group(1), os.path.join(directory, name)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("steps_dir")
    ap.add_argument("--from", dest="start", default="00")
    ap.add_argument("--to", dest="end", default="99")
    ap.add_argument("--setup", action="store_true", help="also run 00_* when --from is later than 00")
    ap.add_argument("--hold", type=float, default=1.5, help="seconds to hold after each step's shots")
    ap.add_argument("--port", type=int, default=9876)
    ap.add_argument("--obs", action="store_true", help="start/stop OBS recording around the replay")
    ap.add_argument("--scene", help="OBS scene to switch to before recording")
    ap.add_argument("--obs-port", type=int, default=4455)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    plan = [(n, p) for n, p in steps(a.steps_dir) if a.start <= n <= a.end]
    if a.setup and a.start > "00":
        plan = [(n, p) for n, p in steps(a.steps_dir) if n == "00"] + plan
    if not plan:
        sys.exit("no NN_*.py steps matched")
    for n, p in plan:
        print(f"{n}  {os.path.basename(p)}")
    if a.dry_run:
        return

    obs = None
    if a.obs:
        import obs_control
        kw = dict(password=os.environ.get("OBS_WS_PASSWORD"), port=a.obs_port)
        obs_control.run("status", **kw)  # fail fast before touching Blender
        if a.scene:
            obs_control.run("scene", a.scene, **kw)
        obs = lambda cmd, arg=None: obs_control.run(cmd, arg, **kw)  # noqa: E731
        obs("start")
        print("OBS recording started")
        time.sleep(1.0)
    try:
        for n, p in plan:
            t0 = time.time()
            if obs:
                try:
                    obs("chapter", os.path.basename(p)[:-3])
                except Exception:
                    pass  # chapters need Hybrid MP4; ignore otherwise
            out = run_code(open(p).read(), a.port)
            if out.strip():
                print("   ", out.strip().splitlines()[-1][:160])
            if not wait_idle(a.port):
                print("    warning: shots still running after timeout")
            time.sleep(a.hold)
            print(f"{n}  done in {time.time() - t0:.1f}s")
    except Exception as e:
        print(f"step failed: {e}", file=sys.stderr)
        raise SystemExit(1)
    finally:
        if obs:
            print("OBS stopped:", obs("stop"))


if __name__ == "__main__":
    main()
