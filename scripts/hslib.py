"""Hard-surface build helpers for MCP-driven Blender sessions.

Import inside execute_blender_code:
    import sys, importlib; sys.path.insert(0, "<dir>"); import hslib as L; importlib.reload(L)
"""
import math
import bpy
import bmesh
import blf
from mathutils import Vector, Matrix, Euler, Quaternion

NS = bpy.app.driver_namespace

# ---------------------------------------------------------------- scene utils
def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


ROOT = "Subject"  # top-level collection for the model; set L.ROOT before building


def sub_coll(sub):
    return coll(sub, coll(ROOT))


def clear(prefix):
    for o in [o for o in bpy.data.objects if o.name.startswith(prefix)]:
        bpy.data.objects.remove(o, do_unlink=True)


def link(obj, collection):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def mesh_obj(name, bm, collection, mats=(), smooth_angle=35.0):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    collection.objects.link(obj)
    for m in mats:
        obj.data.materials.append(mat(m))
    if smooth_angle is not None:
        smooth(obj, smooth_angle)
    return obj


def smooth(obj, angle=35.0):
    me = obj.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    try:
        me.set_sharp_from_angle(angle=math.radians(angle))
    except AttributeError:
        pass
    me.update()


def bevel(obj, width=0.012, segments=3, angle=40.0):
    m = obj.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    m.angle_limit = math.radians(angle)
    m.use_clamp_overlap = True
    m.harden_normals = False
    return m


def cylinder(name, collection, r, depth, verts=48, mats=("GUNMETAL",), base=False, ring=None):
    """Cylinder along local Z. base=True puts the origin at the bottom cap."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r, depth=depth)
    if base:
        bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, depth / 2))
    if ring:  # (inner radius) -> make it a tube by insetting caps and pushing
        caps = [f for f in bm.faces if abs(f.normal.z) > 0.9]
        res = bmesh.ops.inset_region(bm, faces=caps, thickness=r - ring, use_even_offset=True)
        bmesh.ops.delete(bm, geom=caps, context="FACES")
        # bridge the two inner loops
        inner = [e for e in bm.edges if e.is_boundary]
        bmesh.ops.bridge_loops(bm, edges=inner)
    obj = mesh_obj(name, bm, collection, mats, smooth_angle=40)
    return obj


def torus(name, collection, R, r, mats=("EMISSIVE",), major=64, minor=12):
    bm = bmesh.new()
    for i in range(major):
        a = 2 * math.pi * i / major
        for j in range(minor):
            b = 2 * math.pi * j / minor
            bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
    bm.verts.ensure_lookup_table()
    for i in range(major):
        for j in range(minor):
            a = i * minor + j
            b = ((i + 1) % major) * minor + j
            c = ((i + 1) % major) * minor + (j + 1) % minor
            d = i * minor + (j + 1) % minor
            bm.faces.new((bm.verts[a], bm.verts[b], bm.verts[c], bm.verts[d]))
    return mesh_obj(name, bm, collection, mats, smooth_angle=80)


def box(name, collection, size, mats=("BLACK_SATIN",), bev=0.006):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    obj = mesh_obj(name, bm, collection, mats, smooth_angle=30)
    if bev:
        bevel(obj, bev, 2)
    return obj


def place(obj, loc, rot=None, axis_to=None):
    """Put obj at loc. axis_to: world vector the object's local Z should point along."""
    obj.location = loc
    if axis_to is not None:
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(Vector(axis_to).normalized())
    elif rot is not None:
        obj.rotation_euler = rot
    return obj


# ---------------------------------------------------------------- sweep modelling
def bezier(ctrl, t):
    p0, p1, p2, p3 = ctrl
    u = 1 - t
    return u ** 3 * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t ** 3 * p3


def bezier_tan(ctrl, t):
    p0, p1, p2, p3 = ctrl
    u = 1 - t
    return (3 * u * u * (p1 - p0) + 6 * u * t * (p2 - p1) + 3 * t * t * (p3 - p2)).normalized()


def sweep(path_fn, tan_fn, t0, t1, width_fn, height_fn, steps=40, prof=28,
          n_off=0.0, b_off=0.0, side=Vector((0, 1, 0)), power=0.38, matrix=Matrix()):
    """Sweep a rounded-rectangle profile along a path in leg-local space.

    Profile axes: B = side (lateral), N = T x B (convex/outer side).
    Returns a bmesh in world space (matrix applied)."""
    bm = bmesh.new()
    rings = []
    for i in range(steps + 1):
        t = t0 + (t1 - t0) * i / steps
        p = path_fn(t)
        T = tan_fn(t)
        B = side.normalized()
        N = T.cross(B).normalized()
        B = N.cross(T).normalized()
        w = width_fn(t) / 2
        h = height_fn(t) / 2
        ring = []
        for j in range(prof):
            a = 2 * math.pi * j / prof
            c, s = math.cos(a), math.sin(a)
            bb = w * math.copysign(abs(c) ** power, c) + b_off
            nn = h * math.copysign(abs(s) ** power, s) + n_off
            ring.append(bm.verts.new(matrix @ (p + B * bb + N * nn)))
        rings.append(ring)
    for i in range(steps):
        for j in range(prof):
            a, b = rings[i][j], rings[i][(j + 1) % prof]
            c, d = rings[i + 1][(j + 1) % prof], rings[i + 1][j]
            bm.faces.new((a, b, c, d))
    f0 = bm.faces.new(list(reversed(rings[0])))
    f1 = bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- materials
CLAY = dict(base=(0.55, 0.55, 0.55), metal=0.0, rough=0.5, coat=0.0, emit=0.0)

PRESETS = {
    "ARMOR_ORANGE": dict(base=(0.85, 0.22, 0.025), metal=0.0, rough=0.30, coat=0.35, coat_rough=0.12),
    "BLACK_SATIN": dict(base=(0.018, 0.018, 0.02), metal=0.0, rough=0.38, coat=0.15),
    "GUNMETAL": dict(base=(0.09, 0.09, 0.095), metal=1.0, rough=0.33),
    "BRUSHED": dict(base=(0.75, 0.74, 0.72), metal=1.0, rough=0.22, aniso=0.6),
    "CHROME": dict(base=(0.9, 0.9, 0.9), metal=1.0, rough=0.08),
    "RUBBER": dict(base=(0.02, 0.02, 0.022), metal=0.0, rough=0.75),
    "GLASS": dict(base=(0.02, 0.02, 0.025), metal=0.0, rough=0.02, coat=1.0, coat_rough=0.0),
    "EMISSIVE": dict(base=(1.0, 0.35, 0.05), metal=0.0, rough=0.3, emit=9.0, emit_col=(1.0, 0.38, 0.06)),
    "LENS_CORE": dict(base=(1.0, 0.6, 0.15), metal=0.0, rough=0.1, emit=18.0, emit_col=(1.0, 0.62, 0.18)),
}


def mat(name):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        apply_preset(m, CLAY)
    return m


def bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def _set(node, key, value):
    if key in node.inputs:
        node.inputs[key].default_value = value


def apply_preset(m, p):
    n = bsdf(m)
    col = p.get("base", (0.5, 0.5, 0.5))
    _set(n, "Base Color", (*col, 1.0))
    _set(n, "Metallic", p.get("metal", 0.0))
    _set(n, "Roughness", p.get("rough", 0.5))
    _set(n, "Coat Weight", p.get("coat", 0.0))
    _set(n, "Coat Roughness", p.get("coat_rough", 0.1))
    _set(n, "Anisotropic", p.get("aniso", 0.0))
    _set(n, "Emission Color", (*p.get("emit_col", col), 1.0))
    _set(n, "Emission Strength", p.get("emit", 0.0))
    m.diffuse_color = (*col, 1.0)
    m.metallic = p.get("metal", 0.0)
    m.roughness = p.get("rough", 0.5)


def reveal(name):
    apply_preset(mat(name), PRESETS[name])


# ---------------------------------------------------------------- viewport choreography
def view3d():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                return area, area.spaces.active.region_3d
    return None, None


def _current():
    _, r3d = view3d()
    e = r3d.view_rotation.to_euler()
    return dict(elev=90 - math.degrees(e.x), azim=math.degrees(e.z),
                dist=r3d.view_distance, target=r3d.view_location.copy())


def _apply(st):
    area, r3d = view3d()
    r3d.view_perspective = "PERSP"
    r3d.view_rotation = Euler((math.radians(90 - st["elev"]), 0, math.radians(st["azim"]))).to_quaternion()
    r3d.view_distance = st["dist"]
    r3d.view_location = st["target"]
    area.tag_redraw()


def shots(seq):
    """Queue smooth viewport moves: [(elev, azim, dist, (x,y,z), seconds, hold), ...].
    Angles are interpolated directly, so moves arc around the target like an orbit."""
    q = NS.setdefault("hs_shots", [])
    q.extend(seq)
    if not NS.get("hs_timer"):
        NS["hs_timer"] = True
        NS["hs_move"] = None
        bpy.app.timers.register(_tick, first_interval=0.02)


def _tick():
    q = NS.get("hs_shots", [])
    mv = NS.get("hs_move")
    now = __import__("time").time()
    if mv is None:
        if not q:
            NS["hs_timer"] = False
            return None
        elev, azim, dist, tgt, dur, hold = q.pop(0)
        start = _current()
        # take the short way round
        da = (azim - start["azim"] + 180) % 360 - 180
        mv = dict(start=start, end=dict(elev=elev, azim=start["azim"] + da, dist=dist, target=Vector(tgt)),
                  t0=now, dur=max(dur, 0.01), hold=hold)
        NS["hs_move"] = mv
    u = min((now - mv["t0"]) / mv["dur"], 1.0)
    k = u * u * (3 - 2 * u)
    s, e = mv["start"], mv["end"]
    _apply(dict(elev=lerp(s["elev"], e["elev"], k), azim=lerp(s["azim"], e["azim"], k),
                dist=lerp(s["dist"], e["dist"], k), target=s["target"].lerp(e["target"], k)))
    if now - mv["t0"] >= mv["dur"] + mv["hold"]:
        NS["hs_move"] = None
    return 1 / 60


def shots_busy():
    return bool(NS.get("hs_timer"))


# ---------------------------------------------------------------- build-log HUD
def hud_label(text):
    """Project code shown in the HUD header, e.g. 'ARACH-07'."""
    NS["hs_label"] = text


def hud_clear():
    NS["hs_hud"] = None


def hud(step, title, sub="", pct=None):
    NS["hs_hud"] = (step, title, sub, pct)
    if not NS.get("hs_hud_handle"):
        NS["hs_hud_handle"] = bpy.types.SpaceView3D.draw_handler_add(_draw_hud, (), "WINDOW", "POST_PIXEL")
    a, _ = view3d()
    if a:
        a.tag_redraw()


def _draw_hud():
    data = bpy.app.driver_namespace.get("hs_hud")
    if not data:
        return
    step, title, sub, pct = data
    import gpu
    from gpu_extras.batch import batch_for_shader
    x, y = 40, 46
    fid = 0
    blf.size(fid, 13)
    blf.color(fid, 0.95, 0.45, 0.12, 0.95)
    blf.position(fid, x, y + 58, 0)
    blf.draw(fid, bpy.app.driver_namespace.get("hs_label", "BUILD") + "  /  BUILD LOG" + (f"  /  {pct}%" if pct is not None else ""))
    blf.size(fid, 30)
    blf.color(fid, 0.92, 0.92, 0.92, 1.0)
    blf.position(fid, x, y + 18, 0)
    blf.draw(fid, f"{step:02d}   {title.upper()}")
    blf.size(fid, 13)
    blf.color(fid, 0.7, 0.7, 0.7, 0.9)
    blf.position(fid, x + 380, y - 6, 0)
    blf.draw(fid, sub)
    sh = gpu.shader.from_builtin("UNIFORM_COLOR")
    w = 360 * ((pct or 0) / 100.0)
    for (x0, x1, col) in ((x - 14, x - 11, (0.95, 0.45, 0.12, 0.9)),):
        b = batch_for_shader(sh, "TRIS", {"pos": [(x0, y - 8), (x1, y - 8), (x1, y + 78), (x0, y - 8), (x1, y + 78), (x0, y + 78)]})
        sh.uniform_float("color", col)
        b.draw(sh)
    for (w0, col) in ((360, (0.4, 0.4, 0.4, 0.6)), (w, (0.95, 0.45, 0.12, 0.95))):
        b = batch_for_shader(sh, "TRIS", {"pos": [(x, y), (x + w0, y), (x + w0, y + 2), (x, y), (x + w0, y + 2), (x, y + 2)]})
        sh.uniform_float("color", col)
        b.draw(sh)


# ---------------------------------------------------------------- limbs
def _f(v):
    return v if callable(v) else (lambda t, v=v: v)


def sweep2(path_fn, tan_fn, t0, t1, width_fn, height_fn, n_off=0.0, b_off=0.0, **kw):
    """sweep() with per-t offsets."""
    n_off, b_off = _f(n_off), _f(b_off)
    steps = kw.pop("steps", 40)
    prof = kw.pop("prof", 28)
    power = kw.pop("power", 0.38)
    matrix = kw.pop("matrix", Matrix())
    side = Vector((0, 1, 0))
    bm = bmesh.new()
    rings = []
    for i in range(steps + 1):
        t = t0 + (t1 - t0) * i / steps
        p = path_fn(t)
        T = tan_fn(t)
        N = T.cross(side).normalized()
        B = N.cross(T).normalized()
        w, h = width_fn(t) / 2, height_fn(t) / 2
        ring = []
        for j in range(prof):
            a = 2 * math.pi * j / prof
            c, s = math.cos(a), math.sin(a)
            bb = w * math.copysign(abs(c) ** power, c) + b_off(t)
            nn = h * math.copysign(abs(s) ** power, s) + n_off(t)
            ring.append(bm.verts.new(matrix @ (p + B * bb + N * nn)))
        rings.append(ring)
    for i in range(steps):
        for j in range(prof):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % prof], rings[i + 1][(j + 1) % prof], rings[i + 1][j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def tag(obj, role, limb):
    obj["rig"] = role
    obj["limb"] = limb
    return obj


def build_limb(nm, M, ctrl, knee, s, collection, manip=False):
    """Hard-surface limb in limb-local space (origin = shoulder pivot, +X outward, Z up)."""
    R3 = M.to_3x3()
    P = lambda t: bezier(ctrl, t)
    T = lambda t: bezier_tan(ctrl, t)
    N = lambda t: T(t).cross(Vector((0, 1, 0))).normalized()
    W = lambda t: s * (0.20 + 0.30 * math.sin(math.pi * (0.2 + 0.8 * t)) ** 0.7)
    Hh = lambda t: s * (0.16 + 0.40 * math.sin(math.pi * (0.15 + 0.85 * t)) ** 0.8)
    out = []

    def add(o, role):
        out.append(tag(o, role, nm))
        return o

    def put(o, p, axis, role):
        place(o, M @ p, axis_to=R3 @ axis)
        return add(o, role)

    X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
    # shoulder
    put(cylinder(f"{nm}_Shoulder", collection, 0.20 * s, 0.24 * s, 48, ("BLACK_SATIN",)), Vector((0.0, 0, 0)), X, "shoulder")
    put(cylinder(f"{nm}_ShoulderRing", collection, 0.23 * s, 0.06 * s, 48, ("BRUSHED",), ring=0.17 * s), Vector((0.08 * s, 0, 0)), X, "shoulder")
    # femur: dark structural arm + orange cap
    line = [Vector((0, 0, 0)), knee * 0.33, knee * 0.66, knee]
    FP = lambda t: bezier(line, t)
    FT = lambda t: bezier_tan(line, t)
    o = mesh_obj(f"{nm}_Femur", sweep2(FP, FT, 0.05, 0.95, lambda t: 0.24 * s, lambda t: 0.20 * s, matrix=M, steps=8),
                 collection, ["GUNMETAL"], smooth_angle=40)
    bevel(o, 0.01 * s, 2); add(o, "femur")
    o = mesh_obj(f"{nm}_FemurArmor", sweep2(FP, FT, 0.18, 0.85, lambda t: 0.28 * s, lambda t: 0.07 * s, n_off=0.12 * s, matrix=M, steps=8),
                 collection, ["ARMOR_ORANGE"], smooth_angle=40)
    bevel(o, 0.008 * s, 2); add(o, "femur")
    # knee joint with emissive rings
    put(cylinder(f"{nm}_Knee", collection, 0.19 * s, 0.50 * s, 64, ("GUNMETAL",)), knee, Y, "femur")
    for sd in (1, -1):
        put(cylinder(f"{nm}_KneeBezel{'P' if sd > 0 else 'N'}", collection, 0.17 * s, 0.05 * s, 64, ("BLACK_SATIN",), ring=0.10 * s),
            knee + Y * sd * 0.25 * s, Y, "femur")
        put(torus(f"{nm}_KneeGlow{'P' if sd > 0 else 'N'}", collection, 0.125 * s, 0.014 * s), knee + Y * sd * 0.276 * s, Y, "femur")
        put(cylinder(f"{nm}_KneeCap{'P' if sd > 0 else 'N'}", collection, 0.075 * s, 0.07 * s, 32, ("BRUSHED",)), knee + Y * sd * 0.26 * s, Y, "femur")
    # tibia armour shell in three plates + contact foot
    segs = [(0.03, 0.35), (0.36, 0.69), (0.70, 0.925)]
    for i, (a, b) in enumerate(segs):
        o = mesh_obj(f"{nm}_TibiaPlate{i}", sweep2(P, T, a, b, W, Hh, matrix=M, steps=24), collection, ["ARMOR_ORANGE"], smooth_angle=40)
        bevel(o, 0.012 * s, 3); add(o, "tibia")
        # black side inserts on both flanks
        for sd in (1, -1):
            o = mesh_obj(f"{nm}_TibiaInsert{i}{'P' if sd > 0 else 'N'}",
                         sweep2(P, T, a + 0.04, b - 0.04, lambda t: 0.014 * s, lambda t: Hh(t) * 0.55,
                                b_off=lambda t, sd=sd: sd * (W(t) / 2 + 0.002 * s), n_off=lambda t: Hh(t) * 0.05, matrix=M, steps=16),
                         collection, ["BLACK_SATIN"], smooth_angle=40)
            add(o, "tibia")
    o = mesh_obj(f"{nm}_Foot", sweep2(P, T, 0.928, 1.0, lambda t: W(t) * 1.12, lambda t: Hh(t) * 1.12, matrix=M, steps=8),
                 collection, ["RUBBER"], smooth_angle=40)
    bevel(o, 0.01 * s, 2); add(o, "tibia")
    # inner structural spine on the concave side
    o = mesh_obj(f"{nm}_Spine", sweep2(P, T, 0.06, 0.86, lambda t: W(t) * 0.5, lambda t: 0.12 * s,
                                       n_off=lambda t: -Hh(t) * 0.5, matrix=M, steps=30),
                 collection, ["BLACK_SATIN"], smooth_angle=40)
    bevel(o, 0.008 * s, 2); add(o, "tibia")
    # emissive accent near the tip, top clip near the knee
    o = mesh_obj(f"{nm}_TipGlow", sweep2(P, T, 0.86, 0.905, lambda t: 0.035 * s, lambda t: 0.012 * s,
                                         n_off=lambda t: Hh(t) / 2, matrix=M, steps=6), collection, ["EMISSIVE"], smooth_angle=40)
    add(o, "tibia")
    o = mesh_obj(f"{nm}_TopClip", sweep2(P, T, 0.12, 0.2, lambda t: W(t) * 0.7, lambda t: 0.06 * s,
                                         n_off=lambda t: Hh(t) / 2 + 0.02 * s, matrix=M, steps=6), collection, ["BLACK_SATIN"], smooth_angle=40)
    bevel(o, 0.006 * s, 2); add(o, "tibia")
    # piston: housing on the femur, rod on the tibia
    A = knee * 0.3 + Vector((0, 0, -0.13 * s))
    Bp = P(0.30) - N(0.30) * (Hh(0.30) * 0.5 + 0.08 * s)
    d = (Bp - A)
    L_ = d.length
    h = cylinder(f"{nm}_PistonHousing", collection, 0.055 * s, L_ * 0.6, 32, ("BRUSHED",), base=True)
    put(h, A, d.normalized(), "piston_h")
    r = cylinder(f"{nm}_PistonRod", collection, 0.028 * s, L_ * 0.62, 24, ("CHROME",), base=True)
    put(r, Bp, -d.normalized(), "piston_r")
    put(cylinder(f"{nm}_PistonEyeA", collection, 0.05 * s, 0.12 * s, 24, ("BLACK_SATIN",)), A, Y, "femur")
    put(cylinder(f"{nm}_PistonEyeB", collection, 0.05 * s, 0.12 * s, 24, ("BLACK_SATIN",)), Bp, Y, "tibia")
    h["track"] = f"{nm}_PistonEyeB"
    r["track"] = f"{nm}_PistonEyeA"
    if manip:  # dexterous claw: two counter-curved fingers at the tip
        tip = P(1.0)
        for sd in (1, -1):
            cl = [tip + Vector((-0.02, 0, 0.05)) * s, tip + Vector((0.12 * sd, 0, -0.08)) * s,
                  tip + Vector((0.10 * sd, 0, -0.22)) * s, tip + Vector((0.0, 0, -0.30)) * s]
            cl = [tip + (c - tip) for c in cl]
            o = mesh_obj(f"{nm}_Claw{'P' if sd > 0 else 'N'}",
                         sweep2(lambda t, c=cl: bezier(c, t), lambda t, c=cl: bezier_tan(c, t), 0, 1,
                                lambda t: s * lerp(0.08, 0.03, t), lambda t: s * lerp(0.07, 0.025, t), matrix=M, steps=14),
                         collection, ["GUNMETAL"], smooth_angle=40)
            add(o, "claw")
    return out
