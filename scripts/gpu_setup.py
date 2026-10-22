"""Background-render helper: enable the best Cycles GPU backend, optional overrides.

usage: blender -b file.blend --python gpu_setup.py [-o ...] -f N -- [percent] [samples]
"""
import sys
import bpy

def enable_gpu():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            prefs.refresh_devices()
            if any(d.type != "CPU" for d in prefs.devices):
                break
        except TypeError:
            continue
    for d in prefs.devices:
        d.use = True
    scene = bpy.context.scene
    scene.cycles.device = "GPU" if any(d.type != "CPU" for d in prefs.devices) else "CPU"
    return prefs, scene


if __name__ == "__main__":  # run via --python; imported by render_final.py
    prefs, scene = enable_gpu()
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) >= 1:
        scene.render.resolution_percentage = int(argv[0])
    if len(argv) >= 2:
        scene.cycles.samples = int(argv[1])
    print("render devices:", [d.name for d in prefs.devices if d.use], scene.cycles.device)
