# sh run.sh <id> cr3_cloth.py   -> concert dress as an overlay material on each MetaHuman body (the skin material stays underneath):
#   players: black, long sleeves to the wrists, closed collar, black shoes;  singer: deep blue, sleeveless (gown skirt = Inst_Singer mesh)
# The cloth area is a mask on the pre-skinned (A-pose) position of the body mesh, with limits taken from each character's own skeleton.
# The default T-shirt and shorts (component "SkeletalMesh") are hidden.
import unreal, os, sys, csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cr3log import Log
log = Log("cloth"); HERE = os.path.dirname(os.path.abspath(__file__))
EAL = unreal.EditorAssetLibrary; MEL = unreal.MaterialEditingLibrary; AT = unreal.AssetToolsHelpers.get_asset_tools()
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
D = "/Game/CR3Cloth"; MP = D + "/M_CR3_Cloth"
def build(asset, hybrid):
    """cloth by a mask on the A-pose position. hybrid=False: masked cloth only (garment). hybrid=True: opaque, the baked skin colour where there is no cloth (body)."""
    mp = D + "/" + asset
    m = EAL.load_asset(mp) if EAL.does_asset_exist(mp) else AT.create_asset(asset, D, unreal.Material, unreal.MaterialFactoryNew())
    MEL.delete_all_material_expressions(m)
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE if hybrid else unreal.BlendMode.BLEND_MASKED); m.set_editor_property("used_with_skeletal_mesh", True)
    E = lambda cls, x, y: MEL.create_material_expression(m, cls, x, y)
    C = MEL.connect_material_expressions
    def const(v, y): c = E(unreal.MaterialExpressionConstant, -900, y); c.set_editor_property("r", v); return c
    def param(n, v, y): p = E(unreal.MaterialExpressionScalarParameter, -900, y); p.set_editor_property("parameter_name", n); p.set_editor_property("default_value", v); return p
    pos0 = E(unreal.MaterialExpressionPreSkinnedPosition, -1600, 0)        # vertex shader only
    pos = E(unreal.MaterialExpressionVertexInterpolator, -1400, 0); C(pos0, "", pos, "")
    def comp(ch, y):
        c = E(unreal.MaterialExpressionComponentMask, -1150, y)
        for k in "rgba": c.set_editor_property(k, k == ch)
        C(pos, "", c, ""); return c
    ax = E(unreal.MaterialExpressionAbs, -1000, 0); C(comp("r", 0), "", ax, "")
    z = comp("b", 200); one, zero = const(1.0, 900), const(0.0, 1000)
    def less(a, b, y):       # 1 where a < b
        i = E(unreal.MaterialExpressionIf, -600, y); C(a, "", i, "A"); C(b, "", i, "B"); C(zero, "", i, "A > B"); C(zero, "", i, "A == B"); C(one, "", i, "A < B"); return i
    def mul(a, b, y): n = E(unreal.MaterialExpressionMultiply, -350, y); C(a, "", n, "A"); C(b, "", n, "B"); return n
    hand = less(ax, param("HandX", 45.0, 0), 0)                 # not beyond the wrists
    neck = less(z, param("NeckZ", 147.0, 150), 150)             # up to the collar
    foot = less(param("FootZ", -100.0, 300), z, 300)            # above FootZ (default: shoes included)
    armx = less(param("ArmX", 1000.0, 450), ax, 450); armz = less(param("ArmZ", 95.0, 600), z, 600)   # sleeveless: no cloth where |x| > ArmX and z > ArmZ
    arm = E(unreal.MaterialExpressionOneMinus, -200, 500); C(mul(armx, armz, 500), "", arm, "")
    mask = mul(mul(hand, neck, 0), mul(foot, arm, 300), 150)
    col = E(unreal.MaterialExpressionVectorParameter, -350, -300); col.set_editor_property("parameter_name", "Color"); col.set_editor_property("default_value", unreal.LinearColor(0.0012, 0.0012, 0.0014, 1))
    rough = param("Roughness", 0.75, -150)
    if hybrid:
        tx = E(unreal.MaterialExpressionTextureSampleParameter2D, -350, -600); tx.set_editor_property("parameter_name", "Skin")
        tx.set_editor_property("texture", EAL.load_asset("/MetaHumanCharacter/Lookdev_UHM/Common/Textures/Placeholders/T_Flat_White_C_VT")); tx.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR)
        lc = E(unreal.MaterialExpressionLinearInterpolate, -100, -400); C(tx, "RGB", lc, "A"); C(col, "", lc, "B"); C(mask, "", lc, "Alpha")
        MEL.connect_material_property(lc, "", unreal.MaterialProperty.MP_BASE_COLOR)
        lr = E(unreal.MaterialExpressionLinearInterpolate, -100, -100); C(const(0.5, 1100), "", lr, "A"); C(rough, "", lr, "B"); C(mask, "", lr, "Alpha")
        MEL.connect_material_property(lr, "", unreal.MaterialProperty.MP_ROUGHNESS)
    else:
        MEL.connect_material_property(mask, "", unreal.MaterialProperty.MP_OPACITY_MASK)
        MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR); MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(const(0.08, 1200), "", unreal.MaterialProperty.MP_SPECULAR)     # matte cloth under the stage spots
    MEL.recompile_material(m); EAL.save_loaded_asset(m); log("material", asset); return m
build("M_CR3_Cloth", False)
body_parent = build("M_CR3_BodyCloth", True)
parent = EAL.load_asset(MP)
def ref_cs(body, bone):   # reference pose in component space (chain of local reference transforms)
    t = body.get_ref_pose_transform(body.get_bone_index(bone)); p = str(body.get_parent_bone(bone))
    return t if p in ("None", "") else t.multiply(ref_cs(body, p))
rows = [r["name"] for r in csv.DictReader(open(os.path.join(HERE, "layout_ue.csv"))) if not r["name"].startswith("SeatCam")]
for name in rows:
    act = [a for a in ea.get_all_level_actors() if a.get_actor_label() == name and a.get_class().get_name().startswith("BP_")]
    if not act: log(name, "missing"); continue
    comps = act[0].get_components_by_class(unreal.SkeletalMeshComponent); body = [c for c in comps if c.get_name() == "Body"][0]
    hx = abs(ref_cs(body, "hand_l").translation.x); nz = ref_cs(body, "neck_01").translation.z; sx = abs(ref_cs(body, "upperarm_l").translation.x); sz = ref_cs(body, "upperarm_l").translation.z
    mp = f"{D}/MI_Cloth_{name}"
    mi = EAL.load_asset(mp) if EAL.does_asset_exist(mp) else AT.create_asset("MI_Cloth_" + name, D, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, body_parent)
    skin = EAL.load_asset(f"/Game/MetaHumans/{name}/Unpacked/MHC_{name}/Body/Baked/T_Body_BC_VT")
    if skin: MEL.set_material_instance_texture_parameter_value(mi, "Skin", skin)
    else: log(name, "no baked skin texture")
    singer = name == "Singer"
    P = {"HandX": hx - 1.5, "NeckZ": nz + 1.0, "ArmX": (sx + 4.0) if singer else 1000.0, "ArmZ": 95.0, "FootZ": -100.0, "Roughness": 0.45 if singer else 0.8}
    for k, v in P.items(): MEL.set_material_instance_scalar_parameter_value(mi, k, v)
    MEL.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(0.004, 0.008, 0.05, 1) if singer else unreal.LinearColor(0.0012, 0.0012, 0.0014, 1))
    MEL.update_material_instance(mi); EAL.save_loaded_asset(mi)
    body.set_overlay_material(None); body.set_material(0, mi)     # overlay materials are not drawn on these bodies; replace the body material
    # the default T-shirt and shorts stay (the body mesh has no torso under them) and get the same cloth colour
    gp = f"{D}/MI_Garment_{name}"
    gi = EAL.load_asset(gp) if EAL.does_asset_exist(gp) else AT.create_asset("MI_Garment_" + name, D, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(gi, parent)
    for k, v in {"HandX": 1000.0, "NeckZ": 1000.0, "ArmX": (sx + 7.0) if singer else 1000.0, "FootZ": -1000.0, "Roughness": P["Roughness"]}.items(): MEL.set_material_instance_scalar_parameter_value(gi, k, v)
    MEL.set_material_instance_vector_parameter_value(gi, "Color", unreal.LinearColor(0.004, 0.008, 0.05, 1) if singer else unreal.LinearColor(0.0012, 0.0012, 0.0014, 1))
    MEL.update_material_instance(gi); EAL.save_loaded_asset(gi)
    for c in comps:
        if c.get_name() == "SkeletalMesh":
            c.set_visibility(True, True); c.set_editor_property("visible", True); c.set_hidden_in_game(False)
            for i in range(c.get_num_materials()): c.set_material(i, gi)
    log(name, {k: round(v, 1) for k, v in P.items()})
# the gown skirt (Inst_Singer, from cr3_instruments_v3.py) in the same cloth as the bodice. Run this script after re-importing the instruments.
for a in ea.get_all_level_actors():
    if a.get_actor_label() == "Inst_Singer":
        gp = D + "/MI_Skirt_Singer"     # own instance: no mask (the skirt mesh is in world coordinates)
        gi = EAL.load_asset(gp) if EAL.does_asset_exist(gp) else AT.create_asset("MI_Skirt_Singer", D, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(gi, parent)
        for k, v in {"HandX": 1e6, "NeckZ": 1e6, "ArmX": 1e6, "FootZ": -1e6, "Roughness": 0.45}.items(): MEL.set_material_instance_scalar_parameter_value(gi, k, v)
        MEL.set_material_instance_vector_parameter_value(gi, "Color", unreal.LinearColor(0.004, 0.008, 0.05, 1)); MEL.update_material_instance(gi); EAL.save_loaded_asset(gi)
        c = a.static_mesh_component
        for i in range(c.get_num_materials()): c.set_material(i, gi)
        log("gown skirt material set")
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True); log("done")
