---
name: blender-reference-build
description: Build a model in a live Blender session through MCP for Blender, working from reference images and/or a production prompt. When there are no images, it first generates a reference sheet via Codex (codex-image-gen). The skill covers connecting (including fixing an add-on that won't connect), blockout, hard-surface detailing, step-by-step material reveal and studio lighting, and recordable viewport camera moves with a build-log overlay. Rigging, animation and the rendered video are an OPTIONAL phase, run only when the request asks for motion. Use this skill whenever someone wants Blender to recreate, model, build or "reproduce" something from reference images, a concept sheet, a prompt file or just a description — robots, vehicles, props, products, creatures, mechs — and also for "do this Blender MCP case study", "make a timelapse / making-of in Blender", "model this and render it", or "animate it walking and render the video", even if they don't say "skill" or "MCP".
---

# Blender reference build (via MCP for Blender)

Turn reference images and a brief into a finished Blender scene. Do the building in the user's live Blender with the `mcp__blender__*` tools. When the user will record the session, also make the viewport look good while you work.

The approach comes from a full reproduction of a hard-surface robot (the "Mechanical Spider" case study). See `references/case-study-spider.md` for what it looked like in practice.

## 0. Decide the scope before touching Blender

Read the brief (prompt file, message, images). Then fix two choices.

**Deliverable tier.** The motion phase costs hours of render time, so pick the tier up front:

| Tier | When | Phases |
|---|---|---|
| **Model** | "model / build / recreate this", no mention of motion | 1–6, then stills |
| **Animation** | asks for a rig, walk, motion, turntable, "animate" | 1–6 + 7 |
| **Video** | asks for a rendered clip/MP4, "exit the frame", "10 seconds", a timelapse deliverable | 1–6 + 7 + 8 |

If the brief is ambiguous, for example a reference sheet with no word about motion, ask once with AskUserQuestion. Offer: Model + stills (recommended), Animation (no final render), Full video. Don't build a rig nobody asked for.

**Recording mode.** Is the user screen-recording Blender (OBS, timelapse, "making-of")? If yes, use the viewport choreography and the build-log HUD from phase 2, and read `references/obs-recording.md`. That file covers the user's OBS setup, framing the viewport, starting and stopping the recording from Claude over OBS WebSocket (`scripts/obs_control.py`), and the replay workflow (`scripts/replay.py`): build once, then re-run the saved steps from an empty scene for a clean take. If the user isn't recording, skip all of this and just verify with `look`.

Also note what the brief forbids. "No environment" means studio only. "Don't redesign" means stay close to the reference proportions. Re-read those constraints before each phase.

## 0b. No references? Generate them first

When the user describes a subject but gives no images, or the images are too vague to measure (one perspective shot), make references before modelling. Guessing the shape from text costs far more rework later.

1. If the `codex-image-gen` skill is available, use it. Otherwise ask the user for images, or for permission to use another image tool.
2. Generate a **reference sheet** with its turnaround template: front, side, top and back orthographic views on one sheet, a 3/4 hero view, 2–3 detail close-ups, plain background, flat light, primitive-based forms. Put the user's design words into the brief (colours, part counts, proportions, style).
3. Review the sheet as a modeller would:
   - Are the part counts and proportions the same in every view?
   - Is the side view truly orthographic?
   - Are there forms you can't build from sweeps and primitives?

   Fix with one or two `--image` edit passes. Stay within the codex-image-gen budget.
4. Save to `ref/sheet.png` (plus `ref/hero.png` if you made one), and write `ref/prompt.txt`: a short brief with the subject, key proportions read off the sheet, palette, build-order hints and constraints. From here on, treat these files like user-supplied references.
5. Show the sheet to the user before modelling: "this is what I'll build". A quick yes here saves a whole rebuild.

If something about the sheet causes trouble during modelling (an ambiguous part, an impossible view), add a line about it to codex-image-gen's `references/prompt-templates.md`, so that future sheets avoid it.

## 1. Connect to Blender

1. Call `mcp__blender__get_addon_status`, then `get_scene_info`. If both answer, you are connected.
2. If you get "Could not connect", read `references/connection-troubleshooting.md`. It covers how to tell "add-on not enabled" apart from "server not started", the stale-module-name trap in saved preferences, and how to drive Blender's UI with computer use. Blender ignores background clicks unreliably, so take full-screen control and bring Blender to the front first.
3. When the user asked you to open Blender and enable the add-on yourself, do it with computer use: Edit → Preferences → Add-ons → search "MCP" → tick it → Save Preferences. Then open the N-panel tab "MCP for Blender" and click "Connect to MCP server". If the tab doesn't appear, the add-on didn't register; go to the troubleshooting file.

## 2. Set up the workspace

- Copy `scripts/hslib.py` next to the project, for example `<project>/steps/hslib.py`. Import it in every `execute_blender_code` call with `sys.path.insert(...)` + `importlib.reload(...)`, so that edits to the file take effect without restarting Blender. It provides:
  - geometry: sweeps, cylinders/tubes, tori, boxes, `place`, rigid limb builder
  - materials: named slots that start as clay and get revealed later
  - camera: queued smooth viewport moves (`shots`)
  - overlay: the build-log HUD (`hud`)
- Use the bundled `scripts/mcp_send.py` (`python3 mcp_send.py code file.py`) to run long scripts from a file. It talks to the same socket as the MCP server, so it is handy for anything you want saved in the project as a reproducible step file.
- Clear the default scene. Set the viewport to clay: solid shading, single grey colour, cavity on, no grid floor or axes, sidebar hidden. Set fps and frame range now if motion is planned.
- Lay the subject out on paper before modelling: centre, main radii, attachment points, limb angles. Put these numbers in one place (constants at the top of a step file) so every later step reuses them. Reworking proportions late is the most expensive mistake.

## 3. Model in the order a viewer can follow

Follow the brief's build order if it gives one. Otherwise go from big to small: main mass, major secondary masses, the hero feature (head/sensor/cockpit), underside, the first instance of a repeated part, the remaining instances, joints/pivots, actuators/pistons, contact parts (feet/wheels), panelling, vents/hatches, cables, fine details.

For each step:
1. Build just that step with one script. Name objects with a part prefix (`Body_`, `Leg_FR_`, `Head_`), so a step can be rebuilt with `clear(prefix)`. In recording mode, write the step to `steps/NN_name.py` and run it with `mcp_send.py code`, because the file then doubles as the replay script for the clean take. Otherwise `execute_blender_code` is fine.
2. In recording mode, update the HUD and queue 2–4 shots, mixing scales: macro (whole silhouette), medium (assembly), micro (joint/bolt). Shots are interpolated in angle, so moves read as orbits and push-ins rather than jumps.
3. **Look before moving on.** Call `look` with `mode: "angles"` and two views (one matching the reference angle, one revealing) and compare against the reference image. Fix problems now: wrong orientation, parts hidden inside other parts, thin or wrong proportions. These are cheap to fix at this point and expensive later.

Techniques that held up well, such as sweeps for curved armour, clean panel seams and recessed ports, are in `references/hard-surface-techniques.md`. Read it before the first detail step. It also lists the specific bugs hit last time.

## 4. Reveal the materials in stages

Every part gets a named material slot from the start, all clay-grey. Reveal them in an order that reads well on camera: dark mechanics → main colour → secondary/inserts → metals → glass/optics → emissives → roughness breakup. Use `reveal(name)` with presets edited in `PRESETS`, and add an orbit after each stage.

- Switch the viewport to Material Preview first. `look` may return a blank image in material/rendered mode. Wait for shader compilation, or check with an `app_screenshot` of the Blender window.
- Put colours on shader node inputs. `diffuse_color` only drives the solid viewport; hslib sets both.

## 5. Light a studio and add the camera

- Studio only, unless the brief wants an environment: a seamless cyclorama (floor curving into a wall) oriented to face the camera, plus area lights (key, fill, two rims, top softbox, a backdrop light for the gradient). Aim them with Track To at the subject.
- World: dim and warm, low strength. Avoid HDRIs when the brief says no busy reflections.
- Camera: a calm 3/4 view, 35–50 mm, Track To an empty, light DoF. Subtle tracking only; the expressive moves belong to the viewport, not the render camera.
- Render settings: Cycles, AgX (pick the look from the enum, e.g. "AgX - Medium High Contrast"), denoise, 1920×1080, the brief's fps.

## 6. Test render and compare with the reference

Save the .blend. Render 1–2 test frames **in a separate background Blender process** (`scripts/render_still.sh`), so the user's session stays free. Use half resolution and low samples first. Compare with the reference and fix the usual problems:
- overexposure washing out saturated colours (lower light energy; never "fix" it with base colour)
- emissives clipping to white (lower strength, more saturated colour)
- the hero feature hidden behind a foreground part (move the camera)

Then render one full-quality hero still. **Model tier ends here.** Report back with the stills.

## 7. (Optional) Rig and animate

Only for the Animation/Video tiers. Read `references/rig-and-walk.md`. In short:
- Build an armature by script (`temp_override` into the 3D view for edit-mode ops).
- Parent each rigid part to its bone, keeping its world transform (`parent_type='BONE'`, then reassign `matrix_world`).
- Add IK on limb chains and Damped Track for pistons.
- Generate the motion procedurally and bake a key on every frame: planted feet, swing arcs, suspension, secondary motion.
- **Verify numerically, not just visually.** Measure the distance between each IK tip and its target on every frame (it should be about 0), then check the camera framing at 6–8 frames with `look mode:"frames" view:"camera"`. Example: "exits frame by 9.5 s, empty hold after".

## 8. (Optional) Render the video

Only for the Video tier. Read `references/render-and-video.md`.
- First run a quick EEVEE preview MP4 (`scripts/render_preview.py`). It takes minutes and catches timing and framing problems.
- Estimate the Cycles time from one full-quality frame (per-frame seconds × frame count) and tell the user before starting. A long render needs the user's go-ahead.
- Run Cycles in the background with `scripts/render_final.py`: GPU/Metal, a resumable PNG sequence (`use_overwrite=False`, `use_placeholder=True`), wrapped in `caffeinate` on macOS. Watch the process with a `run_in_background` wait loop, then encode with ffmpeg (`scripts/encode.sh`).
- Pull 4 frames from the finished video (start / mid / exit / end) and look at them before calling it done.

## 9. Report

Tell the user:
- what was built
- where the .blend, the stills and the video are
- what deviates from the reference
- what was not done (e.g. "final Cycles render not started", "no OBS recording made by me")

Send the key images or the video with SendUserFile.

## Notes on working style

- Small steps and a look after each. One script per build step keeps failures local, and a broken step can be rebuilt by prefix.
- Keep the user's session usable. Long renders go in a separate `blender -b` process, never in the UI session.
- Save the step scripts into the project (e.g. `steps/NN_name.py`), so the whole build can be replayed for a recording (`scripts/replay.py steps/ --obs`).
