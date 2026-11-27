# sh run.sh <id> cr3_pose.py <Name> <seated|standing>
# Makes a one-frame pose (AnimSequence) for one MetaHuman from its own reference pose and plays it on the Body:
#   seated  : thighs forward (THIGH deg), shins vertical, arms down with forearms resting forward; actor lowered so feet touch the floor
#   standing: arms down only
# Component space of a MetaHuman: +Y forward, +Z up, +X = character's left.
import unreal, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
name, posture = sys.argv[1], sys.argv[2]
THIGH = 80.0
log = Log("pose_" + name)
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem); EAL = unreal.EditorAssetLibrary
act = [a for a in ea.get_all_level_actors() if a.get_actor_label() == name and a.get_class().get_name().startswith("BP_")][0]
body = [c for c in act.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Body"][0]
mesh = body.get_editor_property("skeletal_mesh_asset"); skel = mesh.get_editor_property("skeleton")
# reference pose from the component (anim BP shows the A-pose = reference)
try: unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()   # an open sequence would show the posed bones, not the reference
except Exception: pass
if body.get_editor_property("animation_mode") != unreal.AnimationMode.ANIMATION_BLUEPRINT or str(body.get_parent_bone("foot_l")) == "None":
    # a pose is already applied: go back to the A-pose first; the bones refresh on the next tick, so run this script again
    body.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    l = act.get_actor_location(); act.set_actor_location(unreal.Vector(l.x, l.y, 100.0), False, False)
    log("reset to reference pose - run again"); raise RuntimeError("reset - run again")
CS = lambda b: body.get_socket_transform(b, unreal.RelativeTransformSpace.RTS_COMPONENT)
par = lambda b: str(body.get_parent_bone(b))
V = lambda v: unreal.Vector(v[0], v[1], v[2])
def norm(v): l = math.sqrt(sum(x * x for x in v)); return [x / l for x in v]
def sub(a, b): return [a.x - b.x, a.y - b.y, a.z - b.z]
def qaxis(axis, deg):
    h = math.radians(deg) / 2; s = math.sin(h); a = norm(axis)
    return unreal.Quat(a[0] * s, a[1] * s, a[2] * s, math.cos(h))
def qbetween(u, v):   # shortest rotation u -> v (unit vectors)
    u, v = norm(u), norm(v); c = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    d = max(-1.0, min(1.0, sum(a * b for a, b in zip(u, v))))
    if math.sqrt(sum(x * x for x in c)) < 1e-6: return unreal.Quat(0, 0, 0, 1)
    return qaxis(c, math.degrees(math.acos(d)))
ref = {}
def ref_cs(b):
    if b not in ref: ref[b] = CS(b)
    return ref[b]
# desired component-space rotation deltas, applied top-down
targets = []   # (bone, child_bone_for_direction, target_direction) or (bone, quat)
def side(s): return 1.0 if s == "l" else -1.0
for s in "lr":
    targets.append(("upperarm_" + s, "lowerarm_" + s, [0.18 * side(s), 0.22, -1.0]))
    targets.append(("lowerarm_" + s, "hand_" + s, [-0.25 * side(s), 1.0, -0.35] if posture == "seated" else [0.05 * side(s), 0.15, -1.0]))
    if posture == "seated":
        targets.append(("thigh_" + s, "calf_" + s, [0.06 * side(s), math.sin(math.radians(THIGH)), -math.cos(math.radians(THIGH))]))
        targets.append(("calf_" + s, "foot_" + s, [0.0, 0.08, -1.0]))
keyed = [t[0] for t in targets]
# include every bone on the path between keyed bones so the hierarchy stays consistent
FINGERS = [f"{fg}_0{k}_{sd}" for sd in "lr" for fg in ("index", "middle", "ring", "pinky") for k in (1, 2, 3)]
FINGERS = [b for b in FINGERS if str(body.get_parent_bone(b)) not in ("None", "")]
allb = set(keyed) | set(FINGERS)
for b in keyed + FINGERS:
    p = par(b)
    while p and p != "None" and p not in ("pelvis", "spine_05", "clavicle_l", "clavicle_r"):
        allb.add(p); p = par(p)
def depth(b):
    n = 0
    while b not in ("None", ""): b = par(b); n += 1
    return n
order = sorted(allb, key=depth)
TWIST = {}
def solve(targets):
    global new
    new = {}
    tgt = {t[0]: t for t in targets}
    for b in order:
        p = par(b); local = ref_cs(b).multiply(ref_cs(p).inverse())
        w = local.multiply(fk(p))                      # parent as posed so far (also for parents that are not keyed)
        if b in TWIST: w = unreal.Transform(w.translation, unreal.MathLibrary.compose_rotators(w.rotation.rotator(), TWIST[b].rotator()), w.scale3d)
        if b in tgt:
            _, child, d = tgt[b]
            cl = ref_cs(child).multiply(ref_cs(b).inverse()).multiply(w)
            q = qbetween(sub(cl.translation, w.translation), d)
            w = unreal.Transform(w.translation, unreal.MathLibrary.compose_rotators(w.rotation.rotator(), q.rotator()), w.scale3d)
        new[b] = w
    return new
def fk(b):
    if b in new: return new[b]
    p = par(b)
    if p in ("None", ""): return ref_cs(b)
    return ref_cs(b).multiply(ref_cs(p).inverse()).multiply(fk(p))
cur = fk
solve(targets)
# arms onto the instrument grip points (render/instruments_v3.py -> hands_v3.json), two-bone IK in component space
import json
HJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hands_v3.json")
spec = json.load(open(HJ)).get(name) if os.path.exists(HJ) and "--noik" not in sys.argv else None
if spec:
    drop0 = (fk("foot_l").translation.z - ref_cs("foot_l").translation.z) if posture == "seated" else 0.0
    bw = body.get_world_transform(); al = act.get_actor_location()
    bw = unreal.Transform(unreal.Vector(bw.translation.x, bw.translation.y, bw.translation.z + (100.0 - drop0) - al.z), bw.rotation.rotator(), bw.scale3d)
    inv = bw.inverse()
    toc = lambda p: inv.transform_location(unreal.Vector(*p))
    def L(a, b): return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
    P = lambda v: [v.x, v.y, v.z]
    arms = []
    for s in "lr":
        h = spec.get(s.upper())
        if not h: continue
        S = P(ref_cs("upperarm_" + s).translation); Eref = P(ref_cs("lowerarm_" + s).translation); Href = P(ref_cs("hand_" + s).translation)
        a1, b1 = L(S, Eref), L(Eref, Href)
        T = P(toc(h["t"])); Pp = P(toc(h["pole"]))
        u = norm([t - x for t, x in zip(T, S)]); d = min(L(T, S), (a1 + b1) * 0.995)
        pv = [p - x for p, x in zip(Pp, S)]; pd = sum(x * y for x, y in zip(pv, u)); v = norm([x - pd * y for x, y in zip(pv, u)])
        ca = max(-1.0, min(1.0, (a1 * a1 + d * d - b1 * b1) / (2 * a1 * d))); sa = math.sqrt(1 - ca * ca)
        E = [S[i] + u[i] * a1 * ca + v[i] * a1 * sa for i in range(3)]; Tc = [S[i] + u[i] * d for i in range(3)]
        arms.append(("upperarm_" + s, "lowerarm_" + s, [E[i] - S[i] for i in range(3)]))
        arms.append(("lowerarm_" + s, "hand_" + s, [Tc[i] - E[i] for i in range(3)]))
        log("IK", s, "reach", round(L(T, S), 1), "of", round(a1 + b1, 1), "cm")
    targets = [t for t in targets if not t[0].startswith(("upperarm_", "lowerarm_"))] + arms
    solve(targets)
    def cross(a, b): return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
    def dot(a, b): return sum(x * y for x, y in zip(a, b))
    def palm_of(get, s):
        H, I, K, M = (P(get(b + s).translation) for b in ("hand_", "index_01_", "pinky_01_", "middle_01_"))
        return norm([m - h for m, h in zip(M, H)]), norm(cross([i - h for i, h in zip(I, H)], [k - h for k, h in zip(K, H)]))
    # turn the hand about the forearm so that the palm faces a given point ("face" in hands_v3.json)
    for s in "lr":
        h = spec.get(s.upper())
        if not h or "face" not in h or ("index_01_" + s) not in FINGERS: continue
        _, n0 = palm_of(ref_cs, s); sign = 1.0 if n0[2] < 0 else -1.0
        _, nn = palm_of(fk, s); nn = [x * sign for x in nn]
        W = P(fk("hand_" + s).translation); ax = norm([a - b for a, b in zip(W, P(fk("lowerarm_" + s).translation))])
        des = [a - b for a, b in zip(P(toc(h["face"])), W)]
        perp = lambda v: [v[i] - dot(v, ax) * ax[i] for i in range(3)]
        a_, b_ = perp(nn), perp(des)
        if dot(a_, a_) > 1e-6 and dot(b_, b_) > 1e-6:
            a_, b_ = norm(a_), norm(b_); ang = math.degrees(math.atan2(dot(cross(a_, b_), ax), dot(a_, b_)))
            TWIST["hand_" + s] = qaxis(ax, ang); log("palm", s, "turned", round(ang), "deg")
    if TWIST: solve(targets)
    # curl the fingers (grip): each segment turned from the hand direction towards the palm
    curl = []
    for s in "lr":
        if not spec.get(s.upper()) or ("index_01_" + s) not in FINGERS: continue
        def palm(get):
            H, I, K, M = (P(get(b + s).translation) for b in ("hand_", "index_01_", "pinky_01_", "middle_01_"))
            return norm([m - h for m, h in zip(M, H)]), norm(cross([i - h for i, h in zip(I, H)], [k - h for k, h in zip(K, H)]))
        _, n0 = palm(ref_cs); sign = 1.0 if n0[2] < 0 else -1.0          # in the A-pose the palm faces down
        fw, nn = palm(fk); nn = [x * sign for x in nn]
        for fg in ("index", "middle", "ring", "pinky"):
            for k, ang in ((1, 40.0), (2, 95.0)):
                c, sn = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                curl.append((f"{fg}_0{k}_{s}", f"{fg}_0{k+1}_{s}", [fw[i] * c + nn[i] * sn for i in range(3)]))
    if curl: solve(targets + curl); log("fingers curled:", len(curl))
# local transforms to key
anim_path = f"/Game/CR3Poses/A_{posture}_{name}"
if EAL.does_asset_exist(anim_path):   # reuse (deleting an asset in use opens a modal dialog)
    anim = EAL.load_asset(anim_path)
else:
    at = unreal.AssetToolsHelpers.get_asset_tools()
    fac = unreal.AnimSequenceFactory(); fac.set_editor_property("target_skeleton", skel)
    anim = at.create_asset(anim_path.split("/")[-1], "/Game/CR3Poses", unreal.AnimSequence, fac)
anim.set_preview_skeletal_mesh(mesh) if hasattr(anim, "set_preview_skeletal_mesh") else None
ctl = anim.get_editor_property("controller")
ctl.open_bracket(unreal.Text("pose"), True)
ctl.remove_all_bone_tracks(True)
ctl.set_frame_rate(unreal.FrameRate(30, 1), True)
ctl.set_number_of_frames(unreal.FrameNumber(1), True)
for b in order:
    loc = new[b].multiply(cur(par(b)).inverse())
    ctl.add_bone_curve(b, True) if hasattr(ctl, "add_bone_curve") else ctl.add_bone_track(b, True)
    pk = [loc.translation] * 2; rk = [loc.rotation] * 2; sk = [unreal.Vector(1, 1, 1)] * 2
    ctl.set_bone_track_keys(b, pk, rk, sk, True)
ctl.close_bracket(True)
EAL.save_loaded_asset(anim)
moved = {b: cur(b) for b in ("calf_l", "foot_l", "hand_l")}
# shown through the level sequence LS_CR3 (cr3_seq.py): MetaHumans in the editor do not play a single-node animation by themselves
# lower the actor so the feet stand on the floor
if posture == "seated":
    drop = moved["foot_l"].translation.z - ref_cs("foot_l").translation.z
    loc = act.get_actor_location(); act.set_actor_location(unreal.Vector(loc.x, loc.y, 100.0 - drop), False, False)
    log("lowered by", round(drop, 1), "cm; pelvis at", round(ref_cs("pelvis").translation.z - drop, 1), "cm above the floor")
for b in ("calf_l", "foot_l", "hand_l"): log(b, "ref", ref_cs(b).translation, "new", moved[b].translation)
# landmarks of the posed body in world coordinates (cm) for the instrument layout (render/instruments_v3.py)
import json
bw = body.get_world_transform()
lm = {b: [round(v, 2) for v in (cur(b).multiply(bw).translation.x, cur(b).multiply(bw).translation.y, cur(b).multiply(bw).translation.z)]
      for b in ("pelvis", "spine_03", "neck_01", "head", "upperarm_l", "upperarm_r", "hand_l", "hand_r", "foot_l", "foot_r")}
lm["yaw_actor"] = act.get_actor_rotation().yaw; lm["posture"] = posture
json.dump(lm, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_log", "landmarks_" + name + ".json"), "w"), indent=1)
log("pose", posture, "applied:", anim_path)
