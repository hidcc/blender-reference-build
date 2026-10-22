"""Repair saved prefs so the MCP for Blender add-on loads on startup.

Back up config/userpref.blend first, then run headless:
    blender -b -noaudio --python fix_addon_prefs.py -- [module] [stale_module ...]
Defaults: enable "blender_mcp", disable "blender_mcp_addon".
"""
import sys
import addon_utils
import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
module = argv[0] if argv else "blender_mcp"
stale = argv[1:] or ["blender_mcp_addon"]
for name in stale:
    addon_utils.disable(name, default_set=True)
addon_utils.enable(module, default_set=True)
bpy.ops.wm.save_userpref()
print("enabled add-ons:", [a.module for a in bpy.context.preferences.addons])
