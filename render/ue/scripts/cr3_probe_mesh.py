import unreal
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
for a in ea.get_all_level_actors():
    if isinstance(a, unreal.StaticMeshActor):
        sm = a.static_mesh_component.static_mesh
        if not sm: continue
        ns = sm.get_editor_property("nanite_settings")
        print(a.get_actor_label(), sm.get_path_name(), "nanite", ns.enabled, "lods", sm.get_num_lods(), "tris", [sm.get_num_triangles(i) for i in range(sm.get_num_lods())],
              "hidden", a.is_temporarily_hidden_in_editor(), [m.get_name() if m else None for m in a.static_mesh_component.get_materials()][:6])
