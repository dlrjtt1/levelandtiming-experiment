# quick preview renders from a .blend: python preview.py file.blend name x y z yaw_deg pitch_deg hfov w h samples
import sys, math, os, bpy
f, name, x, y, z, yaw, pitch, fov, w, h, spp = sys.argv[1], sys.argv[2], *map(float, sys.argv[3:9]), int(sys.argv[9]), int(sys.argv[10]), int(sys.argv[11])
bpy.ops.wm.open_mainfile(filepath=f); sc = bpy.context.scene
cd = bpy.data.cameras.new("pc"); cd.sensor_fit = 'HORIZONTAL'; cd.angle = math.radians(fov); cd.clip_start = 0.05
c = bpy.data.objects.new("pc", cd); sc.collection.objects.link(c); c.location = (x, y, z)
c.rotation_euler = (math.radians(90 + pitch), 0, math.radians(90 + yaw))   # yaw 0 = looking along -x
sc.camera = c; sc.render.resolution_x, sc.render.resolution_y = w, h; sc.cycles.samples = spp; sc.cycles.use_denoising = True
sc.render.filepath = os.path.abspath(f"{name}.png"); bpy.ops.render.render(write_still=True)
