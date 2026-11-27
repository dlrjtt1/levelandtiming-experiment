import unreal, sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
log = Log("mh_rig")
try:
    S = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem); EAL = unreal.EditorAssetLibrary
    name = sys.argv[1]; step = sys.argv[2]
    ch = EAL.load_asset(f"/Game/MetaHumans/{name}/MHC_{name}")
    if not S.is_object_added_for_editing(ch): log("add:", S.try_add_object_to_edit(ch))
    if step == "rig":
        p = unreal.MetaHumanCharacterAutoRiggingRequestParams(); p.set_editor_property("rig_type", unreal.MetaHumanRigType.JOINTS_AND_BLEND_SHAPES)
        p.set_editor_property("blocking", False); p.set_editor_property("report_progress", True)
        S.request_auto_rigging(ch, p); log("rig requested")
    elif step == "tex":
        p = unreal.MetaHumanCharacterTextureRequestParams(); p.set_editor_property("blocking", False); p.set_editor_property("report_progress", True)
        S.request_texture_sources(ch, p); log("textures requested")
    elif step == "check":
        log("can build:", S.can_build_meta_human(ch, True), "hires:", ch.get_editor_property("has_high_resolution_textures"))
    elif step == "build":
        b = unreal.MetaHumanCharacterEditorBuildParameters()
        b.set_editor_property("pipeline_type", unreal.MetaHumanDefaultPipelineType.CINEMATIC)
        b.set_editor_property("pipeline_quality", getattr(unreal.MetaHumanQualityLevel, sys.argv[3] if len(sys.argv) > 3 else "HIGH"))
        log("can build:", S.can_build_meta_human(ch, True))
        S.build_meta_human(ch, b); EAL.save_loaded_asset(ch); log("build called")
        log("assets:", [a for a in EAL.list_assets("/Game/MetaHumans", recursive=True, include_folder=False) if "/BP_" in a])
except Exception:
    log(traceback.format_exc())
