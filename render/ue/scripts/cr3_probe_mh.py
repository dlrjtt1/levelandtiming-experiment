import unreal, sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
log = Log("probe_mh")
try:
    names = [n for n in dir(unreal) if "MetaHuman" in n]
    log("MH classes:", len(names)); [log("  ", n) for n in names]
    try:
        enabled = unreal.PluginBlueprintLibrary.get_enabled_plugin_names()
        log("MH plugins enabled:", [p for p in enabled if "MetaHuman" in p])
    except Exception as e: log("plugin list failed", e)
    EAL = unreal.EditorAssetLibrary
    for root in ("/MetaHumanCharacter", "/MetaHumanCoreTechLib", "/MetaHumanSDK", "/Game/MetaHumans"):
        try:
            a = EAL.list_assets(root, recursive=False, include_folder=True); log(root, len(a), a[:10])
        except Exception as e: log(root, "ERR", e)
except Exception:
    log(traceback.format_exc())
