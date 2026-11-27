# Common scene: CR3 hall with the BRAS 360° photo projected from where it was taken. Config coordinates:
# x towards the audience, y to the right as seen from the audience, z up (same as AuralPaths).
import bpy, math, os
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
P0 = Vector((7.7, 0.0, 1.7))            # where the panorama was taken (tools/fit_pano.py)

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    sc.world = bpy.data.worlds.new("w"); sc.world.color = (0.02, 0.015, 0.01)
    return sc

def pano_nodes(nt, img, out_scale=1.0):
    n, l = nt.nodes, nt.links
    geo = n.new('ShaderNodeNewGeometry')
    sub = n.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = P0
    mul = n.new('ShaderNodeVectorMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = (-1, -1, 1)
    env = n.new('ShaderNodeTexEnvironment'); env.image = img; env.interpolation = 'Cubic'
    l.new(geo.outputs['Position'], sub.inputs[0]); l.new(sub.outputs[0], mul.inputs[0]); l.new(mul.outputs[0], env.inputs['Vector'])
    return env

def pano_material(img, name="hall_photo", diffuse_mix=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; n, l = nt.nodes, nt.links
    for x in list(n): n.remove(x)
    out = n.new('ShaderNodeOutputMaterial'); env = pano_nodes(nt, img)
    em = n.new('ShaderNodeEmission'); l.new(env.outputs['Color'], em.inputs['Color']); em.inputs['Strength'].default_value = 1.0 - diffuse_mix
    if diffuse_mix > 0:   # part diffuse so that people and objects cast shadows on it
        df = n.new('ShaderNodeBsdfDiffuse'); l.new(env.outputs['Color'], df.inputs['Color'])
        add = n.new('ShaderNodeAddShader'); l.new(em.outputs[0], add.inputs[0]); l.new(df.outputs[0], add.inputs[1]); l.new(add.outputs[0], out.inputs['Surface'])
    else:
        l.new(em.outputs[0], out.inputs['Surface'])
    return m

def pano_copy(src_name="CR3_360panorama.jpg", width=12000):
    """the BRAS photo (15000 x 7500) is put next to these scripts by the user; a 12000 px copy is used for rendering"""
    dst = os.path.join(HERE, "pano12k.jpg")
    if not os.path.exists(dst):
        from PIL import Image; Image.MAX_IMAGE_PIXELS = None
        Image.open(os.path.join(HERE, src_name)).resize((width, width // 2), Image.LANCZOS).save(dst, quality=92)
    return pano_level()

PANO_ROLL = -1.04      # degrees. The photo is not level: the lower edge of the proscenium header (horizontal in the hall) runs as
                       # atan(k cos az) + PANO_ROLL * sin(az) in it (fit rms 0.06 deg), i.e. the right side hangs low. -1.04 leaves no slope after levelling (fit of the levelled photo: 0.0).
PANO_YAW = 0.75        # degrees. In the levelled photo the stage is centred at az -0.75 (opening edges -23.65 / 22.05, shell towers,
                       # seams of the rear wall), so from the centre seat it looked shifted to the left; turned so that it is at 0.
def pano_level(src="pano12k.jpg", dst="pano12k_level.jpg"):
    """levelled and centred copy of the photo, used for everything that is projected"""
    if not os.path.exists(os.path.join(HERE, dst)):
        import numpy as np, cv2
        from PIL import Image; Image.MAX_IMAGE_PIXELS = None
        im = np.asarray(Image.open(os.path.join(HERE, src)).convert("RGB")); H, W = im.shape[:2]; out = np.empty_like(im); th = math.radians(PANO_ROLL)
        wrap = np.concatenate([im[:, -8:], im, im[:, :8]], 1)
        for y0 in range(0, H, 500):
            y1 = min(H, y0 + 500); az = ((np.arange(W) + 0.5) / W - 0.5) * 2 * np.pi - math.radians(PANO_YAW); el = (0.5 - (np.arange(y0, y1) + 0.5) / H) * np.pi
            AZ, EL = np.meshgrid(az, el); f = np.cos(EL) * np.cos(AZ); r = np.cos(EL) * np.sin(AZ); u = np.sin(EL)
            r2 = r * math.cos(th) - u * math.sin(th); u2 = r * math.sin(th) + u * math.cos(th)      # level direction -> direction in the photo
            x = ((np.arctan2(r2, f) / (2 * np.pi) + 0.5) * W - 0.5 + 8).astype(np.float32); y = ((0.5 - np.arcsin(np.clip(u2, -1, 1)) / np.pi) * H - 0.5).astype(np.float32)
            for c0 in range(0, W, 4000):      # remap is limited to 32767 px wide sources per call only for the destination; chunk for memory
                out[y0:y1, c0:c0 + 4000] = cv2.remap(wrap, x[:, c0:c0 + 4000], y[:, c0:c0 + 4000], cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
        Image.fromarray(out).save(os.path.join(HERE, dst), quality=95)
    return dst

def load_hall(pano_file=None):
    pano_file = pano_file or pano_copy()
    bpy.ops.wm.obj_import(filepath=os.path.join(HERE, "cr3.obj"), forward_axis='NEGATIVE_Z', up_axis='Y')
    hall = [o for o in bpy.context.selected_objects if o.type == 'MESH']
    for o in hall:   # bake the importer's axis conversion into the vertices: config coordinates in the mesh itself
        o.data.transform(o.matrix_world); o.matrix_world = Matrix.Identity(4)
    img = bpy.data.images.load(os.path.join(HERE, pano_file))
    photo = pano_material(img); stage_floor = pano_material(img, "stage_floor_photo", diffuse_mix=0.55)
    for o in hall:
        o.data.materials.clear(); o.data.materials.append(photo); o.data.materials.append(stage_floor)
        for p in o.data.polygons:   # horizontal stage floor at z = 1.0: partly diffuse (receives shadows)
            vs = [o.data.vertices[i].co for i in p.vertices]
            if abs(p.normal.z) > 0.99 and all(abs(v.z - 1.0) < 0.02 for v in vs) and max(v.x for v in vs) < 0.05:
                p.material_index = 1
    return hall, img

def camera(pos, h_fov_deg=94, res=(1280, 720), name="cam"):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'HORIZONTAL'; cd.angle = math.radians(h_fov_deg); cd.clip_start = 0.05
    c = bpy.data.objects.new(name, cd); sc.collection.objects.link(c)
    c.location = pos; c.rotation_euler = (math.radians(90), 0, math.radians(90))   # looks along -x, z up
    sc.camera = c; sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    return c
