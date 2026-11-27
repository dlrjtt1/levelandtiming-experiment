# lighter editor while working (final renders set their own quality): medium scalability, capped texture pool
import unreal
for c in ("sg.ViewDistanceQuality 2", "sg.ShadowQuality 2", "sg.GlobalIlluminationQuality 2", "sg.ReflectionQuality 2",
          "sg.PostProcessQuality 2", "sg.TextureQuality 2", "sg.EffectsQuality 2", "sg.FoliageQuality 2", "r.Streaming.PoolSize 3000"):
    unreal.SystemLibrary.execute_console_command(None, c)
print("editor scalability medium, texture pool 3000 MB")
