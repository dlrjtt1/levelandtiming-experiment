import unreal, sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
log = Log("probe_mh2")
try:
    for cn in ("MetaHumanCharacterEditorSubsystem", "MetaHumanCharacter", "MetaHumanCharacterFactoryNew", "MetaHumanCharacterEditorBuildParameters",
               "MetaHumanCharacterAssemblySettings", "MetaHumanCharacterTemplateType", "MetaHumanDefaultPipelineType", "MetaHumanCharacterInstanceBlueprintLibrary",
               "MetaHumanCollectionBlueprintLibrary", "MetaHumanCharacterExportBlueprintLibrary", "MetaHumanCharacterPalette", "MetaHumanCharacterAssemblyResult",
               "MetaHumanCharacterBodyConstraint", "MetaHumanCharacterTextureRequestParams", "MetaHumanCharacterAutoRiggingRequestParams", "MetaHumanCharacterRenderingQuality"):
        c = getattr(unreal, cn, None)
        if c is None: log(cn, "MISSING"); continue
        log("==", cn, ":", [m for m in dir(c) if not m.startswith("_") and m not in dir(unreal.Object)])
    names = [n for n in dir(unreal) if "MetaHuman" in n]
    log("rest:", [n for n in names if n > "MetaHumanGroomPipeline"])
    EAL = unreal.EditorAssetLibrary
    allp = EAL.list_assets("/MetaHumanCharacter", recursive=True, include_folder=False)
    log("assets", len(allp))
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    kinds = {}
    for p in allp:
        d = ar.get_asset_by_object_path(p.split(".")[0] + "." + p.split(".")[-1]) if False else EAL.find_asset_data(p)
        k = str(d.asset_class_path.asset_name); kinds.setdefault(k, []).append(p)
    for k, v in kinds.items(): log(k, len(v), v[:6])
    for k in ("MetaHumanCharacter", "MetaHumanWardrobeItem", "MetaHumanCollection", "AnimSequence", "PoseAsset", "ControlRigBlueprint"):
        for p in kinds.get(k, []): log("  ", k, p)
except Exception:
    log(traceback.format_exc())
