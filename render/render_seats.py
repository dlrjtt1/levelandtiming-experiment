# Final seat views: camera at each seat's ear position facing the BRIR head direction (-x), 94° horizontal view.
# usage: python render_seats.py cr3_seats.blend outdir [samples] [width]
import sys, math, os, json, bpy
blend, out = sys.argv[1], sys.argv[2]; spp = int(sys.argv[3]) if len(sys.argv) > 3 else 128; W = int(sys.argv[4]) if len(sys.argv) > 4 else 2560
seats = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "scene.json")))["seats"]
for s in "CLR":
    bpy.ops.wm.open_mainfile(filepath=blend); sc = bpy.context.scene
    cd = bpy.data.cameras.new("seat"); cd.sensor_fit = 'HORIZONTAL'; cd.angle = math.radians(94); cd.clip_start = 0.05
    c = bpy.data.objects.new("seat", cd); sc.collection.objects.link(c); c.location = seats[s]
    c.rotation_euler = (math.radians(90), 0, math.radians(90)); sc.camera = c
    sc.render.resolution_x, sc.render.resolution_y = W, W * 9 // 16; sc.cycles.samples = spp; sc.cycles.use_denoising = True
    sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = os.path.join(out, f"seat_{s}.png")
    bpy.ops.render.render(write_still=True); print("done", s, flush=True)
