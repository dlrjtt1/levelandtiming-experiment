# Stage shell rebuilt for the side seats. All angles below are measured in the levelled photo (hall.pano_level).
# The hall is the BRAS 360° photo projected on the BRAS model from one point (P0); the model's
# shell slabs are 0.15-0.35 m taller than the real ones and the house curtains are not in the model, so from the side seats the photo of
# the towers, the curtains and the dark fly space lands on the wrong surfaces. This script builds, in front of the model's surfaces:
#   - eight shell towers and the rear wall with the heights measured in the photo, textured with their own part of the photo
#     (parts hidden from P0 behind the next tower or the curtain are filled by repeating the last visible column),
#   - the two house curtains (missing in the model), textured from the photo,
#   - black masking on the stage-house walls behind the shell.
# Writes ue/CR3_shellfix.fbx (one mesh, world position, UVs) and ue/T_CR3_shell.png.   usage: python shell_fix.py [--blend]
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
P0 = np.array([7.7, 0.0, 1.7])
from hall import pano_level, PANO_YAW as DY      # the az values below were measured before the photo was centred: + DY
PANO = np.asarray(Image.open(os.path.join(HERE, pano_level())).convert("RGB")).astype(np.float32)      # the levelled photo
PH, PW = PANO.shape[:2]

def sample(az, el):
    """bilinear sample of the photo; az in degrees (0 = stage centre, + = right as seen from the audience), el in degrees"""
    x = (az / 360 + 0.5) * PW - 0.5; y = (0.5 - el / 180) * PH - 0.5
    x0 = np.floor(x).astype(int); y0 = np.clip(np.floor(y).astype(int), 0, PH - 2); fx = (x - x0)[..., None]; fy = np.clip(y - y0, 0, 1)[..., None]
    a = PANO[y0, x0 % PW] * (1 - fx) + PANO[y0, (x0 + 1) % PW] * fx; b = PANO[y0 + 1, x0 % PW] * (1 - fx) + PANO[y0 + 1, (x0 + 1) % PW] * fx
    return a * (1 - fy) + b * fy

def edges(az0, az1, n=40, top_from=20.0):
    """top (first lit row below the black fly space) and bottom (first stage-floor row) of a shell element in the photo, as straight lines over az"""
    azs = np.linspace(az0, az1, n); tops, bots = [], []
    for a in azs:
        el = np.arange(top_from, 6.0, -0.03); lum = sample(np.full_like(el, a), el).mean(1)
        lit = np.convolve((lum > 15).astype(float), np.ones(8) / 8, mode="same") > 0.95
        tops.append(el[np.argmax(lit)] - 0.10 if lit.any() else np.nan)
        el = np.arange(-1.2, -5.0, -0.03); c = sample(np.full_like(el, a), el); lum = c.mean(1)
        floor = np.convolve(((lum < 58) | ((c[:, 0] - c[:, 2] > 45) & (lum < 92))).astype(float), np.ones(5) / 5, mode="same") > 0.95
        bots.append(el[np.argmax(floor)] + 0.14 if floor.any() else np.nan)
    def line(v):
        v = np.array(v); ok = ~np.isnan(v); med = np.median(v[ok]); ok &= np.abs(v - med) < 0.6
        return np.polyfit(azs[ok], v[ok], 1)
    return line(tops), line(bots)

TILES = []      # (name, image array, padding) ; packed below
def make_tile(name, w_px, h_px, pos, az_lim, el_fit, z0, z1, pad=6, el_clip=None):
    """pos(s, z) -> world points for s, z arrays; the tile covers s 0..1 (left to right) and z z0..z1 (bottom to top), plus padding"""
    s = (np.arange(-pad, w_px + pad) + 0.5) / w_px; f = (np.arange(-pad, h_px + pad) + 0.5) / h_px
    S, Fr = np.meshgrid(np.clip(s, 0, 1), np.clip(f[::-1], 0, 1))           # image row 0 = top
    Q = pos(S, z0 + Fr * (z1 - z0)); d = Q - P0
    az = np.clip(np.degrees(np.arctan2(d[..., 1], -d[..., 0])), min(az_lim), max(az_lim))
    if el_fit is None:      # the photo as it is in this direction
        el = np.degrees(np.arctan2(d[..., 2], np.hypot(d[..., 0], d[..., 1])))
        if el_clip: el = np.clip(el, el_clip[0](az), el_clip[1](az))
    else:                   # between the element's bottom and top edge in the photo
        t_top = np.tan(np.radians(np.polyval(el_fit[0], az))); t_bot = np.tan(np.radians(np.polyval(el_fit[1], az)))
        el = np.degrees(np.arctan(t_bot + Fr * (t_top - t_bot)))
    TILES.append((name, np.clip(sample(az, el), 0, 255).astype(np.uint8), pad)); return name

V, F, UVT = [], [], []          # vertices, faces, per face: (tile name, [(u, v) in tile units 0..1])
def face(pts, tile, uv, outward):
    pts = [np.array(p, float) for p in pts]
    if np.dot(np.cross(pts[1] - pts[0], pts[2] - pts[0]), outward) < 0: pts = pts[::-1]; uv = uv[::-1]
    i = len(V); V.extend(pts); F.append(tuple(range(i, i + len(pts)))); UVT.append((tile, uv))

Z0 = 1.0
# ---- towers: plan end points (inner, outer) of the model's slabs (stagePanels group of cr3.obj) and the az range visible in the photo
TOWERS = [("T1L", (-3.75, -3.47), (-3.14, -4.74), (-17.3, -21.3)), ("T2L", (-4.65, -3.27), (-4.09, -4.55), (-15.25, -16.75)),
          ("T3L", (-6.05, -3.11), (-5.32, -4.31), (-13.15, -14.75)), ("T4L", (-7.20, -2.90), (-6.47, -4.09), (-11.5, -12.75)),
          ("T1R", (-3.70, 3.36), (-3.13, 4.64), (15.85, 19.35)), ("T2R", (-4.62, 3.18), (-4.10, 4.49), (14.05, 15.4)),
          ("T3R", (-5.98, 2.98), (-5.39, 4.24), (11.85, 13.5)), ("T4R", (-7.02, 2.75), (-6.55, 4.08), (10.15, 11.4))]
report = []
for name, A, B, azv in TOWERS:
    azv = (azv[0] + DY, azv[1] + DY)
    A, B = np.array([*A, 0.0]), np.array([*B, 0.0]); t = (B - A); wid = np.linalg.norm(t); t /= wid; n = np.array([-t[1], t[0], 0.0])
    if n[0] < 0: n = -n
    fit = edges(min(azv), max(azv))
    azm = np.mean(azv); r = np.array([-math.cos(math.radians(azm)), math.sin(math.radians(azm))])       # ray from P0 in plan
    M = np.array([[r[0], -t[0]], [r[1], -t[1]]]); dist, _ = np.linalg.solve(M, (A[:2] - P0[:2]))
    ztop = P0[2] + dist * math.tan(math.radians(np.polyval(fit[0], azm)))
    Af, Bf = A + n * 0.03 - t * 0.02, B + n * 0.03 + t * 0.02; wf = np.linalg.norm(Bf - Af)
    pos = lambda S, Z, Af=Af, Bf=Bf: Af[None, None, :] * (1 - S[..., None]) + Bf[None, None, :] * S[..., None] + np.array([0, 0, 1.0]) * Z[..., None]
    make_tile(name, int(wf * 260), int((ztop - Z0) * 260), pos, azv, fit, Z0, ztop)
    up = np.array([0, 0, 1.0]); lo = lambda P: P + up * Z0; hi = lambda P: P + up * ztop
    face([lo(Af), lo(Bf), hi(Bf), hi(Af)], name, [(0, 0), (1, 0), (1, 1), (0, 1)], n)                         # front
    for P, u, o in ((Af, 0.01, -t), (Bf, 0.99, t)):                                                          # the two ends
        Pb = P - n * 0.10; face([lo(P), lo(Pb), hi(Pb), hi(P)], name, [(u, 0), (u, 0), (u, 1), (u, 1)], o)
    # black cover over the rest of the model's slab (to 5.5 m), which carries the photo of whatever stood in front of it
    ZM = 5.53; hm = lambda P: P + up * ZM; K = [(0.5, 0.5)] * 4
    face([hi(Af), hi(Bf), hm(Bf), hm(Af)], "black", K, n); face([hm(Af), hm(Bf), hm(Bf - n * 0.10), hm(Af - n * 0.10)], "black", K, up)
    for P, o in ((Af, -t), (Bf, t)): face([hi(P), hi(P - n * 0.10), hm(P - n * 0.10), hm(P)], "black", K, o)
    report.append((name, round(float(ztop), 2), [round(float(x), 2) for x in np.polyval(fit[0], azv)], [round(float(x), 2) for x in np.polyval(fit[1], azv)]))

# ---- rear wall: in front of the model's slab at x = -8.20; visible in the photo between the innermost towers
XW, YL, YR = -8.16, -3.62, 3.52; azv = (-10.6 + DY, 8.7 + DY); fit = edges(*azv, top_from=14.0)
zw = P0[2] + (P0[0] - XW) * math.tan(math.radians(np.polyval(fit[0], 0.0)))
pos = lambda S, Z: np.stack([np.full_like(S, XW), YL + S * (YR - YL), Z], -1)
make_tile("wall", int((YR - YL) * 260), int((zw - Z0) * 260), pos, azv, fit, Z0, zw)
face([(XW, YL, Z0), (XW, YR, Z0), (XW, YR, zw), (XW, YL, zw)], "wall", [(0, 0), (1, 0), (1, 1), (0, 1)], np.array([1.0, 0, 0]))
for y, u, o in ((YL, 0.002, -1), (YR, 0.998, 1)):
    face([(XW, y, Z0), (XW - 0.10, y, Z0), (XW - 0.10, y, zw), (XW, y, zw)], "wall", [(u, 0), (u, 0), (u, 1), (u, 1)], np.array([0, o, 0.0]))
K = [(0.5, 0.5)] * 4; ZM = 5.53
face([(XW, YL, zw), (XW, YR, zw), (XW, YR, ZM), (XW, YL, ZM)], "black", K, np.array([1.0, 0, 0]))
face([(XW, YL, ZM), (XW, YR, ZM), (XW - 0.10, YR, ZM), (XW - 0.10, YL, ZM)], "black", K, np.array([0, 0, 1.0]))
for y, o in ((YL, -1), (YR, 1)): face([(XW, y, zw), (XW - 0.10, y, zw), (XW - 0.10, y, ZM), (XW, y, ZM)], "black", K, np.array([0, o, 0.0]))
report.append(("wall", round(float(zw), 2), [round(float(x), 2) for x in np.polyval(fit[0], azv)], [round(float(x), 2) for x in np.polyval(fit[1], azv)]))

# ---- house curtains and proscenium jambs: in the photo the opening is narrower than in the model (edge at az -23.65 / 22.05 instead of
# -24.6 / 24.0) and a curtain hangs behind each edge; neither is in the model, so their photo fell on the towers and walls behind
XC, XJ, ZC = -2.40, -2.215, 5.90
for name, azv, az_j, y_model in (("CurtL", (-22.1, -23.5), -23.65, -4.53), ("CurtR", (20.1, 21.9), 22.05, 4.42)):
    azv = (azv[0] + DY, azv[1] + DY); az_j += DY
    sg = np.sign(y_model); yin = math.tan(math.radians(azv[0])) * (P0[0] - XC); yj = math.tan(math.radians(az_j)) * (P0[0] - XJ); yout = yj + sg * 0.05
    top = np.array([0.0, 19.75]); bot = np.array([0.0, -2.95])
    pos = lambda S, Z, yin=yin, yout=yout: np.stack([np.full_like(S, XC), yin + S * (yout - yin), Z], -1)
    make_tile(name, int(abs(yout - yin) * 300), int((ZC - Z0) * 260), pos, azv, (top, bot), Z0, ZC)
    face([(XC, yin, Z0), (XC, yout, Z0), (XC, yout, ZC), (XC, yin, ZC)], name, [(0, 0), (1, 0), (1, 1), (0, 1)], np.array([1.0, 0, 0]))
    face([(XC, yin, Z0), (XC - 0.06, yin, Z0), (XC - 0.06, yin, ZC), (XC, yin, ZC)], name, [(0.02, 0), (0.02, 0), (0.02, 1), (0.02, 1)], np.array([0, -sg, 0.0]))
    ym = y_model + sg * 0.03; jn = name.replace("Curt", "Jamb")
    pos = lambda S, Z, yj=yj, ym=ym: np.stack([np.full_like(S, XJ), yj + S * (ym - yj), Z], -1)
    make_tile(jn, int(abs(ym - yj) * 300), int((ZC - Z0) * 260), pos, (az_j + sg * 0.08, sg * 40), None, Z0, ZC)
    face([(XJ, yj, Z0), (XJ, ym, Z0), (XJ, ym, ZC), (XJ, yj, ZC)], jn, [(0, 0), (1, 0), (1, 1), (0, 1)], np.array([1.0, 0, 0]))
    face([(XJ, yj, Z0), (XJ - 0.40, yj, Z0), (XJ - 0.40, yj, ZC), (XJ, yj, ZC)], jn, [(0.03, 0), (0.03, 0), (0.03, 1), (0.03, 1)], np.array([0, -sg, 0.0]))
    report.append((name, "curtain y", round(float(yin), 2), "jamb y", round(float(yj), 2)))

# ---- black masking in front of the stage-house walls (side walls y = 5.59 / -5.64, rear wall x = -10.21)
TILES.append(("black", np.full((40, 40, 3), 1, np.uint8), 0))
for y, ny in ((5.54, -1), (-5.59, 1)):
    face([(-10.15, y, Z0), (-2.63, y, Z0), (-2.63, y, 7.70), (-10.15, y, 7.70)], "black", [(0.5, 0.5)] * 4, np.array([0, ny, 0.0]))
face([(-10.15, -5.59, Z0), (-10.15, 5.54, Z0), (-10.15, 5.54, 5.82), (-10.15, -5.59, 5.82)], "black", [(0.5, 0.5)] * 4, np.array([1.0, 0, 0]))
# ---- top of the stage opening. In the photo the header's lower edge is a little lower than the model's opening (5.84 m) and the stage
# lamps hang just behind it; the photo of both fell through the opening onto the fly-space ceiling, the upper rear wall and the two
# ceiling reflectors, where it slides and breaks up when seen from the side seats. Header and lamps get their own surfaces at the
# opening; everything above the shell inside the stage house is masked black.
azs = np.arange(-24.0, 24.01, 0.25); es = []
for a in azs:
    el = np.arange(19.0, 26.0, 0.03); c = sample(np.full_like(el, a), el)
    org = np.convolve(((c[:, 0] - c[:, 2] > 50) & (c.mean(1) > 60)).astype(float), np.ones(6) / 6, mode="same") > 0.95
    es.append(el[np.argmax(org)] if org.any() else np.nan)
es = np.array(es); es[np.isnan(es)] = np.nanmedian(es)
es = np.array([np.median(es[max(0, i - 12):i + 13]) for i in range(len(es))])       # the lamps and the wire are outliers
edge = lambda az: np.interp(az, azs, es)
kh = float(np.median(np.tan(np.radians(es[np.abs(azs) < 20])) / np.cos(np.radians(azs[np.abs(azs) < 20])))); XH = -2.195; zh = P0[2] + kh * (P0[0] - XH)
YA, YB, ZHT = -4.62, 4.52, 5.90; K = [(0.5, 0.5)] * 4
pos = lambda S, Z: np.stack([np.full_like(S, XH), YA + S * (YB - YA), Z], -1)
make_tile("header", int((YB - YA) * 260), int((ZHT - zh) * 260) + 8, pos, (-40, 40), None, zh, ZHT, el_clip=(lambda az: edge(az) + 0.18, lambda az: az * 0 + 60))
face([(XH, YA, zh), (XH, YB, zh), (XH, YB, ZHT), (XH, YA, ZHT)], "header", [(0, 0), (1, 0), (1, 1), (0, 1)], np.array([1.0, 0, 0]))
face([(XH, YA, zh), (XH, YB, zh), (-2.62, YB, zh), (-2.62, YA, zh)], "header", [(0, 0.5), (1, 0.5), (1, 0.5), (0, 0.5)], np.array([0, 0, -1.0]))
XL, YLa, YLb = -2.75, -4.35, 4.25; zl0 = P0[2] + (P0[0] - XL) * math.tan(math.radians(19.2)); zl1 = zh + 0.30      # lamp board
pos = lambda S, Z: np.stack([np.full_like(S, XL), YLa + S * (YLb - YLa), Z], -1)
make_tile("lamps", int((YLb - YLa) * 260), int((zl1 - zl0) * 260), pos, (-19.0, 19.0), None, zl0, zl1, el_clip=(lambda az: az * 0 - 60, lambda az: edge(az) - 0.22))
face([(XL, YLa, zl0), (XL, YLb, zl0), (XL, YLb, zl1), (XL, YLa, zl1)], "lamps", [(0, 0), (1, 0), (1, 1), (0, 1)], np.array([1.0, 0, 0]))
face([(-8.68, -5.59, 5.84), (-8.68, 5.54, 5.84), (-8.68, 5.54, 7.70), (-8.68, -5.59, 7.70)], "black", K, np.array([1.0, 0, 0]))          # upper rear wall
face([(-10.15, -5.59, 7.66), (-2.63, -5.59, 7.66), (-2.63, 5.54, 7.66), (-10.15, 5.54, 7.66)], "black", K, np.array([0, 0, -1.0]))       # fly-space ceiling
for (xa, za), (xb, zb), nn in (((-3.84, 6.38), (-5.20, 5.66), (0.47, 0, -0.88)), ((-6.01, 6.37), (-6.83, 5.54), (0.71, 0, -0.70))):     # ceiling reflectors
    nn = np.array(nn); o = nn * 0.05; e = np.array([xa - xb, 0, za - zb]); e = e / np.linalg.norm(e) * 0.06
    A_, B_ = np.array([xa, 0, za]) + o + e, np.array([xb, 0, zb]) + o - e
    face([A_ + [0, -3.4, 0], A_ + [0, 3.4, 0], B_ + [0, 3.4, 0], B_ + [0, -3.4, 0]], "black", K, nn)
    for P_ in (A_, B_): face([P_ + [0, -3.4, 0], P_ + [0, 3.4, 0], P_ - o * 3 + [0, 3.4, 0], P_ - o * 3 + [0, -3.4, 0]], "black", K, np.sign(P_[0] - (xa + xb) / 2) * np.array([1.0, 0, 0]))
report.append(("header", "z", round(float(zh), 2), "lamp board z", round(float(zl0), 2), round(float(zl1), 2)))
for r in report: print(r)

# ---- pack the tiles into one texture (shelves)
AW = 4096; x = y = rowh = 0; place = {}
for name, im, pad in sorted(TILES, key=lambda t: -t[1].shape[0]):
    h, w = im.shape[:2]
    if x + w > AW: x = 0; y += rowh; rowh = 0
    place[name] = (x, y, w, h, pad); x += w; rowh = max(rowh, h)
AH = 1 << math.ceil(math.log2(y + rowh)); atlas = np.zeros((AH, AW, 3), np.uint8)
for name, im, pad in TILES:
    x, y, w, h, _ = place[name]; atlas[y:y + h, x:x + w] = im
Image.fromarray(atlas).save(os.path.join(HERE, "ue", "T_CR3_shell.png")); print("atlas", AW, AH)

import bpy
from hall import reset
sc = reset()
me = bpy.data.meshes.new("ShellFix"); me.from_pydata([tuple(v) for v in V], [], F); me.update()
uvl = me.uv_layers.new(name="UVMap"); k = 0
for tile, uv in UVT:
    x, y, w, h, pad = place[tile]
    for u, v in uv:
        px = x + pad + u * (w - 2 * pad); py = y + pad + (1 - v) * (h - 2 * pad)
        uvl.data[k].uv = (px / AW, 1 - py / AH); k += 1
m = bpy.data.materials.new("shell_photo"); me.materials.append(m)
ob = bpy.data.objects.new("ShellFix", me); sc.collection.objects.link(ob)
if "--blend" in sys.argv: bpy.ops.wm.save_as_mainfile(filepath="/tmp/shellfix.blend")
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.fbx(filepath=os.path.join(HERE, "ue", "CR3_shellfix.fbx"), use_selection=True, object_types={'MESH'},
                         apply_scale_options='FBX_SCALE_ALL', path_mode='STRIP', mesh_smooth_type='FACE', add_leaf_bones=False)
print("shellfix:", len(me.vertices), "verts", len(me.polygons), "faces")
