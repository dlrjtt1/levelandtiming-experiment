"""Find where the BRAS CR3 360° photo was taken, by matching the model's edges to the photo's edges.
usage: python tools/fit_pano.py <CR3_360panorama.jpg> [overlay.jpg]
Prints the best camera position (three.js coords: x, y up, z = -config y) and yaw, and optionally writes the photo with
the model's edges drawn on it. Result used in make_scene.py: config (7.7, 0.0, 1.7), yaw 0."""
import itertools, os, sys
from collections import defaultdict
import cv2, numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
OBJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "render", "cr3.obj")
V, F = [], []
for l in open(OBJ):
    if l.startswith("v "): V.append(tuple(map(float, l.split()[1:4])))
    elif l.startswith("f "): F.append([int(s.split("/")[0]) - 1 for s in l.split()[1:]])
V = np.array(V)
def normal(f):
    P = V[f]; best = np.zeros(3)
    for k in range(1, len(f) - 1):
        n = np.cross(P[k] - P[0], P[k + 1] - P[0])
        if np.linalg.norm(n) > np.linalg.norm(best): best = n
    return best / (np.linalg.norm(best) + 1e-12)
en = defaultdict(list)
for f in F:
    n = normal(f)
    for a, b in zip(f, f[1:] + f[:1]): en[tuple(sorted((a, b)))].append(n)
edges = [e for e, ns in en.items() if len(ns) == 1 or min(abs(np.dot(ns[0], x)) for x in ns[1:]) < 0.9]   # creases and borders
def proj(p, c, yaw, W, H):  # equirectangular: centre column = -x (stage), right = -z
    d = p - c; az = np.arctan2(-d[..., 2], -d[..., 0]) + yaw; el = np.arctan2(d[..., 1], np.hypot(d[..., 0], d[..., 2]))
    return (W / 2 + az / (2 * np.pi) * W) % W, H / 2 - el / np.pi * H
W, H = 4000, 2000
img = np.array(Image.open(sys.argv[1]).convert("L").resize((W, H), Image.LANCZOS))
dt = cv2.distanceTransform(255 - cv2.Canny(cv2.GaussianBlur(img, (5, 5), 1.5), 40, 120), cv2.DIST_L2, 3)
ts = np.linspace(0, 1, 30)[:, None]; S = np.concatenate([V[a] * (1 - ts) + V[b] * ts for a, b in edges])
def cost(c, yaw):
    u, v = proj(S, np.array(c), yaw, W, H); m = (v > 500) & (v < 1500)       # walls, balconies, stage
    return float(np.mean(np.minimum(dt[v[m].astype(int), u[m].astype(int)], 15)))
best = min(((cost((x, y, z), np.radians(yw)), x, y, z, yw) for x, y, z, yw in itertools.product(
    np.arange(7.4, 8.25, 0.1), np.arange(1.4, 1.95, 0.05), np.arange(-0.3, 0.31, 0.1), np.arange(-1.5, 1.6, 0.5))))
print("mean edge distance %.2f px at x %.2f, height %.2f, z %.2f, yaw %.1f deg" % best)
if len(sys.argv) > 2:
    from PIL import ImageDraw
    im = Image.open(sys.argv[1]).convert("RGB").resize((W, H)); dr = ImageDraw.Draw(im); c = np.array(best[1:4])
    for a, b in edges:
        u, v = proj(V[a] * (1 - np.linspace(0, 1, 40)[:, None]) + V[b] * np.linspace(0, 1, 40)[:, None], c, np.radians(best[4]), W, H)
        for k in range(39):
            if abs(u[k] - u[k + 1]) < W / 2: dr.line([(u[k], v[k]), (u[k + 1], v[k + 1])], fill=(255, 0, 0), width=2)
    im.save(sys.argv[2], quality=85)
