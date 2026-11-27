import unreal
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in ea.get_all_level_actors():
    if "Chair" in a.get_actor_label() or "chair" in a.get_actor_label():
        comp = a.get_component_by_class(unreal.StaticMeshComponent)
        sm = comp.static_mesh if comp else None
        o, e = a.get_actor_bounds(False)
        unreal.log(f"[CR3] {a.get_actor_label()} mesh={sm.get_path_name() if sm else None} hidden={a.is_temporarily_hidden_in_editor()} hiddenGame={a.get_editor_property('hidden')} centre={o} extent={e} slots={[comp.get_material(i).get_name() if comp.get_material(i) else None for i in range(comp.get_num_materials())] if comp else None}")
sm = unreal.EditorAssetLibrary.load_asset("/Game/AudienceChairs")
if sm:
    unreal.log(f"[CR3] asset AudienceChairs lods={sm.get_num_lods()} verts={unreal.EditorStaticMeshLibrary.get_number_verts(sm, 0) if hasattr(unreal,'EditorStaticMeshLibrary') else '?'} bounds={sm.get_bounding_box()}")
