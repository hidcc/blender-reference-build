"""Final Cycles animation as a resumable PNG sequence (rerun the same command to resume).

usage: nohup caffeinate -i blender -b file.blend --python render_final.py -a -- [out_dir] [samples] [percent] &
"""
import os
import sys
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gpu_setup import enable_gpu  # noqa: E402

enable_gpu()

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
scene = bpy.context.scene
r = scene.render
scene.cycles.samples = int(argv[1]) if len(argv) >= 2 else 128
r.resolution_percentage = int(argv[2]) if len(argv) >= 3 else 100
r.use_overwrite = False
r.use_placeholder = True
r.image_settings.file_format = "PNG"
out_dir = argv[0] if argv else "//renders/final"
r.filepath = out_dir.rstrip("/") + "/frame_####"
print("final render ->", r.filepath, scene.frame_start, scene.frame_end, scene.cycles.samples)
