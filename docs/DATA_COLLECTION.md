# Field set: how to shoot it (do this before Oct 26)

35 clips total: 30 with an instrument reading (the truth) and 5 with nothing of known size in view. This set is never used for tuning.

## Phone settings (all clips)

- 1080p at 60 fps if available, otherwise 30 fps. Landscape.
- Tripod or the phone braced on something solid. The camera must not move.
- Turn off video stabilization if your phone allows it (it warps the image).
- Lock focus and exposure (long-press on the subject).
- Clips 2 to 6 seconds long. Trim dead time.
- The motion must be side to side across the frame, not toward or away from the camera.
- The scale reference must be at the same distance from the camera as the moving object. This is the most important rule: a coin closer to the camera than the object makes every number wrong.

## Set A: speed (10 clips)

- Place two markers (cones, bottles, chalk lines) a measured distance apart along the road, for example 10.0 m, measured with a tape. That distance is the reference.
- A friend drives past at a steady speed: 2 runs each at 20, 30, 40 km/h, plus 4 runs at speeds of their choice.
- Record the speed from a GPS speedometer app on their phone at the moment they pass the markers. Write it down immediately.
- Film from the roadside, perpendicular to the road, with both markers in frame. Stay safe and off the road.
- Avoid showing other people's faces or readable number plates; you will use these clips in the demo.

## Set B: gravity (10 clips)

- Tape the printed ArUco card (or a ruler) on a plain wall. Measure the card's side with a ruler and write it down.
- Drop a dense ball (cricket ball, tennis ball) from about 1.5 to 2 m, close to the wall so it falls in the same plane as the card.
- Truth: 9.81 m/s². Air drag over 2 m is negligible for a dense ball; note the ball type anyway.
- Vary the drop height and the ball between clips.

## Set C: size (10 clips)

- Objects from about 5 cm to 2 m: a book, a bottle, a chair, a door, a bicycle.
- Measure the dimension you will ask about with a tape (write which one: height, length, diameter).
- Put a ₹10 coin, an A4 sheet, or the marker card next to the object, touching it if possible.
- Move the camera slowly or keep it still; both are fine for size.

## Set D: no reference (5 clips)

- Motion or objects with nothing of known size in view: a ball rolling on a plain floor, a toy car, a person walking far away.
- Caliper must abstain on all five. These clips prove the refusal works.

## File naming and truth.csv

- Files: `data/field/A01.mp4` to `A10.mp4`, `B01` to `B10`, `C01` to `C10`, `D01` to `D05`.
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

Unit conversions: km/h to m/s divide by 3.6. For set D, leave `true_value` empty and set `quantity` to what you will ask.

## Checklist

- [ ] Marker card printed at 100% scale and measured
- [ ] Tape measure and two markers for set A
- [ ] Friend with a car and a GPS speed app
- [ ] 35 clips recorded and named
- [ ] truth.csv complete, units checked
- [ ] Backup copy of the clips somewhere other than your phone
