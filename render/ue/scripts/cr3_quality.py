# sh run.sh <id> cr3_quality.py <0-4>   -> editor scalability level (2 while working, 4 for the seat pictures)
import unreal, sys
q = sys.argv[1]
for g in ("ViewDistance", "Shadow", "GlobalIllumination", "Reflection", "PostProcess", "Texture", "Effects", "AntiAliasing"):
    unreal.SystemLibrary.execute_console_command(None, f"sg.{g}Quality {q}")
print("quality", q)
