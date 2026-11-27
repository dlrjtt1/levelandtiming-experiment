# Fill light for the audience area (chandeliers + wall lamps are in the photo; this lights the added 3D chairs the same way)
# py ".../cr3_fill.py" <candela of the ceiling fill>
import unreal, sys
val = float(sys.argv[1]) if len(sys.argv) > 1 else 300.0
ea = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
by = {a.get_actor_label(): a for a in ea.get_all_level_actors()}
if "CR3_AudienceFill" in by: ea.destroy_actor(by["CR3_AudienceFill"])
r = ea.spawn_actor_from_class(unreal.RectLight, unreal.Vector(600, 0, 720), unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0))
r.set_actor_label("CR3_AudienceFill")
c = r.rect_light_component
c.set_editor_property("source_width", 1000.0); c.set_editor_property("source_height", 900.0)
c.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS); c.set_intensity(val)
c.set_editor_property("use_temperature", True); c.set_editor_property("temperature", 3000.0)
c.set_mobility(unreal.ComponentMobility.MOVABLE)
unreal.log(f"[CR3] audience fill {val} cd")
