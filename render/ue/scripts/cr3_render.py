# Render the three seat views with Movie Render Queue: 2560 x 1440 PNG, temporal AA 16 samples, 64 warm-up frames.
# Makes one Level Sequence per seat (/Game/CR3/Seq/LS_Seat_<S>, camera cut to SeatCam_<S>, 1 frame) and queues them.
# Output: <project>/Saved/MovieRenders/seat_<S>.png. Not yet tested in UE 5.8 (written while the editor was closed).
import unreal, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
log = Log("render")
SEATS = sys.argv[1:] or ["L", "C", "R"]
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); EAL = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
by = {a.get_actor_label(): a for a in ea.get_all_level_actors()}
for n, a in by.items():   # markers and axis bars must not be in the picture
    if n.startswith(("MARK_", "AXIS_")): a.set_actor_hidden_in_game(True); a.set_is_temporarily_hidden_in_editor(True)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
level_path = world.get_path_name().split(":")[0]
q = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem).get_queue()
for j in list(q.get_jobs()): q.delete_job(j)
for s in SEATS:
    cam = by["SeatCam_" + s]; path = f"/Game/CR3/Seq/LS_Seat_{s}"
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    seq = tools.create_asset(f"LS_Seat_{s}", "/Game/CR3/Seq", unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    seq.set_display_rate(unreal.FrameRate(24, 1)); seq.set_playback_start(0); seq.set_playback_end(1)
    binding = seq.add_possessable(cam)
    cut = seq.add_track(unreal.MovieSceneCameraCutTrack).add_section(); cut.set_range(0, 1)
    cut.set_camera_binding_id(seq.get_binding_id(binding))
    EAL.save_loaded_asset(seq)
    job = q.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.set_editor_property("map", unreal.SoftObjectPath(level_path)); job.set_editor_property("sequence", unreal.SoftObjectPath(path))
    job.set_editor_property("job_name", f"seat_{s}")
    cfg = job.get_configuration()
    out = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    out.set_editor_property("output_resolution", unreal.IntPoint(2560, 1440))
    out.set_editor_property("file_name_format", f"seat_{s}")
    out.set_editor_property("output_directory", unreal.DirectoryPath(os.path.join(unreal.Paths.project_saved_dir(), "MovieRenders")))
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    aa.set_editor_property("temporal_sample_count", 16); aa.set_editor_property("spatial_sample_count", 1)
    aa.set_editor_property("override_anti_aliasing", True); aa.set_editor_property("anti_aliasing_method", unreal.AntiAliasingMethod.AAM_NONE)
    aa.set_editor_property("engine_warm_up_count", 64); aa.set_editor_property("render_warm_up_frames", True)
    log("queued", s, "camera", cam.get_actor_location(), cam.get_actor_rotation())
unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem).render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
log("rendering started; output", os.path.join(unreal.Paths.project_saved_dir(), "MovieRenders"))
