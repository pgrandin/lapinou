# YAUNGEL LED puck — provisional reference

A photo-derived clearance/reference model, not a manufacturer CAD asset or a functional printable light. The user measured the outside disc diameter at **59.3 mm** on 2026-09-30. All other dimensions remain estimates.

Edit `parameters.json` here and run `.venv/bin/python generate_puck.py` from the project root. The STEP, reference STL, display meshes and metadata are written to `output/led-puck/`. The STEP is imported into the planter assembly as a reference; the puck itself is not a printed part.

Coordinates: disc underside Z=0; LED faces point down; USB-C socket faces up. The disc is 59.3 mm diameter and 2.5 mm thick, the socket projects 7 mm above the disc, and the retaining nub projects 2 mm below it. Total estimated height is 11.5 mm. Four 9 mm vents lie on a 31 mm pitch circle at 45°, 135°, 225°, 315°. Grip ribs are 4.5 mm high. All these dimensions are independent parameters; changing diameter does not silently scale the connector or other features.

Visible photo features represented: green circular disc, four vent holes, cross-shaped top grips, central vertical USB-C shell/tongue, underside centre retaining nub, four groups of four LED packages. USB contacts, hidden wiring, internal electronics, mould details, real clip geometry and exact LED types/colours are omitted or schematic. The retaining nub is especially uncertain. This model is not suitable for final fit tolerances until measured.

Measurement priorities:
1. Disc thickness at its rim (outside diameter measured: 59.3 mm).
2. Overall height, and USB-C socket height above the disc.
3. Vent hole diameter and centre-to-centre distance across opposite holes.
4. Retaining nub diameter, projection and any undercut.
5. Grip-rib height/span and connector position relative to disc centre.

Source listing: https://www.amazon.com/dp/B0BHNNJ1K2
Connector and LED close-up: https://m.media-amazon.com/images/I/61aK2QrFHrL.jpg
Top grip/vent view: https://m.media-amazon.com/images/I/7129iy2fuTL.jpg
Components: https://m.media-amazon.com/images/I/71RNoWx2ldL.jpg

Local preview: http://localhost:8765/puck.html
