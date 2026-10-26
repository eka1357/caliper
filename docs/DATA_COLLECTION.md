# Field set: how to shoot it

38 measurement clips plus 1 or 2 street clips: 3 pilot clips, 30 with an instrument reading (the truth), 5 with nothing of known size in view, and the street study clip(s). The truth sets are never used for tuning. Recording before the building period is data collection, not building; the README says when the clips were recorded.

## Phone settings (all clips)

- 1080p at 60 fps if available, otherwise 30 fps. Landscape.
- Tripod or the phone braced on something solid. The camera must not move.
- Turn off video stabilization if your phone allows it (it warps the image).
- Lock focus and exposure (long-press on the subject).
- Clips 2 to 6 seconds long, except the street study clip. Trim dead time.
- The motion must be side to side across the frame, not toward or away from the camera.
- The scale reference must be at the same distance from the camera as the moving object. This is the most important rule: a coin closer to the camera than the object makes every number wrong.

## Pilot clips (3, kept out of the test set)

- P01: a ball dropped in front of an A4 sheet taped to a wall.
- P02: a book with a ₹10 coin beside it.
- P03: a toy rolling across the floor with nothing of known size in view.
- Save in `data/field/pilot/`. Used only to catch phone-specific problems in Phase 1.

## Set A: speed (10 clips; also validates the street study)

- Place two markers (cones, bottles, chalk lines) a measured distance apart along the road, for example 10.0 m, measured with a tape. That distance is the reference.
- A friend drives past at a steady speed: 2 runs each at 20, 30, 40 km/h, plus 4 runs at speeds of their choice.
- Record the speed from a GPS speedometer app on their phone at the moment they pass the markers. Write it down immediately.
- Film from the roadside, perpendicular to the road, with both markers in frame. Stay safe and off the road.
- Avoid showing other people's faces or readable number plates; you will use these clips in the demo.

## Set B: gravity (10 clips)

- Tape a plain white A4 sheet (297 x 210 mm) flat on a wall, on cardboard if possible.
- Drop a dense ball (cricket ball, tennis ball) from about 1.5 to 2 m, close to the wall so it falls in the same plane as the sheet.
- Truth: 9.81 m/s². Air drag over 2 m is negligible for a dense ball; note the ball type anyway.
- Vary the drop height and the ball between clips.

## Set C: size (10 clips)

- Objects from about 5 cm to 2 m: a book, a bottle, a chair, a door, a bicycle.
- Measure the dimension you will ask about with a tape (write which one: height, length, diameter).
- Put a ₹10 coin (27 mm) or an A4 sheet right beside the object, touching it if possible.
- Keep the camera still, or move it slowly.

## Set D: no reference (5 clips)

- Motion or objects with nothing of known size in view: a ball rolling on a plain floor, a toy car, a person walking far away.
- Caliper must abstain on all five. These clips prove the refusal works.

## Set S: street speed study (1 or 2 clips, for the demo)

- A real street with steady traffic, filmed side-on from the footpath for 2 to 3 minutes at 30 fps (60 fps if storage allows).
- Two marks along the road edge a measured distance apart (10 m with a tape: chalk marks, two bottles, or two lamp posts you measure between). Both marks in frame for the whole clip.
- Wide enough that vehicles cross both marks fully; high enough that number plates are not readable, or blur them later.
- Note the posted speed limit if there is one, the place, date and time.
- No truth per vehicle: this is a demonstration. Accuracy comes from set A.

## File naming and truth.csv

- Files: `data/field/A01.mp4` to `A10.mp4`, `B01` to `B10`, `C01` to `C10`, `D01` to `D05`, `S01`, `S02`; pilot clips in `data/field/pilot/`.
- Fill one row per clip in `data/field/truth.csv` the same day you shoot it.
- Keep the original files. Normalized copies are made by the pipeline.

| Column | Example |
| --- | --- |
| clip_id | A03 |
| file | A03.mp4 |
| set | speed |
| question | How fast is the white car in m/s? |
| quantity | speed |
| true_value | 8.33 |
| unit | m/s |
| instrument | GPS app reading 30 km/h |
| reference_object | two cones 10.0 m apart |
| reference_size_m | 10.0 |
| same_plane | yes |
| fps | 60 |
| resolution | 1920x1080 |
| notes | slight wind |

Unit conversions: km/h to m/s divide by 3.6. For sets D and S, leave `true_value` empty; for S put the gate distance in `reference_size_m` and the speed limit in `notes`.

## Checklist

- [ ] A4 sheet on cardboard, ₹10 coin, tape measure
- [ ] Two markers and a friend with a car and a GPS speed app for set A
- [ ] Pilot, A, B, C, D clips recorded and named
- [ ] Street clip S01 recorded with a measured 10 m gate
- [ ] truth.csv complete, units checked
- [ ] Backup copy of the clips somewhere other than your phone
