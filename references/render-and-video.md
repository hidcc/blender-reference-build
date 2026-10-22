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
4. Check the result: `ffprobe` the duration, extract frames at the start, middle, exit point and end, tile them with ffmpeg `xstack`, and look at the sheet.

## Viewport recording (OBS)

The rendered camera stays calm; the expressive camera work is the viewport. In recording mode:
- `hud(step, title, sub, pct)` draws the build log, and the label is set with `hud_label("PROJECT-01")`
- `shots([...])` queues eased orbit, push-in and pull-back moves with holds
- after each material or lighting stage, queue a slow orbit so highlights move across the surfaces
- hide the grid, axes and gizmos, keep a flat grey background, and use studio solid lighting with cavity during clay stages
