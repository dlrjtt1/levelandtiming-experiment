# Replace the instrument meshes with CR3_instruments_v2.fbx (real-proportion violin family with wood textures).
import unreal, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
log = Log("reimport_instruments")
HERE = os.path.dirname(os.path.abspath(__file__))
t = unreal.AssetImportTask()
t.set_editor_property("filename", os.path.join(HERE, "CR3_instruments_v2.fbx")); t.set_editor_property("destination_path", "/Game")
t.set_editor_property("replace_existing", True); t.set_editor_property("automated", True); t.set_editor_property("save", True)
o = unreal.FbxImportUI()
o.set_editor_property("import_mesh", True); o.set_editor_property("import_as_skeletal", False); o.set_editor_property("import_materials", True)
o.set_editor_property("import_textures", True); o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
o.static_mesh_import_data.set_editor_property("combine_meshes", False)
t.set_editor_property("options", o)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
paths = [str(p) for p in t.get_editor_property("imported_object_paths")]; log("imported", paths)
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
names = ("ViolinI", "ViolinII", "Viola", "Cello", "Contrabass", "Bows", "Flute", "Clarinet", "Bassoon", "Horns")
for a in ea.get_all_level_actors():
    lab = a.get_actor_label()
    if isinstance(a, unreal.StaticMeshActor) and lab.startswith(names) and not lab.startswith("MARK_"):
        a.set_actor_scale3d(unreal.Vector(1, 1, 1)); a.set_actor_location(unreal.Vector(0, 0, 0), False, False); a.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
        sm = a.static_mesh_component.static_mesh; log(lab, sm.get_name() if sm else None, a.get_actor_bounds(False))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True); log("done")
