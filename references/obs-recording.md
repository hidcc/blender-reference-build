# Recording the build with OBS

The making-of video is a screen recording of Blender's viewport while the build runs. The skill supplies the camera work (`shots`) and the build-log overlay (`hud`). OBS only captures the window. Use one of two ways:
- **live**: record while you build the model for the first time
- **replay**: build once, save every step as a file, then re-run the steps from an empty scene with `scripts/replay.py` while OBS records

Replay is the recommended way: the take is clean, repeatable and can be redone.

## Contents
- One-time OBS setup (tell the user; they do it)
- Framing the viewport
- Recording control from Claude (OBS WebSocket)
- Replay: re-running the build for a clean take
- Live recording tips
- Editing the timelapse

## One-time OBS setup

These are steps for the user. Claude can't grant macOS permissions and shouldn't change app settings unasked.
1. Install OBS 28 or later (`brew install --cask obs` or obsproject.com). Version 28+ has the WebSocket server built in.
2. macOS: allow OBS in System Settings → Privacy & Security → **Screen Recording**, then restart OBS.
3. Settings → Video: base and output resolution **1920×1080**, **30 fps**.
4. Settings → Output → Recording:
   - format **MKV**: crash-safe; convert afterwards with File → Remux Recordings
   - encoder **Apple VT H264 Hardware** (macOS), or NVENC / QuickSync elsewhere
   - about 20 000 Kbps
5. Add a scene, e.g. "Blender Build", with a **macOS Screen Capture** source in Window mode → Blender. On other platforms use Window Capture.
6. Tools → **WebSocket Server Settings**:
   - Enable, port 4455
   - set a password
   - the user exports it as `OBS_WS_PASSWORD` in the shell Claude uses (e.g. in `~/.zshrc`)

   Never put the password in a script, the skill or a commit.

## Framing the viewport

Reference making-of videos show only the 3D viewport. Either:
- in Blender, hover the viewport and press `Ctrl+Space` (maximize area); or
- in OBS, right-click the source → Transform → **Edit Crop** (or Alt-drag) down to the viewport.

Keep the Blender window the same size for the whole session, because the crop depends on it. Before recording, the clay setup from phase 2 should already hide the grid, axes, gizmos and N-panel. The HUD is drawn inside the viewport, so it is captured automatically.

## Recording control from Claude (OBS WebSocket)

`scripts/obs_control.py` is a dependency-free OBS WebSocket v5 client (stdlib only).

```bash
python3 obs_control.py status            # is OBS reachable, is it recording?
python3 obs_control.py scene "Blender Build"
python3 obs_control.py start             # StartRecord
python3 obs_control.py pause | resume
python3 obs_control.py stop              # StopRecord, prints the output file path
python3 obs_control.py chapter "07 Legs" # chapter marker (only with Hybrid MP4; harmless otherwise)
```

Options: `--host` (default localhost) and `--port` (default 4455). The password comes from `$OBS_WS_PASSWORD`, or from `--password`.

Before starting a take, run `status` first. "connection refused" means OBS is closed or the WebSocket server is off. "auth failed" means the password is wrong or not set. In either case, tell the user what to fix rather than retrying.

Starting or stopping a recording is a visible action on the user's machine. Do it when the user asked for a recorded take, and say so when you start.

## Replay: re-running the build for a clean take

For replay to work, every build step must exist as a file. In recording projects, write each step to `steps/NN_name.py`:
- Two-digit order; `00_setup.py` clears the scene and sets the clay look.
- Each file imports `hslib`, builds its part, then calls `hud(...)` and `shots([...])`.

Run the files with `python3 mcp_send.py code steps/NN_name.py` instead of pasting code into `execute_blender_code`. The build and the replay then use exactly the same code.

```bash
python3 replay.py steps/                       # run every NN_*.py in order
python3 replay.py steps/ --obs --scene "Blender Build"   # start OBS, run, stop OBS
python3 replay.py steps/ --from 06 --to 11     # re-shoot only part of the build
python3 replay.py steps/ --dry-run             # list what would run
```

For each step, replay.py:
1. sends the file through the add-on socket
2. waits until the queued viewport shots have finished (it polls `hs_timer` in Blender)
3. holds for `--hold` seconds (default 1.5), so each milestone gets a beauty pause

If a step fails, replay stops, prints Blender's error and, with `--obs`, stops the recording so the take isn't left running. With `--from`, the script runs `00_*` first only when you pass `--setup`, because a partial re-shoot usually wants the earlier geometry to stay.

Replay rebuilds geometry in the user's live scene. Run it on a fresh or saved file and confirm with the user before replaying over unsaved work.

## Live recording tips

- The user shouldn't touch the viewport during a take: a manual orbit fights the queued shots.
- A new `shots(...)` call appends to the queue, so issuing the next build step early doesn't cut a move short. Long scripts block the UI while they run, though, so keep the heavy geometry in its own step, before the camera work.
- Rendering (test stills, Cycles) runs in a separate process and doesn't disturb the take.
- Use `pause` / `resume` around long waits, such as shader compilation after switching to Material Preview.

## Editing the timelapse

- Speed the raw recording up 10–30× in any editor, or with ffmpeg: `ffmpeg -i take.mkv -vf "setpts=PTS/20" -an -r 30 timelapse.mp4`.
- Cut back to normal speed on beauty orbits and material reveals.
- End on the final rendered shot (phase 8).
