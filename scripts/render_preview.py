"""Fast EEVEE preview MP4 of the scene's frame range. The .blend on disk is not modified.

usage: blender -b file.blend --python render_preview.py -- [out_path] [percent]
"""
import sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
scene = bpy.context.scene
r = scene.render
for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        r.engine = engine
        break
    except TypeError:
        pass
ev = scene.eevee
for key, value in (("taa_render_samples", 64), ("use_raytracing", True), ("use_shadows", True), ("use_gtao", True)):
    if hasattr(ev, key):
        setattr(ev, key, value)
r.use_motion_blur = True
if len(argv) >= 2:
    r.resolution_percentage = int(argv[1])
try:
    r.image_settings.media_type = "VIDEO"  # Blender 5.x
except (AttributeError, TypeError):
    pass
r.image_settings.file_format = "FFMPEG"
r.ffmpeg.format = "MPEG4"
r.ffmpeg.codec = "H264"
r.ffmpeg.constant_rate_factor = "HIGH"
r.filepath = argv[0] if argv else "//renders/preview.mp4"
bpy.ops.render.render(animation=True)
