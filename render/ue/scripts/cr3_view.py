# py "<path>/cr3_view.py" C     -> look through SeatCam_C in the viewport and save a test shot (Saved/Screenshots)
import unreal, sys
seat = (sys.argv[1] if len(sys.argv) > 1 else "C").upper()
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
by = {a.get_actor_label(): a for a in ea.get_all_level_actors()}
for name, a in by.items():   # nothing of the scene should be hidden in the editor; markers are hidden for shots
    a.set_is_temporarily_hidden_in_editor(name.startswith(("MARK_", "AXIS_")))
ea.select_nothing()
cam = by["SeatCam_" + seat]
les.pilot_level_actor(cam)
unreal.AutomationLibrary.take_high_res_screenshot(1920, 1080, f"test_seat_{seat}.png", cam)
unreal.log(f"[CR3] piloting SeatCam_{seat}; test shot requested: Saved/Screenshots/.../test_seat_{seat}.png  project dir: {unreal.Paths.project_saved_dir()}")
