# Re-import the hall photo textures (T_CR3_hall_0..7, T_CR3_stagefloor) over the existing assets, after bake_hall.py was run again
# (e.g. with the levelled photo). The meshes and UVs do not change.
import unreal, os
HERE = os.path.dirname(os.path.abspath(__file__)); EAL = unreal.EditorAssetLibrary
ar = unreal.AssetRegistryHelpers.get_asset_registry(); tools = unreal.AssetToolsHelpers.get_asset_tools()
have = {str(a.asset_name): str(a.package_path) for a in ar.get_assets_by_path("/Game", recursive=True) if str(a.asset_class_path.asset_name) == "Texture2D"}
tasks = []
for name in [f"T_CR3_hall_{i}" for i in range(8)] + ["T_CR3_stagefloor"]:
    if name not in have: print("not in project:", name); continue
    t = unreal.AssetImportTask(); t.set_editor_property("filename", os.path.join(HERE, name + ".png")); t.set_editor_property("destination_path", have[name])
    t.set_editor_property("destination_name", name); t.set_editor_property("replace_existing", True); t.set_editor_property("replace_existing_settings", False)
    t.set_editor_property("automated", True); t.set_editor_property("save", True); tasks.append(t)
tools.import_asset_tasks(tasks)
for t in tasks: print(os.path.basename(t.get_editor_property("filename")), "->", [str(p) for p in t.get_editor_property("imported_object_paths")])
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
