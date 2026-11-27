# Import CR3_instruments_v3.fbx (instruments laid out on the posed MetaHumans, render/instruments_v3.py),
# hide the old instrument actors, spawn one actor per performer (label Inst_<Name>).
import unreal, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
log = Log("instruments_v3"); HERE = os.path.dirname(os.path.abspath(__file__))
t = unreal.AssetImportTask()
t.set_editor_property("filename", os.path.join(HERE, "CR3_instruments_v3.fbx")); t.set_editor_property("destination_path", "/Game/Instruments_v3")
t.set_editor_property("replace_existing", True); t.set_editor_property("automated", True); t.set_editor_property("save", True)
o = unreal.FbxImportUI()
o.set_editor_property("import_mesh", True); o.set_editor_property("import_as_skeletal", False); o.set_editor_property("import_materials", True)
o.set_editor_property("import_textures", True); o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
o.static_mesh_import_data.set_editor_property("combine_meshes", False)
t.set_editor_property("options", o)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
paths = [str(p) for p in t.get_editor_property("imported_object_paths")]; log("imported", paths)
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
old = ("ViolinI", "ViolinII", "Viola", "Cello", "Contrabass", "Bows", "Flute", "Clarinet", "Bassoon", "Horns")
for a in ea.get_all_level_actors():
    lab = a.get_actor_label()
    if isinstance(a, unreal.StaticMeshActor) and lab.startswith(old) and not lab.startswith(("MARK_", "Inst_")):
        a.set_actor_hidden_in_game(True); a.set_is_temporarily_hidden_in_editor(True); a.tags = [unreal.Name("old_instrument")]; log("hid", lab)
    if lab.startswith("Inst_"): ea.destroy_actor(a)
for p in paths:
    sm = unreal.EditorAssetLibrary.load_asset(p)
    if not isinstance(sm, unreal.StaticMesh): continue
    a = ea.spawn_actor_from_object(sm, unreal.Vector(0, 0, 0)); a.set_actor_label("Inst_" + sm.get_name().replace("I_", "", 1))
    a.set_actor_scale3d(unreal.Vector(1, 1, 1)); a.set_actor_rotation(unreal.Rotator(0, 0, 0), False); a.set_actor_location(unreal.Vector(0, 0, 0), False, False)
    log(a.get_actor_label(), a.get_actor_bounds(False)[0])
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True); log("done")
