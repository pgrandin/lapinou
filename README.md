# Lapinou — side-view growth timelapse planter

Python-generated CadQuery assembly for a Raspberry Pi 3B+, provisionally using Camera Module 3 **standard**. The camera, Pi and provisional LED puck references are imported from STEP. The pot provides a **50.8 mm internal diameter × 76.2 mm usable depth** (2 × 3 inches). Default framing allows a **127 mm tall × 127 mm wide** plant (5 inches), with the camera level and 250 mm from the stem plane by default. Five indexed positions provide **230, 250, 270, 290 and 310 mm** camera-to-stem distances using the same printed parts.

This is a working prototype with printed parts and a tested 1.7 mm M2 camera pilot-hole coupon. The deployed camera runs on a **Pi 2 Model B Rev 1.1 with an IMX219 sensor and USB Wi-Fi**. The CAD electronics references still show a Pi 3B+ and Camera Module 3 standard; their full envelopes and optical framing have not been updated to match the deployed hardware. The Pi reference is a simplified community model; mounting-hole positions were checked against Raspberry Pi's official drawing.

## Quick start

```bash
git clone https://github.com/pgrandin/lapinou.git
cd lapinou
python3 -m http.server 8765 --directory viewer
```

Hosted on the homelab at http://lapinou.lab.lan (redeploy with `lab deploy . --name lapinou`; see `Dockerfile`).

Open http://localhost:8765/ for the assembly or http://localhost:8765/#bed for the print layouts. Current individual STEP/STL parts and viewer assets are included. The large complete `output/assembly.step` download is generated locally with the commands below; it is not committed. `output/printed_assembly.step` contains the printed parts only.

The minimal camera daemon and Frigate example are in `pi-camera/`. It serves a changing JPEG and archives a snapshot every six hours. See `pi-camera/README.md` for installation and service commands. No camera photographs, credentials, or printer upload scripts are included.

## Files

- Generator: `generate.py`
- Complete assembly, with imported electronics: `output/assembly.step`
- Printed parts in assembly positions: `output/printed_assembly.step`
- Eleven individual parts (nine original plus two light-mount additions), each as STEP and STL in print orientation: `output/print/`
- Actual CAD preview: `output/assembly.png`
- Geometry and mesh checks: `output/validation.json`
- Reference provenance: `references/SOURCES.md`

STEP preserves editable solids and assembly positions; the Python file is the parametric source. Do not slice the complete assembly: it includes electronics references, and the parts need separate print orientations.

## Regenerate

Interactive browser viewer: http://localhost:8765/

Direct print-bed view: http://localhost:8765/#bed.

Serve the viewer locally or on your LAN:

```bash
python3 -m http.server 8765 --bind 0.0.0.0 --directory viewer
```

The viewer includes orbit/pan/zoom, side/top views, five selectable camera distances, part visibility, an exploded view and STEP/STL downloads. The STEP download is the generated default 250 mm assembly; changing the viewer selector moves the displayed assembly only. Individual printed parts work at every position. Three.js 0.180.0 and its MIT licence are stored locally in the viewer's vendor directory; no CDN is needed at runtime. The viewer shares geometry between assembly and bed modes, batches renders to one per animation frame, and uses lightweight lighting with a capped pixel ratio. Only display meshes load at startup; full-detail print STLs download on request. Electronics display meshes are simplified to approximately 15,000 triangles where needed; the original STEP imports and manufactured geometry remain full detail. The generator also writes display meshes and a manifest to `output/web/`. Relative symlinks connect those files and downloads to the viewer. For an alternative generator output directory, update those links before serving it.

Browser smoke check (regenerate the full assembly STEP first; requires Node.js):

```bash
# Run from the repository root
npm install --prefix scratch/web-test playwright
./scratch/web-test/node_modules/.bin/playwright install chromium
NODE_PATH=./scratch/web-test/node_modules node viewer/smoke.cjs
```

```bash
# Run from the repository root
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python generate_puck.py
.venv/bin/python generate.py
```

Change framing, for example:

```bash
.venv/bin/python generate.py --plant-height 150 --plant-width 100 --distance 290 --output output-150mm
```

Dimensions are millimetres. The distance argument selects an assembly position from 230/250/270/290/310; it does not change the printed parts. Changing plant height changes the mast, ruler and light-arm geometry. Supported ranges are limited to what the two-piece base and ruler placement support. Changing the camera model requires adapting its STEP transformation, mounting pattern and field-of-view calculation. It is not interchangeable merely because a replacement STEP imports successfully.

## Mechanical design

| Part | Function |
| --- | --- |
| camera_base | Rigid rail, mast foot mounting and four 12 mm tall Pi supports |
| plant_base | Matching rail, pot platform and ruler support mounting |
| catch_tray | Drainage basin wrapping around the pot ears; blind fixing holes keep the floor closed |
| pot | 2.4 mm walls, 3.2 mm floor, five 3 mm drainage holes, and two retaining ears flush with the pot bottom |
| camera_mast | Flat camera plate with four bosses and ribbon tie slots |
| camera_shoe | Low socket bolted to the existing camera-base holes; clamps the camera plate |
| ruler_support | Flat plate connecting the ruler to its mounting shoe |
| ruler_shoe | Low open channel bolted to the existing plant-base holes |
| growth_ruler | Raised 5 mm graduations and bold 50 mm labels; two screws prevent rotation |
| light_arm | New flat-printing arm behind the ruler; uses its existing two holes |
| light_cradle | New annular puck seat with three washer retainers and clear LED opening |

The two base halves use an indexed lap with **40–120 mm overlap**, depending on position. The moving upper plate has six columns of 3.3 mm clearance holes at 20 mm pitch, in two rows. The fixed lower plate has four **2.6 mm pilot holes** for M3 screws driven directly into PLA. Use all four screws, from above, through two adjacent columns. Each engraved distance label lies between its selected columns. There are no nuts on this joint. The lower plate provides 4 mm of plastic thread engagement; the upper plate clears the screw so tightening clamps the two halves together. Two short screws retain the pot on the tray; two separate screws retain the tray on the base. The camera's four M2 holes use a 21 × 12.5 mm pattern taken from the imported STEP. The Pi's four M2.5 holes use the 58 × 49 mm pattern confirmed in the manufacturer drawing.

Both mounts now separate into a flat plate and a low shoe. The camera plate seats 24 mm into a socket, with 0.4 mm clearance in front and 0.2 mm at each side. The ruler support seats in a 24 mm deep open channel with 0.4 mm clearance in front. Two M3 × 12 mm screws per shoe pass through 3.3 mm clearances and grip 2.6 mm pilots in the plate, with nominal 4 mm thread engagement and no nuts. Tightening pulls each plate onto its rear datum. The camera lens, ruler face, soil zero and base mounting-hole positions remain at their previous coordinates. The ruler shoe has a narrow rear post to leave the foot nuts accessible.

Exposed edges are softened in the Python model:

- Main base and mast-foot corners: 3 mm radii with 0.5 mm perimeter bevels.
- Pot lip: 0.8 mm fillet; tray lip: 0.6 mm fillet; pot ears have 2 mm corner radii and 0.5 mm bevels.
- Flat plates and ruler: 1–1.5 mm corner radii, with 0.3–0.5 mm edge bevels. Shoe walls have 0.3–2 mm corner radii and 0.2–0.4 mm top bevels.
- Cable slots: 0.8 mm rounded corners and 0.3 mm entry/exit bevels.

Pot ears use 3.3 mm clearance holes and the tray uses 2.6 mm blind pilots. Other mounting holes retain their specified diameters: 3.4 mm for the remaining M3 printed-part joints, 2.8 mm for Pi M2.5 screws, with nuts. The four camera bosses now use 1.7 mm pilots for M2 screws biting directly into PLA, without nuts. Camera hole spacing remains 21 × 12.5 mm; the bosses and bracket outline are unchanged. Clamping surfaces stay planar and the base lap faces remain square. The ruler has a 2 mm margin below zero and its ticks start 1 mm in from the side to keep the raised markings supported behind the perimeter bevel. Its print footprint is now 134 × 24 mm, with the same 3.0 mm body and 0.8 mm relief.

The pot, tray and ruler move as one assembly when the distance changes. The Pi and camera stay together, so adjustment does not change the ribbon route. Remove the four joint screws, move the plant half to the selected holes, and tighten on a flat surface. Hole clearance and printer tolerance limit repositioning accuracy; check focus and recalibrate pixels/mm after changing distance. Keep the distance fixed during each timelapse.

The Pi mounts on the open, elevated platform at the camera end, approximately 200 mm away from the pot. Ports remain accessible. This is an indoor open carrier, not a sealed or splashproof enclosure. No HAT or heatsink is included in the clearance checks.

The pot bottom and its two retaining ears share the same flat underside at assembly Z = 14.4 mm. The ears print directly on the bed, with 6 mm thickness and rounded, bevelled edges. The tray wall follows around both ears with 0.6 mm clearance; its footprint is 80 × 104 mm. Four internal pads and two ear pads support the pot. Two M3 × 10 mm screws enter from above through the ears at Y = ±38 mm. Two more enter from below the base at the existing Y = ±44 mm holes. Each screw engages a separate 4.2 mm deep blind pilot in the tray, with a 2.2 mm closed end. Use no washer on these four screws; nominal engagement is 4 mm. Remove the top two screws to lift out the pot. Water in place during recordings to preserve registration. Check the printed tray for leaks before mounting powered electronics and avoid filling it high enough to submerge the pot floor.

## Hardware and assembly

Use button-head screws for the recessed underside locations; check actual head dimensions against the 6.6 mm diameter × 2 mm deep recesses. No heat-set inserts or printed threads are required.

| Fastener | Qty | Location |
| --- | ---: | --- |
| M3 × 8 mm self-tapping/thread-forming screw, no nut | 4 | Adjustable base lap; screws enter from above into PLA pilots |
| M3 × 16 mm button head, nut, washer | 8 | Camera and ruler shoe feet; from below |
| M3 × 12 mm self-tapping/thread-forming screw, no nut | 4 | Two per shoe, entering from the back into the flat plate |
| M3 × 10 mm self-tapping/thread-forming screw, no nut | 4 | Two below the base into the tray; two above the pot ears into separate tray pilots |
| M3 × 20 mm, nut, thin washer | 2 | Ruler + support + new light arm; replaces the original M3 × 12 screws |
| M3 × 10 mm self-tapping/thread-forming screw, no nut | 2 | Light cradle to arm |
| M3 × 6 mm self-tapping screw, 9 mm OD M3 washer | 3 | Puck rim retention |
| M2.5 × 25 mm button head, nut, nylon washer | 4 | Pi mounting posts; from below |
| M2 × 8 mm, small nylon washer, no nut | 4 | Camera; screws enter from the camera side and bite into 1.7 mm PLA pilots |

Print `output/print/m3_pilot_coupon.stl` in the same PLA and settings as the base first. It has labelled 2.5, 2.6 and 2.7 mm pilots through a 4 mm plate, matching the threaded lap thickness. Use the actual screws to find a firm fit without splitting or stripping. The default is 2.6 mm; change `JOINT_PILOT` in `generate.py` and regenerate if needed. The lap uses 8 mm screws with an 8 mm stack and no washer; check that the actual tip does not protrude below the base. A pointed tip gives less full-thread engagement. Tighten by hand; repeated removal can wear PLA threads. The mount clamps and blind tray fixings also use this pilot size; the remaining joints use the nuts listed above.

Dry-assemble before final tightening; screw lengths assume ordinary nuts and thin washers. Tighten PCB hardware gently. Fasteners, washers and the ribbon cable are described here but are not separate CAD objects.

For an M2 screw fit check before reprinting the camera plate, run `.venv/bin/python generate_camera_fit.py` after generating the assembly. This crops all four camera bosses directly from the print-oriented STEP, preserving the 1.7 mm pilots, 21 × 12.5 mm spacing, 7 mm backing and 4.38 mm bosses. The test piece is 20.5 × 29 mm and prints back down using the same settings as the full plate. Files: `output/print/camera_mount_fit.stl` and `output/print/camera_mount_fit.step`. Check screw grip and camera alignment on this piece before printing the full mount.

1. Select the 250 mm index initially and screw the two rails together on a flat surface using all four M3 screws from above. Bolt both mounting shoes to their existing base holes, seat the small pilot-hole ends of both flat plates fully on the shoe floors, then install two M3 × 12 mm clamp screws per shoe from behind. Use no washer under these clamp heads; the 12 mm length allows 4 mm nominal engagement after the 8 mm shoe wall.
2. Fit the Pi to its mounting posts and fit the camera to the mast's four front bosses, lens pointing at the pot. Insert the four M2 × 8 screws through small nylon washers and the camera PCB into the 1.7 mm PLA pilots. Tighten gently by hand. The pilot is a starting print fit; adjust `CAMERA_PILOT` in `generate.py` if the actual screws fit too tightly or loosely. An already printed bracket with 2.3 mm through-holes can still use the original M2 × 16 screws and nuts; direct PLA engagement requires the revised camera plate.
3. Route a **15-pin to 15-pin, 1 mm pitch CSI cable** from the camera, over the mast and down its back to the Pi. A 300 mm cable is a starting length; confirm the route with string and allow relaxed bends. The 200 mm stock cable may be short. Sleeve the cable where it is loosely restrained by ties; do not pinch its conductors or sharply fold it.
4. Attach the tray from below with two M3 × 10 mm screws, then seat the pot and secure its ears from above with two more M3 × 10 mm screws. Install the ruler with the raised markings toward the camera.
5. Fill soil to the small marks **3 mm below the rim**. The ruler's zero corresponds to that height. Lock the setup before recording.

## Printing

All exported STLs are translated to the bed and oriented individually. The plant base is **220 × 158 mm** and the camera base is **215 × 150 mm**. Both fit the MK3’s 250 × 210 mm bed with their long dimension along X. Allow for your printer's actual printable area and brim requirements.

Use **Bed** in the viewer to inspect five production plates and a separate pilot coupon test. It reuses lightweight display meshes with the same print rotations generated for the STL exports, excludes electronics, and provides Orbit/Side/Top views. The plate selector shows each part's XYZ dimensions, lower-left X/Y position in millimetres, and its STL download. Each layout leaves at least 5 mm at the bed edges and 10 mm between part bounding boxes, with Z = 0 at the bed and all parts below the MK3's 210 mm height limit. The grid is 10 mm; the dashed rectangle marks the 5 mm edge margin.

| Plate | Parts and orientation |
| --- | --- |
| 1 | Camera base, base down and Pi posts up |
| 2 | Plant base, top face down to support the long lap |
| 3 | Pot and tray upright; camera and ruler support plates flat; both low shoes base down |
| 4 | Ruler only, flat with markings up for the colour change |
| 5 | New light arm flat and puck cradle shelf down; existing prints reused |
| Test | Pilot coupon; print this before the bases |

For the default 5-inch plant, the camera plate prints **158.3 × 38 × 11.38 mm**, the ruler support **96.8 × 24 × 5 mm**, and the two shoes are **30 mm high**. The third plate now tops out at the pot’s 79.4 mm instead of the previous 164.3 mm camera mast. Actual print-time savings depend on slicing settings; no time estimate is claimed. A different plant height may require rearranging the plate; the viewer flags insufficient spacing.

These are layout previews, not sliced jobs. STL downloads remain individual parts at their own origins; use the displayed positions to reproduce a plate in PrusaSlicer. Add local supports and any brims in the slicer and inspect their clearance. Print the grouped parts by layer rather than sequentially completing each object. The colour change applies only to the ruler plate.

- PLA is the starting material for the self-tapping joint. Start with a 0.4 mm nozzle, 0.2 mm layers, 4–5 walls, 5–6 top/bottom layers and 30–40% infill. These are untested starting settings.
- Pot, tray, camera base and the two low shoes print base down. The camera plate prints back down with bosses facing up; the ruler support plate prints flat. The plant base prints upside down with its broad top and upper lap on the bed; this avoids a long unsupported tongue. Its engraved distance labels face the bed. The ruler prints flat, raised markings up.
- The pot ears lie flush with the bottom and print directly on the bed. The camera bosses grow upward from the flat plate. The low shoes have small horizontal clamp holes; inspect their bridges in the slicer. Keep supports out of small mounting holes.
- Check holes with the intended fasteners; small FDM holes may need careful cleanup. Verify the ruler's spacing with a physical ruler.
- The basin is not assumed watertight just because its mesh is closed. Leak-test it separately.

### Two-colour ruler on the MK3

The ruler is one connected solid: a **3.0 mm flat body** with **0.8 mm raised ticks and numbers**, for a total thickness of **3.8 mm**. All markings start at the same print height. Ticks are 0.8 mm wide; numbers use a larger, bold font for a 0.4 mm nozzle. The exported ruler STL already lies flat with the markings facing upward; no supports are needed.

1. Load `output/print/growth_ruler.stl` into PrusaSlicer, using the MK3 single-extruder profile.
2. Use 0.20 mm layers and a 0.20 mm first layer, without a raft or variable layer height.
3. In sliced Preview, add a colour change **before layer 16, displayed Z = 3.20 mm**. The body finishes at Z = 3.00 mm; layers 16–19 print only the raised markings in the second colour.
4. Use contrasting colours of the same material, for example a white PLA body and black PLA marks. Verify the layer preview shows only ticks/numbers after the change. The MK3 will prompt for the filament swap through M600.

For the installed PrusaSlicer Flatpak with the MK3 and Hatchbox PLA profiles, `python3 slice_ruler.py` creates the same 0.20 mm white-to-black G-code and verifies that M600 appears once before layer 16. It only slices; it does not contact a printer. Machine-specific G-code is kept out of Git.

For other layer heights, select the first layer containing only markings, immediately after the 3.0 mm body. STL and STEP do not store an M600 command; add the change in the slicer before exporting G-code. Print the ruler on its own if other parts should retain their original colour.

Prusa's colour-change instructions: https://help.prusa3d.com/article/color-change_1687

## Measurement and framing

The camera looks horizontally along the base. Its lens centre is **154.3 mm above the base underside**, halfway up the intended 127 mm growth range above the 90.8 mm soil datum. The ruler body face lies at the stem plane; its markings project 0.8 mm toward the camera. The ruler sits beside the plant.

The 230 mm setting is useful for smaller plants but may crop the full 5-inch target at its near edge. Start at 250 mm for the intended mature envelope; the more distant settings add framing room.

Using the standard camera's nominal 41° vertical FoV, the model calculates about **187 mm vertical coverage** at the 250 mm stem plane, and **139 mm** at the near edge of a 127 mm deep plant envelope. This assumes full sensor framing. Cropping, capture mode, lens distortion and focus breathing can change the actual image; verify framing with a ruler in a live capture.

For repeatable apparent height, keep the stem near the calibrated plane, use a plain background and consistent lighting, and calibrate pixels/mm from the scale in the captured image. Leaves extending toward the camera appear larger; one side view measures projected growth, not true 3D size. Establish focus once and lock it for the sequence. Fixed exposure and white balance also help under controlled lighting.

Camera controls and capture details:

https://www.raspberrypi.com/documentation/computers/camera_software.html

## Validation

The generator checks mounting-hole coordinates in both imported STEP files, valid connected solids for every printed part, 220 mm bed bounds, volumetric interference between printed parts and electronics, and boundary/non-manifold edges in the eleven assembly STLs. It checks that both pot-ear undersides are flush with the bottom, that the retaining holes remain open, and that the staggered tray pilots have closed 2.2 mm ends and screw-head clearance. It also verifies the flat plates’ print heights and broad bed contact, clamp-hole alignment and surrounding material, and tool/nut access above the shoe feet. At each of the five distance settings it also checks base interference, pilot/clearance alignment, screw-head space, bearing material and minimum lap overlap. Results and reference file SHA-256 hashes are saved with each build.

These checks do not establish real-world stiffness, printer tolerance, cable flex, fastener clearance, optical calibration, thermal performance or water tightness. Verify those on the prototype.

## Bolt-on LED puck mount

The light adds **two printed parts**, `light_arm` and `light_cradle`. All nine previously printed parts retain their geometry. Plate 5 in the bed viewer contains only the new parts; the arm prints flat (153.7 × 72 × 8 mm) and the cradle prints shelf down (73.3 × 106.65 × 6.5 mm). Both fit together on the MK3 bed. The arm's small transverse pilot holes may bridge slightly; keep supports out of them.

The arm seats against the back of the existing ruler support at X = pot centre + 8 mm and uses its two existing M3 through-holes, 10 mm apart. Replace the two M3 × 12 ruler screws with **two M3 × 20**, reusing the nuts and thin washers. The combined ruler/support/arm stack is 16 mm. Fit the new arm one screw at a time to preserve the ruler position, then verify the zero mark against the soil line.

Fasten the cradle onto the arm with **two M3 × 10 self-tapping screws** through 3.3 mm clearances into 2.6 mm pilots (4 mm cradle + 6 mm engagement; no washers). Seat the puck LED-side down. Retain its rim with **three M3 × 6 screws and 9 mm OD M3 washers**, tightened gently; the washers overlap the disc edge. The cradle supports the outer 2 mm of the disc and leaves the LED packages, vent holes, centre retaining nub and top USB-C connector clear. No adhesive or changes to the old parts are required.

At the default 127 mm plant height, the LEDs are 157 mm above the soil, giving 30 mm over the intended canopy. The arm stands beside the plant and behind the ruler; the beam stays above the target plant envelope. All light components move with the pot when camera distance changes. Route the USB lead along the arm with slack at the puck so cable tension does not twist the ruler support. This is a geometric placement, not a measured light-output recommendation.

The puck is imported from `output/led-puck/yaungel_puck_reference.step`. Its outside diameter is measured at 59.3 mm; other dimensions remain provisional. The cradle pocket is 59.5 mm diameter (0.1 mm radial clearance). Disc thickness still needs measurement before finalizing the cradle. This diameter update leaves the long arm and all nine original printed parts unchanged. To revise it, update `references/yaungel-led-puck/parameters.json`, run `.venv/bin/python generate_puck.py`, then `.venv/bin/python generate.py`. The standalone puck model is a reference asset, not a printed part.

New part exports:
- `output/print/light_arm.stl`
- `output/print/light_arm.step`
- `output/print/light_cradle.stl`
- `output/print/light_cradle.step`

Assembly: http://localhost:8765/
Bed view (select plate 5): http://localhost:8765/#bed

The generator checks the reused hole alignment, cradle pilots, washer contact on both puck and cradle, flat arm orientation, plant-envelope clearance, and interference with existing geometry. These are CAD checks; mechanical stiffness and the actual puck fit remain untested.
