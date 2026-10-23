# Case study: delivery drone from a generated sheet (Model tier, ~25 min)

Input: one-sentence description → `codex-image-gen` turnaround sheet. The first pass had two defects: the top view was drawn larger, and the rotors overlapped in the side view. One `--image` fix pass corrected both, and the fixed sheet became `ref/sheet.png`, with `ref/prompt.txt` written from it.

## Steps (files in `steps/`, run with `mcp_send.py code`)
1. `layout.py`: constants, real scale in metres, front = −Y.
2. `01_body.py`: upper/lower shell, a dark core showing in the seam, an inset top panel.
3. `02_arms_ducts.py`: X arms with folding hinges, ducted rings, motor struts and three-blade rotors.
4. `03_under.py`: camera gimbal, cargo pod with latch, landing gear with skids, cyan strips, vents.
5. `04_materials_studio.py`: presets, the cyclorama, six area lights, two cameras, Cycles/AgX.
6. Test render at 50 %, then the hero and low stills at 100 % / 128 spp. About 20 s each on an Apple M5 GPU.

## What the comparison caught
- **Body too wide, duct spacing wrong.** The first layout guessed the proportions. Re-measuring pixel ratios on the top view gave body 0.18 × 0.34, ducts at (±0.215, ±0.185), r 0.10. Measure first.
- **Ducts and blades too thin.** The duct height/diameter ratio on the sheet is about 0.25; the first version was 0.17. The blades are paddles, not sticks.
- **Dark void behind the second camera.** The cyc faced only the hero camera. Fixed by re-aiming it at render time (`steps/render_low.py`).
- **First hero framing too tight.** A near duct hid the body. Higher and farther away, at 55 mm, fixed it.
