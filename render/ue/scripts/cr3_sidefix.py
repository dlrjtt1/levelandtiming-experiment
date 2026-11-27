# Import CR3_sidefix.fbx (render/side_fix.py) and place it as actor CR3_SideFix: covers the smeared photo chairs on the side podiums.
import unreal, os
HERE = os.path.dirname(os.path.abspath(__file__)); EAL = unreal.EditorAssetLibrary
t = unreal.AssetImportTask()
t.set_editor_property("filename", os.path.join(HERE, "CR3_sidefix.fbx")); t.set_editor_property("destination_path", "/Game/SideFix")
t.set_editor_property("replace_existing", True); t.set_editor_property("automated", True); t.set_editor_property("save", True)
o = unreal.FbxImportUI()
o.set_editor_property("import_mesh", True); o.set_editor_property("import_as_skeletal", False); o.set_editor_property("import_materials", True)
o.set_editor_property("import_textures", False); o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
o.static_mesh_import_data.set_editor_property("combine_meshes", True)
t.set_editor_property("options", o)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
paths = [str(p) for p in t.get_editor_property("imported_object_paths")]; print(paths)
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in ea.get_all_level_actors():
    if a.get_actor_label() == "CR3_SideFix": ea.destroy_actor(a)
sm = [EAL.load_asset(p) for p in paths]; sm = [s for s in sm if isinstance(s, unreal.StaticMesh)][0]
a = ea.spawn_actor_from_object(sm, unreal.Vector(0, 0, 0)); a.set_actor_label("CR3_SideFix"); a.set_actor_scale3d(unreal.Vector(1, 1, 1))
# same materials as the audience chairs, so both kinds of chair match
ac = [x for x in ea.get_all_level_actors() if x.get_actor_label() == "AudienceChairs"]
if ac:
    src = {m.get_name(): m for m in ac[0].static_mesh_component.get_materials() if m}; c = a.static_mesh_component
    for i, m in enumerate(c.get_materials()):
        if m and m.get_name() in src: c.set_material(i, src[m.get_name()])
    print("materials", [m.get_name() for m in c.get_materials()], "from", list(src))
print("bounds", a.get_actor_bounds(False))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
