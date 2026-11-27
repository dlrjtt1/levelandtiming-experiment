Scripts used inside Unreal Engine 5.8.4 for the seat pictures (copy of the experimenter's `UE_CR3_pilot2/` folder, 2026-11-25).
`init_unreal_copy.py` goes to `<project>/Content/Python/init_unreal.py`: it runs every `_cmd/*.py` queued by `sh run.sh <id> <script.py> [args]`.
Order for a fresh scene: ue_setup.py → cr3_mh_make.py (one per performer) → cr3_place_people.py → cr3_pose_all.py (twice: reset, then pose)
→ render/instruments_v3.py (Blender, needs _log/landmarks_*.json) → cr3_instruments_v3.py → cr3_pose_all.py → cr3_seq.py → cr3_cloth.py
→ cr3_sidefix.py → cr3_quality.py 4 → cr3_shot.py seat_C 784 0 123 180 0 94 (L: y 400, R: y -400; the editor window must be frontmost).

## Shell fix (2026-11-26)
`python render/shell_fix.py` writes `ue/CR3_shellfix.fbx` and `ue/T_CR3_shell.png`; copy both next to the scripts and run
`sh run.sh <id> cr3_shellfix.py`. It adds actor `CR3_ShellFix` (shell towers, rear wall, house curtains, proscenium jambs with
their own part of the hall photo; black masking on the stage-house walls) and turns Nanite off for `AudienceChairs`.
Seat pictures: `cr3_quality.py 4`, then `cr3_shot.py seat_X 784 <y> 123 180 0 94 3840 2160` (L: y 400, C: 0, R: -400), then `cr3_quality.py 2`.

## Levelled photo (2026-11-26)
The BRAS photo is rolled by about 1 degree (header edge fit, `hall.PANO_ROLL`). `hall.pano_level()` writes `pano12k_level.jpg`, which
`bake_hall.py` and `shell_fix.py` now use. After `python render/bake_hall.py 4096` copy `ue/T_CR3_hall_*.png` and `ue/T_CR3_stagefloor.png`
next to the scripts and run `sh run.sh <id> cr3_reimport_tex.py` (textures only; meshes and UVs are unchanged), then `cr3_shellfix.py`.
