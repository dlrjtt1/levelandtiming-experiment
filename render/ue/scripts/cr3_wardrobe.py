# sh run.sh <id> cr3_wardrobe.py <Name> <Slot> <wardrobe item path> [more Slot path pairs]  -> select items in the MetaHuman's collection and rebuild (~2-4 min)
# e.g. cr3_wardrobe.py Singer Hair /MetaHumanCharacter/Optional/Grooms/Bindings/Hair/WI_Hair_S_UpdoBuns
import unreal, sys, os, time, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
name = sys.argv[1]; pairs = list(zip(sys.argv[2::2], sys.argv[3::2]))
log = Log("wardrobe_" + name)
try:
    S = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem); EAL = unreal.EditorAssetLibrary; t0 = time.time()
    ch = EAL.load_asset(f"/Game/MetaHumans/{name}/MHC_{name}")
    if not S.is_object_added_for_editing(ch): log("add:", S.try_add_object_to_edit(ch))
    col = ch.get_editor_property("internal_collection"); inst = col.get_editor_property("default_instance")
    for slot, wi_path in pairs:
        wi = EAL.load_asset(wi_path); log("wardrobe item", wi_path, type(wi).__name__ if wi else None)
        r = col.try_add_item_from_wardrobe_item(slot, wi); log("added:", r)
        key = r[1] if isinstance(r, tuple) else r
        if isinstance(r, tuple) and not r[0]:
            keys = [k for k in col.get_item_keys_for_wardrobe_item(wi)] if hasattr(col, "get_item_keys_for_wardrobe_item") else []
            key = keys[0] if keys else None; log("existing key used:", key is not None)
        log("select:", inst.set_single_slot_selection(slot, key))
    ch.modify(); EAL.save_loaded_asset(ch)
    b = unreal.MetaHumanCharacterEditorBuildParameters()
    b.set_editor_property("pipeline_type", unreal.MetaHumanDefaultPipelineType.CINEMATIC)
    b.set_editor_property("pipeline_quality", unreal.MetaHumanQualityLevel.HIGH)
    S.build_meta_human(ch, b); EAL.save_loaded_asset(ch)
    S.remove_object_to_edit(ch)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    log("rebuilt", name, round(time.time() - t0), "s")
except Exception:
    log(traceback.format_exc())
