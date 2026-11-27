# Import CR3_shellfix.fbx + T_CR3_shell.png (render/shell_fix.py) and place them as actor CR3_ShellFix: shell towers, rear wall, house
# curtains and proscenium jambs with their own part of the hall photo, and black masking on the stage-house walls behind them.
# Also turns Nanite off for the audience chairs (on this Mac the simplified fallback mesh was drawn: torn chair corners).
import unreal, os
HERE = os.path.dirname(os.path.abspath(__file__)); EAL, MEL = unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools(); DEST = "/Game/ShellFix"

def imp(filename, options=None):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", os.path.join(HERE, filename)); t.set_editor_property("destination_path", DEST)
    t.set_editor_property("replace_existing", True); t.set_editor_property("automated", True); t.set_editor_property("save", True)
    if options: t.set_editor_property("options", options)
    tools.import_asset_tasks([t]); return [EAL.load_asset(str(p)) for p in t.get_editor_property("imported_object_paths")]

tex = [a for a in imp("T_CR3_shell.png") if isinstance(a, unreal.Texture2D)][0]
tex.set_editor_property("srgb", True); tex.set_editor_property("never_stream", True)
tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP); EAL.save_loaded_asset(tex)
o = unreal.FbxImportUI()
o.set_editor_property("import_mesh", True); o.set_editor_property("import_as_skeletal", False); o.set_editor_property("import_materials", False)
o.set_editor_property("import_textures", False); o.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
o.static_mesh_import_data.set_editor_property("combine_meshes", True)
sm = [a for a in imp("CR3_shellfix.fbx", o) if isinstance(a, unreal.StaticMesh)][0]

master = EAL.load_asset("/Game/CR3/Materials/M_HallPhoto"); ref = EAL.load_asset("/Game/CR3/Materials/MI_HallPhoto_0")
path = DEST + "/MI_ShellPhoto"
mi = EAL.load_asset(path) if EAL.does_asset_exist(path) else tools.create_asset("MI_ShellPhoto", DEST, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
MEL.set_material_instance_parent(mi, master); MEL.set_material_instance_texture_parameter_value(mi, "Photo", tex)
gain = MEL.get_material_instance_scalar_parameter_value(ref, "Gain"); MEL.set_material_instance_scalar_parameter_value(mi, "Gain", gain)
MEL.update_material_instance(mi); EAL.save_loaded_asset(mi)
print("gain", gain, "two sided", master.get_editor_property("two_sided"))

sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
def nanite_off(mesh):
    ns = mesh.get_editor_property("nanite_settings")
    if ns.enabled:
        ns.enabled = False; sub.set_nanite_settings(mesh, ns, True); EAL.save_loaded_asset(mesh)
    print(mesh.get_name(), "nanite", mesh.get_editor_property("nanite_settings").enabled, "tris", mesh.get_num_triangles(0))
nanite_off(sm)
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in ea.get_all_level_actors():
    if a.get_actor_label() == "CR3_ShellFix": ea.destroy_actor(a)
    elif a.get_actor_label() == "AudienceChairs": nanite_off(a.static_mesh_component.static_mesh)
a = ea.spawn_actor_from_object(sm, unreal.Vector(0, 0, 0)); a.set_actor_label("CR3_ShellFix"); a.set_actor_scale3d(unreal.Vector(1, 1, 1))
c = a.static_mesh_component
for i in range(c.get_num_materials()): c.set_material(i, mi)
c.set_editor_property("cast_shadow", False)
print("bounds", a.get_actor_bounds(False))
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
