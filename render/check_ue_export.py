# Re-import the exported FBX files and render from a seat with the textures shown as emission (as in UE with emissive).
import sys, os, math, bpy
HERE = os.path.dirname(os.path.abspath(__file__)); UE = os.path.join(HERE, "ue")
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.view_settings.view_transform = 'Standard'; sc.world = bpy.data.worlds.new("w")
for f in sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["CR3_hall.fbx", "CR3_stagefloor.fbx", "CR3_audiencefloor.fbx", "CR3_audience_chairs.fbx", "CR3_PA.fbx", "CR3_stage_props.fbx", "CR3_instruments.fbx", "CR3_markers_cameras.fbx"]:
    bpy.ops.import_scene.fbx(filepath=os.path.join(UE, f))
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    for m in o.data.materials:
        nt = m.node_tree; tex = next((n for n in nt.nodes if n.type == 'TEX_IMAGE'), None)
        if tex is None:
            continue
        if not tex.image.filepath or not os.path.exists(bpy.path.abspath(tex.image.filepath)):
            tex.image.filepath = os.path.join(UE, os.path.basename(tex.image.filepath))
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'); em = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(tex.outputs[0], em.inputs[0]); nt.links.new(em.outputs[0], out.inputs[0])
cams = [o for o in bpy.data.objects if o.type == 'CAMERA']
for o in cams: print("camera", o.name, [round(v, 3) for v in o.location], [round(math.degrees(v), 1) for v in o.rotation_euler], round(o.data.angle_x * 180 / math.pi, 1))
for o in bpy.data.objects:
    if o.name.startswith("MARK_Singer") or o.name.startswith("AXIS"): print(o.name, [round(v, 3) for v in o.matrix_world.translation])
bpy.data.worlds["w"].color = (0.25, 0.22, 0.2)
cd = bpy.data.cameras.new("c"); cd.sensor_fit = 'HORIZONTAL'; cd.angle = math.radians(94); c = bpy.data.objects.new("c", cd); sc.collection.objects.link(c)
c.rotation_euler = (math.radians(90), 0, math.radians(90)); sc.camera = c
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080; sc.cycles.samples = 16; sc.cycles.use_denoising = True
sun = bpy.data.lights.new("top", 'AREA'); sun.energy = 2500; sun.size = 8; so = bpy.data.objects.new("top", sun); sc.collection.objects.link(so); so.location = (3, 0, 7.5)
out = os.environ.get("REF_OUT", "/tmp/rv")
for s, y in (("L", -4), ("C", 0), ("R", 4)):
    c.location = (7.84, y, 1.23); sc.render.filepath = os.path.join(out, f"ref_seat_{s}.png"); bpy.ops.render.render(write_still=True)
