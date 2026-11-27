# sh run.sh <id> cr3_mh_make.py <Name> <Preset> [quality]   -> one MetaHuman, start to finish (blocks the editor ~5 min)
# copy preset -> /Game/MetaHumans/<Name>/MHC_<Name>, auto-rig (joints + blend shapes), high-res textures, assemble.
import unreal, sys, os, time, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
name, preset = sys.argv[1], sys.argv[2]; quality = sys.argv[3] if len(sys.argv) > 3 else "HIGH"
log = Log("make_" + name)
try:
    S = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem); EAL = unreal.EditorAssetLibrary
    ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    dst = f"/Game/MetaHumans/{name}/MHC_{name}"; t0 = time.time()
    if "--replace" in sys.argv and EAL.does_directory_exist(f"/Game/MetaHumans/{name}"):
        for a in ea.get_all_level_actors():
            if a.get_actor_label() == name: ea.destroy_actor(a)
        if EAL.does_asset_exist(dst):
            old = EAL.load_asset(dst)
            if S.is_object_added_for_editing(old): S.remove_object_to_edit(old)
        log("delete old:", EAL.delete_directory(f"/Game/MetaHumans/{name}"))
    ch = EAL.load_asset(dst) if EAL.does_asset_exist(dst) else EAL.duplicate_asset("/MetaHumanCharacter/Optional/Presets/" + preset, dst)
    log("character", ch.get_path_name(), "from", preset)
    if not S.is_object_added_for_editing(ch): log("add:", S.try_add_object_to_edit(ch))
    p = unreal.MetaHumanCharacterAutoRiggingRequestParams(); p.set_editor_property("rig_type", unreal.MetaHumanRigType.JOINTS_AND_BLEND_SHAPES)
    p.set_editor_property("blocking", True); p.set_editor_property("report_progress", False)
    S.request_auto_rigging(ch, p); log("rig done", round(time.time() - t0), "s")
    if not ch.get_editor_property("has_high_resolution_textures"):
        q = unreal.MetaHumanCharacterTextureRequestParams(); q.set_editor_property("blocking", True); q.set_editor_property("report_progress", False)
        S.request_texture_sources(ch, q)
    log("textures", ch.get_editor_property("has_high_resolution_textures"), round(time.time() - t0), "s")
    ok = S.can_build_meta_human(ch, True); log("can build:", ok)
    if ok:
        b = unreal.MetaHumanCharacterEditorBuildParameters()
        b.set_editor_property("pipeline_type", unreal.MetaHumanDefaultPipelineType.CINEMATIC)
        b.set_editor_property("pipeline_quality", getattr(unreal.MetaHumanQualityLevel, quality))
        S.build_meta_human(ch, b); EAL.save_loaded_asset(ch)
        log("built:", [a for a in EAL.list_assets(f"/Game/MetaHumans/{name}", recursive=True, include_folder=False) if "/BP_" in a], round(time.time() - t0), "s")
    S.remove_object_to_edit(ch)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True); log("DONE", name)
except Exception:
    log(traceback.format_exc())
