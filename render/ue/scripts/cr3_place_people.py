# Place the MetaHumans at the performer positions of the stimuli (layout_ue.csv).
# Convention: the assembled MetaHuman blueprint for each performer is named BP_<Name> (Name = Singer, ViolinI, ViolinII,
# Viola, Cello, Contrabass, Flute, Clarinet, Bassoon, Horn1, Horn2), anywhere under /Game.
# Actors already in the level with the label <Name> are moved; otherwise BP_<Name> is spawned.
# Feet are put on the stage floor (Z = 100 cm); seated people still need their pose (the chair seat is at 145 cm).
# Not yet tested in UE 5.8 (written while the editor was closed).
import unreal, csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
log = Log("place_people")
HERE = os.path.dirname(os.path.abspath(__file__))
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); EAL = unreal.EditorAssetLibrary
rows = [r for r in csv.DictReader(open(os.path.join(HERE, "layout_ue.csv"))) if not r["name"].startswith("SeatCam")]
assets = EAL.list_assets("/Game", recursive=True, include_folder=False)
by = {a.get_actor_label(): a for a in ea.get_all_level_actors() if a.get_class().get_name().startswith("BP_")}   # only MetaHuman actors (instrument meshes share labels like "Flute")
for r in rows:
    name = r["name"]; loc = unreal.Vector(float(r["UE_X_cm"]), float(r["UE_Y_cm"]), float(r["UE_Z_floor_cm"]))
    rot = unreal.Rotator(roll=0.0, pitch=0.0, yaw=float(r["UE_yaw_deg"]) - 90.0)   # MetaHumans face +Y in their own frame
    a = by.get(name)
    if a is None:
        bp = next((p for p in assets if p.split("/")[-1].split(".")[0] in ("BP_" + name, "BP_MHC_" + name)), None)
        if bp is None: log(name, ": no actor and no BP_" + name, "- skipped"); continue
        cls = EAL.load_blueprint_class(bp.split(".")[0])
        a = ea.spawn_actor_from_class(cls, loc, rot); a.set_actor_label(name); log(name, ": spawned from", bp)
    a.set_actor_location(loc, False, False); a.set_actor_rotation(rot, False)
    log(name, r["posture"], "at", loc, "yaw", r["UE_yaw_deg"])
log("done")
