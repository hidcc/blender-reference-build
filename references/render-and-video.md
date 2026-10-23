# Rendering stills and video

Always render in a **separate background Blender** on the saved file. Rendering inside the user's session freezes the MCP connection and the UI.

```bash
python3 mcp_send.py code save.py          # or execute_blender_code: bpy.ops.wm.save_mainfile()
```

## Stills

`scripts/render_still.sh <file.blend> <out_prefix> <percent> <samples> <frame> [frame...]`
- Turns on GPU (Metal on Apple Silicon, otherwise whatever Cycles offers) via `gpu_setup.py`. Without it, background renders fall back to CPU, about 3× slower.
- First pass at 50 % and 64 samples; the hero still at 100 % and 128 samples.
- Measured on an Apple M5: about 30 s per half-res frame, about 2 min per 1080p/128-sample frame.

What to look for against the reference:
- Saturated paint looking pastel: the lights are too strong. Lower their energy by 2–3×, and darken the backdrop's albedo.
- Emissive rings clipping to white: strength around 5, and a more saturated emission colour.
- The hero feature hidden: move the camera, not the model.
- **A second camera angle shows a dark void behind the subject.** The cyclorama faces one camera. For each extra angle, re-aim the cyc and its backdrop light at that camera in a render-time `--python` script, and leave the saved scene alone.
- **Light power depends on distance.** Values that worked for a ~2 m subject lit from 5–6 m (key ~1000 W) are far too strong for a 0.6 m product lit from ~1.4 m. Scale by (distance ratio)²: the drone used key 55 / fill 14 / rims 40 & 32 / top 22 / backdrop 30 W.

## Preview video (fast)

`scripts/render_preview.py` switches to EEVEE in the background process only (the .blend is not modified), turns on raytracing/AO/motion blur and writes an H.264 MP4. A 240-frame 1080p clip takes a few minutes. Show it to the user to approve timing and framing before any long Cycles run.

Blender 5.x video output: set `image_settings.media_type = 'VIDEO'` (wrapped in try/except for older versions), then `file_format = 'FFMPEG'`, `ffmpeg.format = 'MPEG4'`, `codec = 'H264'`.

## Final Cycles video

1. Estimate the time: hero-still seconds × frames. Say it to the user and get a go-ahead when it is over about 30 min.
2. Start it detached and resumable:
   ```bash
   mkdir -p renders/final
   nohup caffeinate -i Blender -b file.blend --python render_final.py -a > renders/final/render.log 2>&1 &
   ```
   `render_final.py` sets the GPU, samples, `use_overwrite=False` and `use_placeholder=True`. Re-running the same command resumes and skips the frames already done.
3. Wait without polling, using a `run_in_background` loop: `while kill -0 $PID; do sleep 60; done`, then count the frames, grep the log for errors, and encode (`scripts/encode.sh renders/final renders/final.mp4 24`).
   To stop a render: kill the Blender PID; a broad `pkill -f render_final.py` also kills the waiting loop, since the loop's own command line matches. Then delete the zero-byte placeholder of the frame that was in progress (`find renders/final -name 'frame_*.png' -size -10k -delete`), so a resume re-renders it.
4. Check the result: `ffprobe` the duration, extract frames at the start, middle, exit point and end, tile them with ffmpeg `xstack`, and look at the sheet.

## Viewport recording (OBS)

The rendered camera stays calm; the expressive camera work belongs to the viewport. For OBS setup, recording control and the replay workflow, see `obs-recording.md`.
