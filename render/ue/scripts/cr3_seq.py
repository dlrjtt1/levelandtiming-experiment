# sh run.sh <id> cr3_seq.py   -> level sequence /Game/LS_CR3 with each performer's pose on its Body, opened at frame 0
import unreal, os, sys, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
log = Log("seq"); HERE = os.path.dirname(os.path.abspath(__file__))
EAL = unreal.EditorAssetLibrary; ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); LSE = unreal.LevelSequenceEditorBlueprintLibrary
try: LSE.close_level_sequence()
except Exception: pass
path = "/Game/LS_CR3"
if EAL.does_asset_exist(path): seq = EAL.load_asset(path)
else: seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset("LS_CR3", "/Game", unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
for b in list(seq.get_bindings()): b.remove()
seq.set_display_rate(unreal.FrameRate(30, 1)); seq.set_playback_start(0); seq.set_playback_end(30)
rows = [r for r in csv.DictReader(open(os.path.join(HERE, "layout_ue.csv"))) if not r["name"].startswith("SeatCam")]
for r in rows:
    name = r["name"]; posture = "seated" if r["posture"] == "seated" else "standing"
    act = [a for a in ea.get_all_level_actors() if a.get_actor_label() == name and a.get_class().get_name().startswith("BP_")]
    anim = EAL.load_asset(f"/Game/CR3Poses/A_{posture}_{name}") if EAL.does_asset_exist(f"/Game/CR3Poses/A_{posture}_{name}") else None
    if not act or not anim: log(name, "skipped (actor or pose missing)"); continue
    body = [c for c in act[0].get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body"][0]
    seq.add_possessable(act[0]); bb = seq.add_possessable(body)
    tr = bb.add_track(unreal.MovieSceneSkeletalAnimationTrack); sec = tr.add_section()
    sec.set_range(0, 30)
    prm = sec.get_editor_property("params"); prm.set_editor_property("animation", anim); sec.set_editor_property("params", prm)
    log(name, posture, "bound")
EAL.save_loaded_asset(seq)
LSE.open_level_sequence(seq); LSE.set_current_time(0); LSE.refresh_current_level_sequence()
log("opened", path)
