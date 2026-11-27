# Hall photo material: Default Lit with black base colour and the photo as emissive, so that Lumen uses the hall as a light source
import unreal
MEL, EAL = unreal.MaterialEditingLibrary, unreal.EditorAssetLibrary
m = EAL.load_asset("/Game/CR3/Materials/M_HallPhoto")
m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
for prop, val in ((unreal.MaterialProperty.MP_BASE_COLOR, 0.0), (unreal.MaterialProperty.MP_SPECULAR, 0.0), (unreal.MaterialProperty.MP_ROUGHNESS, 1.0)):
    c = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 400)
    c.set_editor_property("r", val); MEL.connect_material_property(c, "", prop)
MEL.recompile_material(m); EAL.save_loaded_asset(m)
unreal.log("[CR3] M_HallPhoto is now Default Lit + emissive")
