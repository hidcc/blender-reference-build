# Connecting MCP for Blender

The MCP server (`uvx mcp-for-blender`, registered in Claude Code) talks to an add-on inside Blender over a TCP socket. The default port is **9876**. The tools fail with "Could not connect to Blender" whenever nothing inside Blender is listening on that port.

## Diagnose in this order

```bash
lsof -nP -iTCP:9876 -sTCP:LISTEN          # is Blender listening?
ps aux | grep -i "[B]lender.app"          # is Blender running at all, and only once?
claude mcp get blender                    # is the MCP server side connected?
ls ~/Library/Application\ Support/Blender/*/scripts/addons/   # where the add-on file lives (macOS)
```

- Nothing is listening and the N-panel has **no "MCP for Blender" tab**: the add-on is not registered in this Blender. See below.
- The tab is there but shows "Not connected": click **Connect to MCP server**. Auto-start is on by default, so this mostly happens after the user pressed Disconnect.
- Something is listening but the MCP tools still fail: check that the port in the N-panel matches what the server uses.

## The stale-module trap

The saved user preferences can list an add-on module that no longer exists (for example `blender_mcp_addon`, from an older install) and not list the real one (`blender_mcp`). Ticking the checkbox in the UI may then appear to work but not persist, so the tab never shows up.

1. Confirm that the add-on itself loads, in a throwaway headless Blender:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender -b -noaudio --python check.py
   ```
   where `check.py` runs `addon_utils.enable("blender_mcp", default_set=False)` and prints `[a.module for a in bpy.context.preferences.addons]`. The "Add-on not loaded: ... No module named ..." line shows the stale name.
2. Fix the preferences headlessly with `scripts/fix_addon_prefs.py`. Back up `config/userpref.blend` first. The script disables the stale name, enables `blender_mcp` and saves the user prefs.
3. Restart the user's Blender. Only do this when the open scene has nothing worth saving (an untitled default scene); otherwise ask. `osascript -e 'tell application "Blender" to quit'` gets cancelled by the unsaved-changes dialog, so with a disposable scene end the process instead. Then `open -a Blender` and wait until port 9876 is listening.

## Driving Blender's UI with computer use

- Blender draws its own UI, so background `app_click` sometimes works and sometimes silently doesn't. Popup menus are not captured by background screenshots. For menus and preferences, call `request_full_control`, `open_application("Blender")` to bring it to the front, then use `computer_batch`.
- Floating overlay windows from other apps (dictation tools, chat launchers) can sit over Blender. A click that "would land on <other app>" is refused. Either click a different spot on the same control or switch back to `app_*` background clicks on the Preferences window, which worked for checkboxes.
- After an `open_application`, check with a screenshot which app is frontmost before clicking. Focus can jump back to the Claude window.
- Escalating permission modes can make the auto-mode classifier refuse the next UI clicks as "self-modification". If that happens, stop and ask the user to click the one control themselves; don't work around it.

## Splash and dialogs

At startup there may be add-on update dialogs (e.g. BlenderKit). Cancel them, then click empty viewport space to dismiss the splash.
