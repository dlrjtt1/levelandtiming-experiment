# sh run.sh <id> cr3_lights.py <spot_cd> <stagetop_cd>   -> stage light levels (hall photo is emissive and is not affected)
import unreal, sys
spot, top = float(sys.argv[1]), float(sys.argv[2])
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in ea.get_all_level_actors():
    lab = a.get_actor_label()
    if lab.startswith("CR3_Spot_"): a.get_component_by_class(unreal.SpotLightComponent).set_intensity(spot)
    if lab == "CR3_StageTop": a.get_component_by_class(unreal.RectLightComponent).set_intensity(top)
print("spots", spot, "cd, stage top", top, "cd")
