# Violin-family instruments with real proportions: outline with C-bouts and corners, arched top and back, ribs,
# f-holes, neck, fingerboard, pegbox with scroll and pegs, bridge, tailpiece, four strings, chinrest (violin, viola).
# Wood is a drawn texture (spruce top, flamed maple back and ribs) so it survives the FBX export.
# Local frame: +y from the tail end to the scroll, +z out of the top plate, origin at the bottom of the body.
import bpy, bmesh, math, os
import numpy as np
from mathutils import Vector
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); TEX = os.path.join(HERE, "ue"); os.makedirs(TEX, exist_ok=True)

KINDS = {  # body length L (m) and everything else as a fraction of L, from standard instrument dimensions
    "violin": dict(rib=0.085, arch=0.045, neck=0.365, fb=0.76, bridge_y=0.452, bridge_h=0.093, fb_w0=0.067, fb_w1=0.118, pegbox=0.20, tone="amber", chin=True),
    "viola":  dict(rib=0.090, arch=0.045, neck=0.360, fb=0.75, bridge_y=0.452, bridge_h=0.095, fb_w0=0.062, fb_w1=0.112, pegbox=0.20, tone="amber", chin=True),
    "cello":  dict(rib=0.155, arch=0.036, neck=0.370, fb=0.77, bridge_y=0.467, bridge_h=0.120, fb_w0=0.042, fb_w1=0.085, pegbox=0.19, tone="red", chin=False),
    "bass":   dict(rib=0.185, arch=0.034, neck=0.385, fb=0.78, bridge_y=0.450, bridge_h=0.140, fb_w0=0.040, fb_w1=0.080, pegbox=0.17, tone="red", chin=False),
}
# half outline (half width, y) / L from the bottom to the top; "c" marks the two corners of the C-bout
OUT_VIOLIN = [(0, 0), (0.10, 0.004), (0.20, 0.028), (0.265, 0.09), (0.292, 0.17), (0.287, 0.25), (0.262, 0.33), (0.240, 0.385), (0.250, 0.402, "c"),
              (0.192, 0.425), (0.163, 0.47), (0.157, 0.52), (0.166, 0.57), (0.196, 0.612), (0.222, 0.632, "c"),
              (0.208, 0.655), (0.226, 0.72), (0.236, 0.79), (0.224, 0.87), (0.18, 0.94), (0.10, 0.988), (0, 1.0)]
OUT_BASS = [(0, 0), (0.11, 0.004), (0.22, 0.028), (0.285, 0.09), (0.305, 0.17), (0.298, 0.25), (0.270, 0.33), (0.246, 0.385), (0.254, 0.402, "c"),
            (0.196, 0.425), (0.168, 0.47), (0.162, 0.52), (0.170, 0.57), (0.198, 0.612), (0.220, 0.632, "c"),
            (0.205, 0.655), (0.212, 0.72), (0.200, 0.79), (0.165, 0.87), (0.115, 0.94), (0.06, 0.985), (0, 1.0)]

def _catmull(P, n=24):
    P = np.array(P, float); Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]]); out = []
    for i in range(1, len(Q) - 2):
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        out.append(0.5 * ((2 * Q[i]) + (-Q[i - 1] + Q[i + 1]) * t + (2 * Q[i - 1] - 5 * Q[i] + 4 * Q[i + 1] - Q[i + 2]) * t ** 2 + (-Q[i - 1] + 3 * Q[i] - 3 * Q[i + 1] + Q[i + 2]) * t ** 3))
    return np.vstack(out + [P[-1:]])

def half_width(outline):
    """returns a function w(y) on 0..1 and the y values of the corners"""
    segs, cur, corners = [], [], []
    for p in outline:
        cur.append(p[:2])
        if len(p) == 3: segs.append(cur); cur = [p[:2]]; corners.append(p[1])
    segs.append(cur)
    pts = np.vstack([_catmull(s) for s in segs]); order = np.argsort(pts[:, 1], kind="stable"); ys, xs = pts[order, 1], pts[order, 0]
    return (lambda y: np.interp(y, ys, xs)), corners

def wood_textures(tone):
    """spruce (straight fine grain along the length) and flamed maple (wavy bands across); returns the two file paths"""
    base = dict(amber=(118, 58, 22), red=(84, 32, 15))[tone]; paths = []
    rng = np.random.default_rng(7); N = 1024; yy, xx = np.mgrid[0:N, 0:N] / N
    for kind in ("spruce", "maple"):
        path = os.path.join(TEX, f"T_wood_{kind}_{tone}.jpg"); paths.append(path)
        if os.path.exists(path): continue
        if kind == "spruce":
            lines = np.interp(xx[0], np.linspace(0, 1, 140), rng.uniform(0.86, 1.06, 140)); g = np.tile(lines, (N, 1))
            g = g * (1 + 0.03 * np.sin(yy * 40 + xx * 6)); k = np.array([1.08, 1.0, 0.85])
        else:
            wav = 0.012 * np.sin(xx * 23) + 0.008 * np.sin(xx * 61 + 1.3)
            g = 0.93 + 0.11 * np.sin((yy + wav) * 2 * np.pi * 34) * (0.6 + 0.4 * np.sin(xx * 9 + yy * 3)); k = np.array([1.0, 0.94, 0.85])
        g = g + rng.normal(0, 0.012, (N, N)); img = np.clip(g[..., None] * np.array(base) * k, 0, 255).astype(np.uint8)
        Image.fromarray(img).filter(ImageFilter.GaussianBlur(0.6)).save(path, quality=92)
    return paths

def _wood_mat(name, tex, rough=0.28):
    if name in bpy.data.materials: return bpy.data.materials[name]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(tex, check_existing=True); nt.links.new(t.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough; b.inputs["Coat Weight"].default_value = 0.35; b.inputs["Coat Roughness"].default_value = 0.2
    return m

def _mesh(name, verts, faces, uvs, mats, mat_idx):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    uv = me.uv_layers.new(name="UVMap")
    for li, l in enumerate(me.loops): uv.data[li].uv = uvs[l.vertex_index]
    for m in mats: me.materials.append(m)
    for p, i in zip(me.polygons, mat_idx): p.material_index = i; p.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def string_instrument(name, body_len, rib=None, neck_len=None, origin=(0, 0, 0), axis=(0, 1, 0), up_hint=(0, 0, 1), wood=None):
    import props as PR
    L = body_len; kind = "violin" if L < 0.38 else "viola" if L < 0.5 else "cello" if L < 0.9 else "bass"; K = KINDS[kind]
    w_of, corners = half_width(OUT_BASS if kind == "bass" else OUT_VIOLIN)
    spruce_p, maple_p = wood_textures(K["tone"])
    spruce = _wood_mat("spruce_" + K["tone"], spruce_p); maple = _wood_mat("maple_" + K["tone"], maple_p, 0.3)
    ebony = PR.mat("ebony", (0.012, 0.010, 0.009), 0.5, spec=0.3); black = PR.mat("fhole_black", (0.004, 0.004, 0.004), 0.9)
    steel = PR.mat("string_steel", (0.75, 0.75, 0.76), 0.25, metal=1.0); bridge_m = PR.mat("bridge_maple", (0.72, 0.56, 0.36), 0.5)
    R, A = K["rib"] * L, K["arch"] * L
    # ---- body: arched top (z = R + arch), arched back (z = -arch), ribs between z = 0 and z = R
    ys = np.unique(np.concatenate([0.5 - 0.5 * np.cos(np.linspace(0, np.pi, 110)), corners, [c - 0.004 for c in corners], [c + 0.004 for c in corners]]))
    NX = 28; us = np.linspace(-1, 1, NX)
    def arch(u, y):  # cross arch with a recurve near the edge, long arch flattened in the middle
        cross = (0.5 + 0.5 * np.cos(np.pi * np.abs(u))) ** 0.8; return cross * np.sin(np.pi * np.clip(y, 0, 1)) ** 0.55
    V, UV, Fc, MI = [], [], [], []
    def grid(zf, flip, mi):
        base = len(V)
        for y in ys:
            w = max(float(w_of(y)), 0.003)
            for u in us:
                V.append((u * w * L, y * L, zf(u, y))); UV.append((0.5 + u * w * 1.6, y))
        for j in range(len(ys) - 1):
            for i in range(NX - 1):
                a = base + j * NX + i; q = (a, a + 1, a + NX + 1, a + NX); Fc.append(q[::-1] if flip else q); MI.append(mi)
        return base
    top = grid(lambda u, y: R + A * arch(u, y), False, 0)
    back = grid(lambda u, y: -A * 0.9 * arch(u, y), True, 1)
    for side, flip in ((0, True), (NX - 1, False)):            # ribs along both edges
        for j in range(len(ys) - 1):
            a, b, c, d = top + j * NX + side, top + (j + 1) * NX + side, back + (j + 1) * NX + side, back + j * NX + side
            Fc.append((a, b, c, d) if flip else (a, d, c, b)); MI.append(1)
    body = _mesh(name + "_body", V, Fc, UV, [spruce, maple], MI); parts = [body]
    ztop = lambda x, y: R + A * float(arch(x / max(float(w_of(y / L)), 0.003) / L, y / L))
    # ---- f-holes: dark ribbons lying on the top, on both sides of the bridge
    by = K["bridge_y"] * L
    for s in (-1, 1):
        t = np.linspace(-1, 1, 40); fy = by + t * 0.105 * L; fx = s * (0.118 * L + 0.022 * L * np.sin(t * 1.9) - 0.012 * L * t)
        wd = 0.0085 * L * (1 - 0.55 * np.abs(t) ** 2); fv, ff = [], []
        for k in range(len(t)):
            for sg in (-1, 1): x = fx[k] + sg * wd[k]; fv.append((x, fy[k], ztop(x, fy[k]) + 0.0004))
        for k in range(len(t) - 1): ff.append((2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2))
        o = _mesh(name + "_fhole", fv, ff, [(0, 0)] * len(fv), [black], [0] * len(ff)); parts.append(o)
        for k, rr in ((0, 0.016), (-1, 0.011)):                                              # round eyes at the ends
            ex = fx[k] + s * (0.006 * L if k == 0 else -0.006 * L); ey = fy[k]
            parts.append(PR.cyl(name + "_feye", rr * L, 0.0006, (ex, ey, ztop(ex, ey) + 0.0002), (0, 0, 1), black, verts=16))
    # ---- bridge, strings, fingerboard, neck, pegbox, scroll, pegs
    bh = K["bridge_h"] * L; bz = ztop(0, by) + bh; bw = 0.118 * L if kind in ("violin", "viola") else 0.12 * L
    half = [(0.50, 0.0), (0.50, 0.10), (0.37, 0.17), (0.30, 0.36), (0.43, 0.48), (0.40, 0.60), (0.44, 0.78), (0.33, 0.92), (0.16, 0.985)]
    prof = half + [(0.0, 1.0)] + [(-x, z) for x, z in reversed(half)]; t = 0.006 * L + 0.0008; z0 = bz - bh; n = len(prof)
    bv = [(x * bw, by - t / 2, z0 + z * bh) for x, z in prof] + [(x * bw, by + t / 2, z0 + z * bh) for x, z in prof]
    bf = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))] + [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
    br = _mesh(name + "_bridge", bv, bf, [(0, 0)] * (2 * n), [bridge_m], [0] * len(bf)); parts.append(br)
    for q in br.data.polygons: q.use_smooth = False
    nut = Vector((0, L + K["neck"] * L, R + bh * 0.42)); btop = Vector((0, by, bz)); sdir = (btop - nut)
    fb_len = K["fb"] * L; e = nut + sdir.normalized() * fb_len; th = 0.016 * L; drop = Vector((0, 0, -(0.004 * L + th / 2)))
    fbv, w0, w1 = [], K["fb_w0"] * L / 2, K["fb_w1"] * L / 2
    for p, w in ((nut, w0), (e, w1)):
        c = p + drop
        for dx, dz in ((-w, -th / 2), (w, -th / 2), (w * 0.9, th * 0.35), (0, th / 2), (-w * 0.9, th * 0.35)): fbv.append((c.x + dx, c.y, c.z + dz))
    ff = [(i, (i + 1) % 5, 5 + (i + 1) % 5, 5 + i) for i in range(5)] + [(4, 3, 2, 1, 0), (5, 6, 7, 8, 9)]
    parts.append(_mesh(name + "_fingerboard", fbv, ff, [(0, 0)] * 10, [ebony], [0] * len(ff)))
    heel = Vector((0, L * 0.99, R * 0.55)); nk = nut + drop + Vector((0, 0, -th * 0.9))
    parts.append(PR.cyl(name + "_neck", w0 * 0.95, (nk - heel).length, heel, nk - heel, maple, verts=20, r2=w0 * 0.85))
    parts.append(PR.box(name + "_heel", (w0 * 2.2, 0.05 * L, R * 0.95), (0, L * 0.985, R * 0.5), maple, 0.004 * L))
    parts.append(PR.box(name + "_nut", (w0 * 2, 0.008 * L, 0.008 * L), nut + Vector((0, 0.002 * L, -0.004 * L)), ebony, 0.0008 * L))
    pb_dir = Vector((0, 1, -0.22)).normalized(); pb_len = K["pegbox"] * L; pb0 = nut + Vector((0, 0.006 * L, -0.012 * L))
    pbc = pb0 + pb_dir * pb_len / 2
    pbx = PR.box(name + "_pegbox", (w0 * 2.1, pb_len, 0.055 * L), pbc, maple, 0.004 * L); pbx.rotation_euler = (math.atan2(pb_dir.z, pb_dir.y), 0, 0); parts.append(pbx)
    sc = pb0 + pb_dir * (pb_len + 0.028 * L) + Vector((0, 0, 0.012 * L))
    parts.append(PR.cyl(name + "_scroll", 0.045 * L, w0 * 2.3, sc - Vector((w0 * 1.15, 0, 0)), (1, 0, 0), maple, verts=28))
    for s in (-1, 1): parts.append(PR.cyl(name + "_scroll_eye", 0.02 * L, 0.012 * L, sc + Vector((s * w0 * 1.15, 0, 0)), (s, 0, 0), maple, verts=16))
    for i in range(4):
        s = -1 if i % 2 == 0 else 1; pc = pb0 + pb_dir * (pb_len * (0.18 + 0.2 * i))
        parts.append(PR.cyl(name + "_peg", 0.008 * L, 0.11 * L, pc - Vector((s * 0.02 * L, 0, 0)), (s, 0, 0), ebony, verts=10, r2=0.006 * L))
        parts.append(PR.sphere(name + "_peghead", 0.02 * L, pc + Vector((s * 0.095 * L, 0, 0)), ebony, scale=(0.35, 1.0, 1.25)))
    # ---- tailpiece, saddle, strings, chinrest
    tp0 = Vector((0, 0.035 * L, R + 0.012 * L)); tp1 = btop + (Vector((0, by * 0.42, R + bh * 0.55)) - btop)
    tp1 = Vector((0, by - 0.115 * L, ztop(0, by - 0.115 * L) + bh * 0.62))
    tv = []
    for p, w in ((tp0, 0.02 * L), (tp1, 0.058 * L)):
        for dx, dz in ((-w, 0), (w, 0), (w * 0.8, 0.012 * L), (-w * 0.8, 0.012 * L)): tv.append((p.x + dx, p.y, p.z + dz))
    tf = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (3, 2, 1, 0), (4, 5, 6, 7)]
    parts.append(_mesh(name + "_tailpiece", tv, tf, [(0, 0)] * 8, [ebony], [0] * 6))
    parts.append(PR.cyl(name + "_tailgut", 0.0025 * L, (tp0 - Vector((0, 0, R * 0.9))).length, (0, 0, R * 0.9), tp0 - Vector((0, 0, R * 0.9)), ebony, verts=8))
    sr = (0.0009, 0.0011, 0.0014, 0.0018) if kind in ("violin", "viola") else (0.0012, 0.0016, 0.0021, 0.0027)
    for i in range(4):
        fx = (i - 1.5) / 1.5
        a = nut + Vector((fx * w0 * 0.78, 0, 0.001)); b = btop + Vector((fx * bw * 0.27, 0, -abs(fx) ** 2 * bh * 0.06)); c = tp1 + Vector((fx * 0.04 * L, 0, 0.012 * L))
        parts.append(PR.cyl(name + "_string", sr[i], (b - a).length, a, b - a, steel, verts=6))
        parts.append(PR.cyl(name + "_string_tail", sr[i], (c - b).length, b, c - b, steel, verts=6))
        pg = pb0 + pb_dir * (pb_len * (0.18 + 0.2 * i)); parts.append(PR.cyl(name + "_string_peg", sr[i], (pg - a).length, a, pg - a, steel, verts=6))
    if K["chin"]:
        cx, cy = -0.15 * L, 0.085 * L
        parts.append(PR.sphere(name + "_chinrest", 0.1 * L, (cx, cy, ztop(cx, cy) + 0.03 * L), ebony, scale=(0.95, 0.75, 0.2)))
    else:
        parts.append(PR.cyl(name + "_endpin_collar", 0.012 * L, 0.03 * L, (0, -0.028 * L, R * 0.5), (0, 1, 0), ebony, verts=12))
    root = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(root)
    for p in parts: p.parent = root
    PR._orient(root, origin, axis, up_hint)
    return root
