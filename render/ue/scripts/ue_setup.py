# CR3 pilot 2: scene setup in Unreal Editor 5.8 (run from the Cmd box:  py "<path>/ue_setup.py")
# 1) report positions (axis, cameras, markers)  2) hall photo materials (unlit, emissive)  3) lights + exposure  4) seat cameras
import unreal, math
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
EAL, MEL = unreal.EditorAssetLibrary, unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors = ea.get_all_level_actors()
by = {a.get_actor_label(): a for a in actors}
log = lambda *a: unreal.log("[CR3] " + " ".join(str(x) for x in a))

# ---- 1) report
for name in sorted(by):
    if name.startswith(("AXIS", "SeatCam", "MARK_", "CR3_hall", "PA_")):
        a = by[name]; o, e = a.get_actor_bounds(False)
        log(name, type(a).__name__, "loc", a.get_actor_location(), "rot", a.get_actor_rotation(), "bounds centre", o, "extent", e)

# ---- 2) hall photo: one unlit master material, 8 instances with the baked textures
FOLDER = "/Game/CR3/Materials"
assets = EAL.list_assets("/Game", recursive=True, include_folder=False)
def find_asset(name):
    for p in assets:
        if p.split("/")[-1].split(".")[0] == name: return EAL.load_asset(p)
    return None
master = EAL.load_asset(FOLDER + "/M_HallPhoto") if EAL.does_asset_exist(FOLDER + "/M_HallPhoto") else None
if master is None:
    master = tools.create_asset("M_HallPhoto", FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    master.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    tex = MEL.create_material_expression(master, unreal.MaterialExpressionTextureSampleParameter2D, -400, 0)
    tex.set_editor_property("parameter_name", "Photo")
    gain = MEL.create_material_expression(master, unreal.MaterialExpressionScalarParameter, -400, 250)
    gain.set_editor_property("parameter_name", "Gain"); gain.set_editor_property("default_value", 1.0)
    mul = MEL.create_material_expression(master, unreal.MaterialExpressionMultiply, -150, 0)
    MEL.connect_material_expressions(tex, "RGB", mul, "A"); MEL.connect_material_expressions(gain, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(master); EAL.save_loaded_asset(master)
    log("created M_HallPhoto")
for i in range(8):
    a = by.get(f"CR3_hall_{i}"); t = find_asset(f"T_CR3_hall_{i}")
    if a is None or t is None: log("missing", i, a, t); continue
    path = f"{FOLDER}/MI_HallPhoto_{i}"
    mi = EAL.load_asset(path) if EAL.does_asset_exist(path) else tools.create_asset(f"MI_HallPhoto_{i}", FOLDER, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, master)
    MEL.set_material_instance_texture_parameter_value(mi, "Photo", t)
    EAL.save_loaded_asset(mi)
    a.static_mesh_component.set_material(0, mi)
    log("hall", i, "->", mi.get_name())

# ---- 3) lights and exposure (positions: README_UE.md section 4)
def spawn(cls, label, loc, aim=None):
    old = by.get(label)
    if old: ea.destroy_actor(old)
    rot = unreal.MathLibrary.find_look_at_rotation(loc, aim) if aim else unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0)
    a = ea.spawn_actor_from_class(cls, loc, rot); a.set_actor_label(label); return a
for k, y in enumerate((300, 100, -100, -300)):
    s = spawn(unreal.SpotLight, f"CR3_Spot_{k+1}", unreal.Vector(120, y, 660), unreal.Vector(-500, y * 0.55, 150))
    c = s.spot_light_component
    c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS); c.set_intensity(4000.0)
    c.set_editor_property("use_temperature", True); c.set_editor_property("temperature", 3200.0)
    c.set_editor_property("inner_cone_angle", 15.0); c.set_editor_property("outer_cone_angle", 21.0)
    c.set_editor_property("source_radius", 25.0); c.set_mobility(unreal.ComponentMobility.MOVABLE)
r = spawn(unreal.RectLight, "CR3_StageTop", unreal.Vector(-550, 0, 680))
r.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0), False)   # facing down
rc = r.rect_light_component
rc.set_editor_property("source_width", 600.0); rc.set_editor_property("source_height", 600.0)
rc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS); rc.set_intensity(800.0)
rc.set_editor_property("use_temperature", True); rc.set_editor_property("temperature", 3600.0)
pp = spawn(unreal.PostProcessVolume, "CR3_Exposure", unreal.Vector(0, 0, 300))
pp.set_editor_property("unbound", True)
st = pp.get_editor_property("settings")
for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
             ("override_auto_exposure_apply_physical_camera_exposure", True), ("auto_exposure_apply_physical_camera_exposure", False),
             ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.0)):
    try: st.set_editor_property(k, v)
    except Exception as ex: log("pp", k, ex)
pp.set_editor_property("settings", st)
log("lights + exposure done")

# ---- 4) seat cameras: filmback 36 x 20.25 mm, focal 16.79 mm (94° horizontal), yaw 180, pitch/roll 0
for s, y in (("L", 400.0), ("C", 0.0), ("R", -400.0)):
    a = by.get(f"SeatCam_{s}")
    if a is None: log("no camera", s); continue
    log("camera before", s, type(a).__name__, a.get_actor_location(), a.get_actor_rotation())
    a.set_actor_location(unreal.Vector(784.0, y, 123.0), False, False); a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=0.0, yaw=180.0), False)
    cc = a.get_cine_camera_component() if hasattr(a, "get_cine_camera_component") else None
    if cc:
        fb = cc.get_editor_property("filmback"); fb.set_editor_property("sensor_width", 36.0); fb.set_editor_property("sensor_height", 20.25)
        cc.set_editor_property("filmback", fb); cc.set_editor_property("current_focal_length", 16.79)
        log("camera", s, "cine fov", cc.get_horizontal_field_of_view())
    else:
        cam = a.get_component_by_class(unreal.CameraComponent)
        cam.set_editor_property("field_of_view", 94.0); cam.set_editor_property("aspect_ratio", 16.0 / 9.0)
        log("camera", s, "plain fov 94")
log("setup finished")
