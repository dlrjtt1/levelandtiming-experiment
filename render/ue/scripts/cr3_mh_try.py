import unreal, sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
log = Log("mh_try")
try:
    S = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    for m in ("try_add_object_to_edit", "can_build_meta_human", "build_meta_human", "request_auto_rigging", "request_texture_sources",
              "spawn_meta_human_actor", "assemble_for_preview", "remove_object_to_edit", "is_object_added_for_editing", "commit_posed_state_as_a_pose"):
        log("DOC", m, ":", (getattr(S, m).__doc__ or "").replace("\n", " | "))
    for cn in ("MetaHumanCharacterEditorBuildParameters", "MetaHumanCharacterAutoRiggingRequestParams", "MetaHumanCharacterTextureRequestParams", "MetaHumanRigType", "MetaHumanQualityLevel"):
        log("DOC", cn, ":", (getattr(unreal, cn).__doc__ or "").replace("\n", " | "), [x for x in dir(getattr(unreal, cn)) if x.isupper()])
    EAL = unreal.EditorAssetLibrary
    src = "/MetaHumanCharacter/Optional/Presets/" + (sys.argv[1] if len(sys.argv) > 1 else "Ada")
    name = sys.argv[2] if len(sys.argv) > 2 else "Singer"
    dst = f"/Game/MetaHumans/{name}/MHC_{name}"
    ch = EAL.load_asset(dst) if EAL.does_asset_exist(dst) else EAL.duplicate_asset(src, dst)
    log("character", ch, "props:", {p: str(ch.get_editor_property(p))[:80] for p in ("has_high_resolution_textures", "fixed_body_type", "preview_material_type")})
    ok = S.try_add_object_to_edit(ch); log("add to edit:", ok)
    try: log("can build:", S.can_build_meta_human(ch))
    except Exception as e: log("can_build err", e)
except Exception:
    log(traceback.format_exc())
