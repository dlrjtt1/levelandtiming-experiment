# Replace the audience chair mesh with ue/CR3_audience_chairs_v2.fbx (square backs as in the BRAS photographs)
import unreal, os
FBX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CR3_audience_chairs_v2.fbx")
EAL = unreal.EditorAssetLibrary
paths = [p for p in EAL.list_assets("/Game", recursive=True, include_folder=False) if p.split("/")[-1].split(".")[0] == "AudienceChairs"]
dest = paths[0].rsplit("/", 1)[0] if paths else "/Game"
unreal.log(f"[CR3] chairs asset {paths} -> {dest}")
t = unreal.AssetImportTask()
t.set_editor_property("filename", FBX); t.set_editor_property("destination_path", dest); t.set_editor_property("destination_name", "AudienceChairs")
t.set_editor_property("replace_existing", True); t.set_editor_property("automated", True); t.set_editor_property("save", True)
o = unreal.FbxImportUI()
o.set_editor_property("import_mesh", True); o.set_editor_property("import_as_skeletal", False); o.set_editor_property("import_materials", True)
o.set_editor_property("import_textures", False); o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
o.static_mesh_import_data.set_editor_property("combine_meshes", True)
t.set_editor_property("options", o)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
unreal.log(f"[CR3] reimported chairs: {t.get_editor_property('imported_object_paths')}")
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in ea.get_all_level_actors():   # the new mesh is in centimetres: the actor must not scale it again
    if a.get_actor_label() == "AudienceChairs": a.set_actor_scale3d(unreal.Vector(1, 1, 1)); a.set_actor_location(unreal.Vector(0, 0, 0), False, False)
