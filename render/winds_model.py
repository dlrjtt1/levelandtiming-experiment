# Flute, clarinet, bassoon and horn with their main visible parts (joints, rings, keys, bell, bocal, coils, valves).
# Same call signatures as the placeholders in props.py. Object name prefixes (flute, clarinet, bassoon, bocal, horn_)
# are what export_ue.py groups by.
import bpy, math
import numpy as np
from mathutils import Vector

def _mesh(name, verts, faces, m):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update(); me.materials.append(m)
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def sweep(name, pts, radii, m, seg=16, scale2=1.0):
    """tube through pts (world) with a radius per point; parallel-transport frames; capped. scale2 flattens the section"""
    P = [Vector(p) for p in pts]; n = len(P); R = [radii] * n if np.isscalar(radii) else list(radii)
    T = [(P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized() for i in range(n)]
    u = T[0].orthogonal().normalized(); V, F = [], []
    for i in range(n):
        if i: 
            q = T[i - 1].rotation_difference(T[i]); u = (q @ u).normalized()
        v = T[i].cross(u)
        for k in range(seg):
            a = 2 * math.pi * k / seg; V.append(P[i] + (u * math.cos(a) + v * math.sin(a) * scale2) * R[i])
    for i in range(n - 1):
        for k in range(seg):
            a, b = i * seg + k, i * seg + (k + 1) % seg; F.append((a, b, b + seg, a + seg))
    F.append(tuple(range(seg - 1, -1, -1))); F.append(tuple(range((n - 1) * seg, n * seg)))
    return _mesh(name, V, F, m)

def _mats():
    import props as PR
    return dict(silver=PR.mat("silver", (0.85, 0.85, 0.86), 0.15, metal=1.0), black=PR.mat("grenadilla", (0.010, 0.009, 0.009), 0.5, spec=0.35),
                brass=PR.mat("brass", (0.80, 0.56, 0.20), 0.2, metal=1.0), maple=PR.mat("bassoon_wood", (0.075, 0.018, 0.008), 0.35, coat=0.3),
                ivory=PR.mat("ivory_ring", (0.85, 0.82, 0.72), 0.4), cane=PR.mat("reed_cane", (0.72, 0.58, 0.33), 0.5), hole=PR.mat("fhole_black", (0.004, 0.004, 0.004), 0.9))

def _perp(d):
    d = Vector(d).normalized(); k = Vector((0, 0, 1)) - d * d.z
    return k.normalized() if k.length > 0.05 else d.orthogonal().normalized()

def _keys(prefix, a, d, k, positions, r_tube, m, r_key=0.008, rod=True):
    import props as PR
    side = d.cross(k)
    for i, s in enumerate(positions):
        off = side * (0.004 if i % 3 == 0 else 0.0)
        PR.cyl(prefix + "_key", r_key, 0.004, a + d * s + k * (r_tube + 0.002) + off, k, m, verts=14)
    if rod and positions:
        p0 = a + d * positions[0] + k * r_tube * 0.8 + side * (r_tube + 0.003); PR.cyl(prefix + "_rod", 0.0018, positions[-1] - positions[0], p0, d, m, verts=6)

def flute(a, d):
    import props as PR
    M = _mats(); a, d = Vector(a), Vector(d).normalized(); k = _perp(d); r = 0.0095
    PR.cyl("flute_tube", r, 0.69, a - d * 0.06, d, M["silver"], verts=24)
    PR.cyl("flute_crown", r * 1.08, 0.012, a - d * 0.072, d, M["silver"], verts=24)
    lp = PR.sphere("flute_lipplate", 1.0, a + k * (r + 0.001), M["silver"]); lp.scale = (0.017, 0.012, 0.0035)
    lp.rotation_mode = 'QUATERNION'; lp.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(k)
    PR.cyl("flute_hole", 0.005, 0.0045, a + k * (r + 0.001), k, M["hole"], verts=12)
    for s in (0.155, 0.165, 0.50, 0.51): PR.cyl("flute_ring", r * 1.14, 0.008, a + d * s, d, M["silver"], verts=24)
    _keys("flute", a, d, k, [0.21, 0.235, 0.265, 0.295, 0.325, 0.355, 0.385, 0.415, 0.445, 0.475, 0.535, 0.56, 0.585, 0.608], r, M["silver"], 0.0085)

def clarinet(a, d):
    import props as PR
    M = _mats(); a, d = Vector(a), Vector(d).normalized(); k = _perp(d)
    S = [0.0, 0.02, 0.085, 0.087, 0.118, 0.15, 0.152, 0.37, 0.372, 0.60, 0.615, 0.635, 0.655, 0.672]
    Rr = [0.004, 0.0105, 0.0125, 0.0148, 0.0158, 0.0148, 0.0128, 0.0128, 0.0133, 0.0138, 0.017, 0.024, 0.033, 0.0385]
    sweep("clarinet_body", [a + d * s for s in S], Rr, M["black"], seg=24)
    for s, w in ((0.032, 0.022), (0.086, 0.006), (0.150, 0.006), (0.371, 0.008), (0.598, 0.007)):
        rr = np.interp(s, S, Rr) + 0.0012; PR.cyl("clarinet_ring", rr, w, a + d * (s - w / 2), d, M["silver"], verts=24)
    PR.cyl("clarinet_bellring", 0.0395, 0.004, a + d * 0.669, d, M["silver"], verts=28)
    _keys("clarinet", a, d, k, [0.19, 0.215, 0.24, 0.27, 0.30, 0.33, 0.41, 0.44, 0.47, 0.50, 0.53, 0.56], 0.013, M["silver"], 0.0075)
    side = d.cross(k)
    for s in (0.20, 0.46): PR.cyl("clarinet_sidekey", 0.0022, 0.09, a + d * s + side * 0.015, d, M["silver"], verts=6)

def bassoon(base, axis, mouth):
    import props as PR
    M = _mats(); b, ax, mo = Vector(base), Vector(axis).normalized(), Vector(mouth)
    front = (mo - b); front = (front - ax * front.dot(ax)).normalized(); side = ax.cross(front)
    sweep("bassoon_boot", [b - ax * 0.03, b + ax * 0.0, b + ax * 0.40, b + ax * 0.42], [0.026, 0.031, 0.030, 0.026], M["maple"], seg=24, scale2=1.5)
    PR.cyl("bassoon_bootcap", 0.033, 0.03, b - ax * 0.045, ax, M["silver"], verts=24).scale = (1, 1, 1)
    lj = b + side * 0.016
    sweep("bassoon_long", [lj + ax * 0.40, lj + ax * 1.02], [0.0195, 0.019], M["maple"], seg=20)
    sweep("bassoon_bell", [lj + ax * 1.02, lj + ax * 1.10, lj + ax * 1.28, lj + ax * 1.33], [0.0205, 0.020, 0.0225, 0.0245], M["maple"], seg=20)
    PR.cyl("bassoon_bellring", 0.0265, 0.022, lj + ax * 1.325, ax, M["ivory"], verts=24)
    for s in (0.41, 1.02): PR.cyl("bassoon_band", 0.0215, 0.012, lj + ax * s, ax, M["silver"], verts=20)
    wj = b - side * 0.02; wt = wj + ax * 0.86 - side * 0.01
    sweep("bassoon_wing", [wj + ax * 0.40, wj + ax * 0.62 - side * 0.004, wt], [0.018, 0.0185, 0.012], M["maple"], seg=18, scale2=1.25)
    PR.cyl("bassoon_wingband", 0.019, 0.012, wj + ax * 0.405, ax, M["silver"], verts=18)
    _keys("bassoon", lj, ax, front, [0.47, 0.53, 0.60, 0.68, 0.76, 0.86, 0.95], 0.0195, M["silver"], 0.011)
    _keys("bassoon_boot", b, ax, front, [0.08, 0.15, 0.22, 0.30], 0.031, M["silver"], 0.012, rod=False)
    mid = wt + ax * 0.16 + (mo - wt) * 0.35; pts = []
    for t in np.linspace(0, 1, 14):
        pts.append(wt * (1 - t) ** 2 + mid * 2 * t * (1 - t) + mo * t ** 2)
    sweep("bocal", pts[:-1], list(np.linspace(0.0045, 0.0022, 13)), M["silver"], seg=10)
    sweep("bassoon_reed", [pts[-2], mo], [0.0035, 0.0055], M["cane"], seg=8, scale2=0.35)

def horn(center, facing, bell_dir):
    import props as PR
    M = _mats(); c, n = Vector(center), Vector(facing).normalized(); bd = Vector(bell_dir).normalized()
    e1 = bd - n * bd.dot(n); e1 = e1.normalized() if e1.length > 0.05 else n.orthogonal().normalized(); e2 = n.cross(e1)
    pt = lambda ang, r, h=0.0: c + (e1 * math.cos(ang) + e2 * math.sin(ang)) * r + n * h
    # main coil: one and a half turns, slowly widening tube
    A = np.linspace(math.radians(90), math.radians(90 + 540), 70)
    sweep("horn_coil", [pt(a, 0.150 - 0.012 * i / 69, 0.022 * (i / 69 - 0.5)) for i, a in enumerate(A)], list(np.linspace(0.0065, 0.011, 70)), M["brass"], seg=12)
    # bell branch: clockwise half turn outside the coil, then out along the bell direction with the flare
    B = np.linspace(math.radians(270), math.radians(90), 26); pts = [pt(a, 0.138 + 0.034 * i / 25, 0.011 - 0.023 * i / 25) for i, a in enumerate(B)]; rad = list(np.linspace(0.011, 0.024, 26))
    end = pts[-1]
    for t, r in ((0.05, 0.028), (0.10, 0.034), (0.15, 0.045), (0.19, 0.062), (0.22, 0.088), (0.24, 0.118), (0.252, 0.150), (0.256, 0.158)):
        dirv = (e1 * (1 - t * 2.2) + bd * (t * 2.2)).normalized() if t * 2.2 < 1 else bd
        pts.append(end + e1 * min(t, 0.08) + dirv * max(0.0, t - 0.08) * 1.0 + (bd - e1) * 0.0); rad.append(r)
    sweep("horn_bell", pts, rad, M["brass"], seg=28)
    # lead pipe to the mouthpiece
    lp = [pt(math.radians(90), 0.150, -0.011), pt(math.radians(120), 0.165, -0.02), pt(math.radians(150), 0.21, -0.03), pt(math.radians(165), 0.29, -0.035), pt(math.radians(170), 0.36, -0.035)]
    sweep("horn_leadpipe", lp, [0.0065, 0.006, 0.0052, 0.0045, 0.004], M["brass"], seg=10)
    mp = lp[-1]; d = (lp[-1] - lp[-2]).normalized(); sweep("horn_mouthpiece", [mp, mp + d * 0.03, mp + d * 0.045, mp + d * 0.05], [0.004, 0.005, 0.011, 0.012], M["silver"], seg=14)
    # valve section: three rotary valves with slides and levers
    for i in range(3):
        v = c + e1 * (-0.045 + 0.045 * i) + e2 * 0.01
        PR.cyl("horn_valve", 0.019, 0.034, v - n * 0.017, n, M["brass"], verts=18); PR.cyl("horn_valvecap", 0.016, 0.006, v + n * 0.017, n, M["silver"], verts=18)
        U = [v + e2 * 0.0 - e1 * 0.012, v - e2 * (0.05 + 0.012 * i) - e1 * 0.012, v - e2 * (0.065 + 0.012 * i), v - e2 * (0.05 + 0.012 * i) + e1 * 0.012, v + e1 * 0.012]
        sweep("horn_slide", U, 0.0055, M["brass"], seg=8)
        PR.cyl("horn_lever", 0.003, 0.085, v + n * 0.02 + e2 * 0.01, (e2 * 0.9 - e1 * 0.25).normalized(), M["silver"], verts=6)
        PR.sphere("horn_paddle", 0.011, v + n * 0.02 + e2 * 0.1 - e1 * 0.024, M["silver"], scale=(1.4, 0.8, 0.25))
    PR.cyl("horn_brace", 0.003, 0.29, pt(math.radians(200), 0.145), (pt(math.radians(20), 0.145) - pt(math.radians(200), 0.145)), M["brass"], verts=6)
