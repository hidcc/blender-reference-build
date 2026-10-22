# Hard-surface techniques that work through bpy

All of these are in `scripts/hslib.py` or are short enough to inline.

## Contents
- Curved armour: profile sweeps
- Clean panel seams: grooves, not split edges
- Bands and stripes: bisect, don't pick faces
- Recessed ports, turbines, bezels
- Placing details on a curved surface
- Limbs
- Bugs hit last time

## Curved armour: profile sweeps

`sweep2(path_fn, tan_fn, t0, t1, width_fn, height_fn, n_off=, b_off=, matrix=)` sweeps a rounded-rectangle profile (a superellipse, `power≈0.38`) along a cubic Bezier in a local plane and caps both ends.
- Width and height are functions of t. Taper, or swell in the middle, with `sin(pi*(a+b*t))**p`, for example a crescent leg that is thick near the top and thin at the tip.
- Splitting one path into consecutive t-ranges with small gaps gives separate **armour plates** with real gaps.
- `b_off` / `n_off` (also callables) offset the profile sideways or outward. Use them for **inserts** on the flanks (thin profile at `b_off = ±(W/2 + ε)`), **spines** on the concave side, and **glow strips** on the convex side.
- Add a Bevel modifier (limit by angle) and smooth by angle (`mesh.set_sharp_from_angle`).

Proportions matter more than detail. The first version of the spider legs was half as thick as the reference and read as hoses. Check the thickness against the reference right after the first instance.

## Clean panel seams: grooves, not split edges

Splitting edges along bisect cuts and then using Solidify + Bevel gave crinkled shading on slivers. What worked:
1. Build the shell mesh (e.g. a UV sphere scaled to an ellipsoid).
2. For each seam plane, bisect at `+g` and `−g` (g ≈ 5–7 mm), then delete the faces whose centres lie within `g` of the plane. A predicate limits which faces are cut, e.g. only `|x| > 0.3`.
3. `dissolve_degenerate`, then Solidify (inward, ~45 mm) + Bevel (~10 mm).
4. Put a smaller dark "core" mesh inside, so the grooves read as dark lines.

## Bands and stripes: bisect, don't pick faces

Selecting UV-sphere faces by `|x| < w` gives a zig-zag border. Instead, bisect with `clear_outer=True` on each side plane, scale slightly up (×1.012), and add Solidify outward. The borders come out perfectly straight.

## Recessed ports, turbines, bezels

- Cut the hole in the shell by deleting faces within an angle of the port axis.
- Stack along the axis, from outside to inside: lip ring (tube) → cup (dark cylinder) → fan blades → machined ring → hub → cap → bolt circle.
- `cylinder(..., ring=inner_r)` makes a tube; `base=True` puts the origin at one end (good for pistons).
- Keep the inner core **smaller than the port depth** along the port axis. Last time the core sphere poked through the cup and hid everything inside.

## Placing details on a curved surface

For an ellipsoid with centre C and radii R, the point for direction u is `p = C + u*R` and the normal is `n = normalize(p.x/R.x², p.y/R.y², p.z/R.z²)`. Orient the detail with local Z along n: build the basis from `up × n`, and switch `up` when it is nearly parallel to n. This covers vents (frame + slats), hatches, glow slits, bolt rows and nubs.

## Limbs

`build_limb(prefix, M, ctrl, knee, scale, collection, manip=False)` builds, in limb-local space (origin at the shoulder, +X outward):
- a shoulder hub, a femur with an armour cap, and a knee joint with emissive rings
- three tibia plates, side inserts, a spine, a rubber foot, a tip glow strip and a top clip
- a piston: a housing on the femur and a rod on the tibia, each tagged with the object it should track
- optionally a two-finger claw

Every object is tagged `obj["rig"]` (shoulder / femur / tibia / claw / piston_h / piston_r) and `obj["limb"]`, so the rig step can bind parts automatically. Reuse it for any jointed appendage. For a different design, change `ctrl`, `knee`, and the W/H functions.

## Bugs hit last time (check these)

- **Radial arrays rotated twice.** If the blades are already distributed around the port axis, don't rotate the whole set again; they collapse into a line.
- **Solid look is fine, material look is blank.** The `look` tool rendered blank in Material Preview. Verify with an `app_screenshot` of the window, or switch `look` to solid.
- Object names that are too generic collide on rebuild. Always prefix them and `clear(prefix)` before a rebuild.
