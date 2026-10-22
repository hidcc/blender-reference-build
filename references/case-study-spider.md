# Case study: Mechanical Spider (what a full Video-tier run looked like)

Brief: a detailed production prompt plus a concept sheet and hero renders. The subject is a compact orange armoured robot with a black central stripe, 4 crescent walking legs, 2 front manipulators, an emissive sensor head and side turbine housings. The deliverable: a studio render and a 10 s walk that exits the frame. The original project was laid out as `steps/` (shared lib + one script per step, e.g. `19_walk.py`), `ref/` (brief and images), `mechanical_spider.blend` and `renders/`. Use the same layout for new projects.

## Layout constants (decided before modelling)
- Body ellipsoid: centre (0,0,1.35), radii (0.95, 1.10, 0.90). Front is −Y.
- Legs at yaw ±50° / 180±50° from +X. Shoulder at local (0.92,0,0.05), knee (0.55,0,0.50), foot (2.0,0,−1.40), so the feet land exactly on z=0.
- Tibia Bezier control points: (0.55,0.5) → (1.3,0.95) → (2.2,0.35) → (2.0,−1.4) in the leg's XZ plane.
- Head centre (0,−1.12,1.0). Manipulators mounted at (±0.42,−0.92,0.95).

## Step log (~35 MCP calls for modelling)
1. Ellipsoid blockout.
2. Black stripe (bisected band).
3. Side ports cut, solidified shell, turbine housing.
4. Sensor head with a flat optic face and lenses.
5. Underbody drum and actuator blocks.
6. First leg; thickened after comparing with the reference.
7. The other three legs.
8. Manipulators.
9. Yaw motors and brackets.
10. Struts.
11. Foot pads.
12. Seams as grooves.
13. Vents and hatches.
14. Cables.
15. Bolts, light strips, top nub.
16. Materials revealed in stages.
17. Emissives and roughness noise.
18. Rig.
19. Walk.
20. Studio.
21. Render.

## Numbers that worked
- Walk: cycle 24 f, swing 10 f, VMAX 0.052 m/f, ramp over frames 6–46. Total ~11 m in 240 f; exits frame ~9.4 s.
- Camera: 35 mm, from (6.3,−7.3,1.8) tracking an empty from (0.4,−1.0,1.0) to (−0.15,−4.1,0.95), easing out by frame 205.
- Lights (W): key 1000 / fill 220 / rims 900 & 700 / top 350 / backdrop 650. Backdrop albedo (0.40,0.29,0.20). World 0.25.
- Orange armour (0.9,0.2,0.018), roughness 0.26–0.38 noise, coat 0.35. Emissive (1.0,0.22,0.02) at 5.

## What went wrong and was fixed
- The add-on would not register (the stale-module trap). Fixed headlessly, then Blender was restarted.
- The first legs were too thin, the turbine blades collapsed into a line, the core sphere hid the port, and the stripe edges zig-zagged.
- The first render was overexposed (pastel orange) and the camera was too side-on (head hidden). Fixed by cutting the lights by ~2.5× and moving the camera toward the front.
