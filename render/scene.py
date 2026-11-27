# Builds the full scene: CR3 hall (photo), audience chairs, parquet, PA loudspeakers, singer and ten players.
# usage: python scene.py <out.blend>     (render with render_seats.py)
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector, Matrix
from hall import reset, load_hall, pano_copy, P0
from people import load_avatar, place, ik, bone_world
import props as PR

HERE = os.path.dirname(os.path.abspath(__file__))
INFO = json.load(open(os.path.join(HERE, "scene.json")))
STAGE = 1.0

def heading(frm, to):
    return math.atan2(to[1] - frm[1], to[0] - frm[0])

def frame(yaw):
    f = Vector((math.cos(yaw), math.sin(yaw), 0)); l = Vector((0, 0, 1)).cross(f); return f, l, Vector((0, 0, 1))

AVATAR = {  # part -> (Rocketbox avatar, sex)
    "Violin I": ("Professions/Business_Male_01", "m"), "Violin II": ("Professions/Business_Female_01", "f"),
    "Viola": ("Professions/Business_Male_03", "m"), "Cello": ("Professions/Business_Male_05", "m"),
    "Contrabass": ("Professions/Business_Male_02", "m"), "Flute": ("Professions/Business_Female_04", "f"),
    "Clarinet": ("Professions/Business_Male_06", "m"), "Bassoon": ("Professions/Business_Male_01", "m"),
    "Horn 1": ("Professions/Business_Male_03", "m"), "Horn 2": ("Professions/Business_Male_05", "m"),
}

def player(p):
    part = p["part"]; rel, sex = AVATAR[part]; xy = p["pos"][:2]
    yaw = heading(xy, (4.0, 0.0))                       # turned towards the front of the stage, slightly to the centre
    f, l, z = frame(yaw); base = Vector((xy[0], xy[1], STAGE))
    standing = part == "Contrabass"
    pose = (f"{sex}_idle_neutral_01.max.fbx" if standing else f"{sex}_sit_chair_idle_neutral_01.max.fbx")
    arm, meshes = load_avatar(rel, pose, name="P_" + part.replace(" ", ""))
    place(arm, xy, STAGE, yaw)
    pel = bone_world(arm, 'Bip01 Pelvis')
    if not standing:
        PR.orchestra_chair(Vector((pel.x, pel.y, STAGE)) - f * 0.05, yaw)
    head = bone_world(arm, 'Bip01 Head'); neck = bone_world(arm, 'Bip01 Neck')
    shL = bone_world(arm, 'Bip01 L UpperArm'); shR = bone_world(arm, 'Bip01 R UpperArm')
    mouth = head + f * 0.09 + z * 0.0
    out = lambda side: (shL if side == 'L' else shR) + (l if side == 'L' else -l) * 0.35 - z * 0.25 - f * 0.1
    if part in ("Violin I", "Violin II", "Viola"):
        k = 1.12 if part == "Viola" else 1.0; L = 0.355 * k
        tail = neck + l * 0.11 - z * 0.03 + f * 0.04
        d = (f * 0.62 + l * 0.72 - z * 0.22).normalized()
        upv = (z * 0.8 - l * 0.45 + f * 0.1)
        PR.string_instrument(part.replace(" ", ""), L, 0.04 * k, 0.26 * k, tail, d, upv)
        ik(arm, 'L', tail + d * (L + 0.17 * k) - z * 0.03, pole=shL + l * 0.3 - z * 0.5)
        bridge = tail + d * (0.42 * L) + z * 0.05
        perp = d.cross(z).normalized()                  # across the strings, towards the player's right
        hand = bridge + perp * 0.25 - z * 0.03 + f * 0.05
        ik(arm, 'R', hand, pole=shR - l * 0.4 - z * 0.3)
        PR.bow(hand - perp * 0.05, hand - perp * 0.70 + z * 0.06)
    elif part in ("Cello", "Contrabass"):
        big = part == "Contrabass"; L = 1.12 if big else 0.75; rib = 0.19 if big else 0.12; neckL = 0.75 if big else 0.5
        foot = base + f * (0.42 if big else 0.45) + l * (0.12 if big else 0.02)
        top_to = (z * 1.0 - f * 0.22 + l * 0.12) if big else (z * 1.0 - f * 0.42 + l * 0.12)
        d = top_to.normalized(); tail = foot + d * (0.16 if big else 0.2)
        PR.string_instrument(part, L, rib, neckL, tail, d, f)
        PR.tube(part + "_endpin", foot, tail, 0.006, PR.mat("chrome", (0.6, 0.6, 0.62), 0.2, metal=1.0))
        ik(arm, 'L', tail + d * (L + neckL * 0.35) - f * 0.02 + l * 0.05, pole=shL + l * 0.4 - z * 0.2)
        bridge = tail + d * (0.38 * L) + f * (rib + 0.03)
        hand = bridge - l * 0.26 + z * 0.06 - f * 0.06
        ik(arm, 'R', hand, pole=shR - l * 0.4 - z * 0.4)
        PR.bow(hand + l * 0.02, hand + l * 0.68 - z * 0.04 + f * 0.04)
    elif part == "Flute":
        a = mouth - z * 0.04 + l * 0.04; d = (-l * 0.92 + f * 0.25 - z * 0.12).normalized()
        PR.flute(a, d); ik(arm, 'L', a + d * 0.14, pole=shL + l * 0.2 - z * 0.5); ik(arm, 'R', a + d * 0.45, pole=shR - l * 0.5 - z * 0.3)
    elif part == "Clarinet":
        a = mouth - z * 0.03; d = (f * 0.55 - z * 0.83).normalized()
        PR.clarinet(a, d); ik(arm, 'L', a + d * 0.22, pole=shL + l * 0.4 - z * 0.3); ik(arm, 'R', a + d * 0.45, pole=shR - l * 0.4 - z * 0.3)
    elif part == "Bassoon":
        b0 = pel + f * 0.28 - l * 0.16 - z * 0.15; ax = (z * 1.0 + l * 0.22 + f * 0.05).normalized()
        PR.bassoon(b0, ax, mouth - z * 0.02)
        ik(arm, 'L', b0 + ax * 0.78 + f * 0.04, pole=shL + l * 0.4 - z * 0.3); ik(arm, 'R', b0 + ax * 0.38 + f * 0.04 - l * 0.02, pole=shR - l * 0.4 - z * 0.3)
    elif part.startswith("Horn"):
        c = pel + f * 0.25 - l * 0.12 + z * 0.32
        PR.horn(c, l, (-l * 0.6 - f * 0.4 - z * 0.7))
        ik(arm, 'L', c + l * 0.02 + z * 0.05 + f * 0.02, pole=shL + l * 0.4 - z * 0.3)
        ik(arm, 'R', c - l * 0.2 - z * 0.12 - f * 0.08, pole=shR - l * 0.4 - z * 0.3)
    if part not in ("Contrabass",):
        PR.music_stand(base + f * 0.8 - l * 0.05, yaw + math.pi, 0.86)
    return arm

def singer(pos):
    xy = pos[:2]; yaw = heading(xy, (9.0, 0.0)); f, l, z = frame(yaw)
    arm, meshes = load_avatar("Professions/Business_Female_04", "f_idle_neutral_01.max.fbx", name="Singer")
    place(arm, xy, STAGE, yaw)
    pel = bone_world(arm, 'Bip01 Pelvis'); spine = bone_world(arm, 'Bip01 Spine1')
    shL = bone_world(arm, 'Bip01 L UpperArm'); shR = bone_world(arm, 'Bip01 R UpperArm')
    waist = spine + f * 0.17 - z * 0.02
    ik(arm, 'L', waist + l * 0.03, pole=shL + l * 0.4 - z * 0.3 - f * 0.2)
    ik(arm, 'R', waist - l * 0.03 + z * 0.02, pole=shR - l * 0.4 - z * 0.3 - f * 0.2)
    # floor-length gown (deep blue satin) from the waist; the jacket stays as the top
    satin = PR.mat("satin", (0.02, 0.035, 0.14), 0.42, sheen=0.25)
    h = pel.z + 0.1 - STAGE
    prof = [(0.145, h), (0.17, h - 0.08), (0.19, h - 0.2), (0.2, h - 0.34), (0.205, h - 0.55), (0.22, 0.32), (0.25, 0.1), (0.27, 0.01), (0.272, 0.0)]
    g = PR.lathe("gown", prof, satin, (pel.x, pel.y, STAGE), segs=96, scale=(1.0, 0.78, 1.0))
    g.rotation_euler.z = yaw
    # soft folds: displacement by a stretched noise, stronger towards the hem
    tex = bpy.data.textures.new("folds", 'WOOD'); tex.wood_type = 'BANDNOISE'; tex.noise_scale = 0.06; tex.turbulence = 3.0
    g.modifiers.new("sub", 'SUBSURF').levels = 2
    dm = g.modifiers.new("folds", 'DISPLACE'); dm.texture = tex; dm.strength = 0.01; dm.texture_coords = 'LOCAL'
    g.modifiers.new("sub2", 'SUBSURF').levels = 1
    # hide the trousers under the gown: legs are inside, nothing to do
    return arm

def lights():
    sc = bpy.context.scene
    def spot(loc, aim, power, size_deg, color=(1.0, 0.86, 0.72), blend=0.6, radius=0.25):
        ld = bpy.data.lights.new("spot", 'SPOT'); ld.energy = power; ld.spot_size = math.radians(size_deg); ld.spot_blend = blend; ld.color = color; ld.shadow_soft_size = radius
        o = bpy.data.objects.new("spot", ld); sc.collection.objects.link(o); o.location = loc
        d = Vector(aim) - Vector(loc); o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, -1)).rotation_difference(d)
    for y in (-3.0, -1.0, 1.0, 3.0):            # front truss (seen in the photo above the stage front)
        spot((1.2, y, 6.6), (-5.0, y * 0.55, 1.5), 900, 42)
    area = bpy.data.lights.new("stage_top", 'AREA'); area.energy = 900; area.size = 6; area.color = (1.0, 0.9, 0.8)
    o = bpy.data.objects.new("stage_top", area); sc.collection.objects.link(o); o.location = (-5.5, 0, 6.8)

def build():
    sc = reset(); load_hall(pano_copy(INFO["pano"]["file"]))
    PR.floor_plane(PR.parquet(os.path.join(HERE, "parquet.jpg")))
    PR.audience_chairs(INFO["seats"]["C"][0])
    for p in INFO["pa"]: PR.pa_speaker(p, INFO["seats"]["C"])
    for p in INFO["players"]: player(p)
    singer(INFO["singer"])
    lights()
    cy = sc.cycles; cy.samples = 128; cy.use_denoising = True; cy.max_bounces = 6; cy.transparent_max_bounces = 16; cy.caustics_reflective = False; cy.caustics_refractive = False
    cy.sample_clamp_indirect = 5.0
    return sc

if __name__ == "__main__":
    build()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(sys.argv[-1] if sys.argv[-1].endswith(".blend") else os.path.join(HERE, "cr3_seats.blend")))
