# levelandtiming-experiment

Listening-experiment page for the second pilot (BRAS CR3 hall model, AuralPaths stimuli): effects of the time and level
differences between the direct sound and the PA-reinforced sound on localisation, timbre and image stability, at three seats.

Status (2026-11-27): the page (`web/`, version pilot2-0.4) works from start to end; ten complete simulated runs with the real stimuli
passed (`tools/sim_run.py`). Seat pictures from Unreal Engine (MetaHuman performers, 3840×2160) are in `web/img/`. The receiver is in
`gas/` (set-up in `gas/README.md`, not yet deployed). Not in the repository: the stimulus audio (`web/audio/`, waiting for permission
from Aalto to host files derived from their recordings) and the source recordings (`mozart_mp3/`). To do before data collection:
deploy the receiver and enter its URL in `web/config.js`, final consent text, native check of the Japanese texts. Not made: local Rust
server for the lab runs (`server/`).

Local preview: put the FLAC files in `web/audio/online/{main,practice}/`, then double-click `start_preview.command` (macOS; serves
`web/` at http://localhost:8000/?mode=online). Add `&debug=1` for a short run with two trials per block.

## Layout
- `web/` static page. `config.js` settings, `design.js` presentation order, `app.js` screens/playback/recording,
  `i18n/{ko,ja,en}.json` texts, `design.json` condition list.
- `tools/make_design.py` builds `web/design.json` from the stimulus set's `stimuli.csv`, `manifest.json` and `practice.csv`.
- `tools/make_i18n.py` writes the three text files (edit the texts there).
- Seat and trial screens are see-through panels over a full-window picture of the hall seen from the listener's seat
  (`web/img/seat_{L,C,R}.jpg`, ear position and head direction as in the BRIRs, 94° horizontal view). See "Seat pictures".
- `tools/test_design.js` checks of the order logic (`node tools/test_design.js`).
- `tools/smoke_test.py` full run in headless Chrome, online and lab mode (`python tools/smoke_test.py`).
- `tools/results_to_csv.py` downloaded result files -> `sessions.csv`, `trials.csv`.

## Audio
`<audioBase>/main/<file>.<ext>` (45 conditions + 3 references) and `<audioBase>/practice/<file>.<ext>` (4 practice + 1 volume file).
Online: `web/audio/online/…flac` (set without headphone EQ). Lab: `/audio/…wav` from the local server (HD600 set).
For a local try-out: put or link the WAV folders as `web/audio_test/main` and `web/audio_test/practice`, run
`python -m http.server --directory web 8000`, open `http://localhost:8000/?debug=1&audiobase=audio_test&ext=wav`.

## URL options
`mode=online|lab`, `lang=ko|ja|en`, `debug=1` (2 trials per repetition, 1 s minimum listening), `order=LCR…` (fix the seat order),
`pid=…`, `audiobase=…`, `ext=wav|flac`.

## Design
3 seats (blocked; order one of 6) x 15 conditions (ITDG 0/20/40 ms x level ratio -9/-6/-3/0/+6 dB) ; centre seat twice, side seats once (config.js `repetitions`) = 60 trials, plus one hidden reference (path A only, file `<seat>_s00`) per repetition = 64 trials. A comprehension check (3 items, no sound) follows the instructions. Screening rules: `python tools/screening.py results/*.json`. Screenshots of a full Korean session: `python tools/tour.py <outdir>`. Stimuli 12.1 s (set pilot2s_*), target session under 30 min.
Reference (direct sound only) once at the start of each seat. Rating possible after 5 s of listening; replays allowed and counted.

## Seat pictures (`render/`)
Rendered offline with Blender (Cycles, `pip install bpy`), because the camera never moves.
- Hall: the BRAS CR3 model with the BRAS 360° photo (`CR3 medium room/Pictures/CR3_360panorama.jpg`) projected onto it from
  where it was taken. That point was found with `tools/fit_pano.py` (model edges matched to the photo's edges): x 7.7 m, centre
  line, 1.7 m high, i.e. 0.5 m above and 0.14 m in front of seat C's ear. The photo surfaces also light the added objects; the stage
  floor is partly diffuse so performers cast shadows on it. From L and R (4 m to the side) near objects in the photo are slightly displaced.
- Added: ground-floor audience chairs (after the BRAS seating photographs: ivory frame, blue-green velvet, seats folded), parquet,
  the two PA loudspeakers on stands (assumed; CR3 has none), the singer (standing, floor-length gown) and ten seated players
  (contrabass standing) with chairs, music stands and simple modelled instruments, at the source positions of the stimuli.
  People: Microsoft Rocketbox avatars (MIT), posed with the Rocketbox sitting/standing poses and two-bone arm IK.
- Steps: `tools/make_scene.py <config>` (writes `render/cr3.obj`, `render/scene.json`), copy the BRAS photo to
  `render/CR3_360panorama.jpg`, `render/get_assets.sh`, `python render/scene.py render/cr3_seats.blend`,
  `python render/render_seats.py render/cr3_seats.blend render/out 128 2560`, convert to JPEG in `web/img/`.
  `render/preview.py` renders any other view for checking.
- Unreal Engine route (chosen 2026-11-24 for realistic people, MetaHuman): `python render/bake_hall.py` bakes the projected photo
  into 8 hall textures (4096 px, about 150 px/m where the listeners look) and exports the hall, stage floor and parquet as FBX;
  `python render/export_ue.py` exports chairs, PA, stage props, instruments, seat cameras, performer markers and `layout_ue.csv`;
  `render/check_ue_export.py` re-imports everything and renders `ref_seat_*.png`. Work steps in UE: `render/ue/README_UE.md`. 2560 x 1440, 128 samples: about 15-20 min per seat on 2 CPU cores.

## Sources and licences of the material
Hall model, hall photograph and loudspeaker directivity: BRAS (Aspöck et al. 2020, doi:10.14279/depositonce-6726.3, CC BY-SA 4.0;
check the licence of the photographs and credit them on the page before the online version is public).
People in the seat pictures: MetaHuman (Epic Games; pictures rendered in Unreal Engine 5.8). Lower side walls (wainscot), extra seats, instruments and clothing are reconstructions (`render/side_fix.py`, `render/instruments_v3.py`, UE scripts in the experimenter's `UE_CR3_pilot2/` folder).
Avatars and poses of the earlier Blender pictures: Microsoft Rocketbox (Gonzalez-Franco et al. 2020, doi:10.3389/frvir.2020.561558, MIT licence).
Music: Aalto anechoic recordings (Pätynen, Pulkki & Lokki 2008, doi:10.3813/AAA.918104), free for academic research.
