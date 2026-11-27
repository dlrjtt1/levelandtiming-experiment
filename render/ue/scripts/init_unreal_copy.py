# CR3 pilot 2: command watcher. Runs at editor start. Every second it looks for *.py files in the _cmd folder of
# UE_CR3_pilot2, runs each one inside the editor, writes what it printed (and any error) to _log/<name>.out and renames
# the file to <name>.py.done. This lets scripts be run without typing in the editor's console.
import unreal, os, sys, time, traceback, io, contextlib
CR3_DIR = "/Users/user/Library/Mobile Documents/com~apple~CloudDocs/LABO 1557/UE_CR3_pilot2"
CMD, LOGD = os.path.join(CR3_DIR, "_cmd"), os.path.join(CR3_DIR, "_log")
_state = {"t": 0.0, "busy": False}
def _tick(dt):
    if _state["busy"]: return             # a running command may pump the editor loop (blocking requests): never nest
    _state["t"] += dt
    if _state["t"] < 1.0: return
    _state["t"] = 0.0
    try:
        files = sorted(f for f in os.listdir(CMD) if f.endswith(".py"))
    except Exception:
        return
    for f in files[:1]:                       # one per tick
        p = os.path.join(CMD, f); out = io.StringIO(); _state["busy"] = True
        try:
            src = open(p).read(); os.replace(p, p + ".done")
            if CR3_DIR not in sys.path: sys.path.insert(0, CR3_DIR)
            with contextlib.redirect_stdout(out):
                exec(compile(src, p, "exec"), {"__name__": "__main__", "__file__": p})
            out.write("\n[ok]\n")
        except BaseException:
            out.write("\n[error]\n" + traceback.format_exc())
        finally:
            _state["busy"] = False
        try:
            os.makedirs(LOGD, exist_ok=True)
            with open(os.path.join(LOGD, f[:-3] + ".out"), "w") as h: h.write(out.getvalue())
        except Exception: pass
if os.path.isdir(CR3_DIR):
    os.makedirs(CMD, exist_ok=True)
    unreal.register_slate_post_tick_callback(_tick)
    unreal.log("[CR3] command watcher running: " + CMD)

# lighter editor while working (2026-11-25, after out-of-memory crashes); final renders set their own quality
try:
    for _c in ("sg.ViewDistanceQuality 2", "sg.ShadowQuality 2", "sg.GlobalIlluminationQuality 2", "sg.ReflectionQuality 2",
               "sg.PostProcessQuality 2", "sg.TextureQuality 2", "sg.EffectsQuality 2", "r.Streaming.PoolSize 3000"):
        unreal.SystemLibrary.execute_console_command(None, _c)
except Exception as _e:
    unreal.log_warning("CR3 editor settings: %s" % _e)
