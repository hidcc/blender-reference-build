# Rigging hard-surface subjects and procedural walk cycles

Hard-surface models don't need skinning. Each rigid part follows one bone.

## Armature by script

```python
area, r3d = L.view3d(); region = next(r for r in area.regions if r.type == 'WINDOW')
bpy.context.view_layer.objects.active = arm
with bpy.context.temp_override(area=area, region=region, active_object=arm, object=arm):
    bpy.ops.object.mode_set(mode='EDIT')
    # eb = arm.data.edit_bones; eb.new(...) ...
    bpy.ops.object.mode_set(mode='POSE')
```

Typical hierarchy:
- `root` (moves the whole subject) → `body` (suspension: bob, roll, pitch) → `head`, plus `shoulder_X` → `femur_X` → `tibia_X` (connected)
- `ik_X` foot targets with **no parent**, so they stay planted in world space

Add an IK constraint on each tibia (`chain_count=2`, target `ik_X`), and `lock_ik_y` on the femur and tibia so they don't twist. Without a pole target the solver keeps the rest-pose bend plane, which is fine for legs modelled in a vertical plane.

Bone-local axes: for a bone pointing +Z, pose `location = (dx, dz, -dy)` in world terms. For the root pointing −Y, `location.y` is the forward distance.

## Binding parts

```python
mw = o.matrix_world.copy()
o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = bone_name
o.matrix_world = mw
```

Choose the bone from the `rig` / `limb` tags that `build_limb` writes.

Pistons: add a `DAMPED_TRACK` (`TRACK_Z`) on the housing, aimed at the eye on the other bone, and another on the rod aimed back. Both cylinders need their origin at the base. Cables: parent them to the moving segment, or hook their ends to empties on the two bones.

## Procedural gait (bake a key every frame)

1. Speed profile `v(f)`: settle, a smoothstep ramp, then cruise. Distance `s(f)` is the cumulative sum.
2. Phase each leg. A diagonal pair gait for 4 legs is 0 / 0.5; for 6 legs use a tripod 0 / 0.5. Cycle `LC` (e.g. 24 f), swing `LS` (e.g. 10 f, duty about 0.6).
3. For each touchdown k: plant `P_k = home + forward * s(td_k + (LC−LS)/2)`, so the foot sits under its hip at mid-stance.
4. The foot holds `P_k` until lift-off, then moves by smoothstep to `P_{k+1}`, plus a lift `h·sin(πu)`. Skip the lift when the step is under ~3 cm, so the subject doesn't stomp in place while starting up.
5. Body: a dip at each pair touchdown (twice per cycle), a small roll toward the planted diagonal, a slight forward lean when cruising, all scaled by `v/vmax`.
6. Secondary motion: sine sways on manipulators, the head and antennas, phase-offset per side.

The case study's numbers (`case-study-spider.md`) are a tested starting point for a 4-legged walker.

## Verify

- **Foot slide/reach:** for sampled frames, measure `|tibia.tail − ik.head|` in world space. It should be about 0 everywhere; anything over ~5 cm means unreachable targets (step too long, or the body too high).
- **Clipping:** check `look mode:"frames"` from the side and from the front at stance and swing peaks.
- **Exit and timing:** `look mode:"frames" view:"camera"` at 1, 25%, 50%, 75%, the exit frame and the last frame. If the subject must leave the frame by time T, tune `VMAX` (or the camera path) until the frame at T is empty and stays empty.
