# sh run.sh <id> cr3_shot.py <name> x y z yaw pitch fov   -> Saved/Screenshots/MacEditor/<name>.png (1920x1080), markers hidden
import unreal, sys
name, x, y, z, yaw, pitch, fov = sys.argv[1], *map(float, sys.argv[2:8])
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
by = {a.get_actor_label(): a for a in ea.get_all_level_actors()}
for n, a in by.items():
    if n.startswith(("MARK_", "AXIS_")): a.set_is_temporarily_hidden_in_editor(True)
cam = by.get("CR3_PreviewCam") or ea.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(0, 0, 0))
cam.set_actor_label("CR3_PreviewCam"); cam.set_actor_location(unreal.Vector(x, y, z), False, False); cam.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=pitch, yaw=yaw), False)
c = cam.camera_component; c.set_editor_property("field_of_view", fov); c.set_editor_property("aspect_ratio", 16 / 9); c.set_editor_property("constrain_aspect_ratio", True)
ea.set_selected_level_actors([])                       # no selection outlines
try: unreal.EditorLevelLibrary.editor_set_game_view(True)   # no editor icons, gizmos or volume boxes
except Exception as e: print('game view:', e)
unreal.AutomationLibrary.take_high_res_screenshot(2560, 1440, name + ".png", cam)
print("shot", name)
