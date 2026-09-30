"""Crop the four camera bosses from the exported, print-oriented mount STEP.

Run after generate.py: .venv/bin/python generate_camera_fit.py
"""
import hashlib
import json

import cadquery as cq
from generate import ROOT, CAMERA_PILOT, box, hole_axes


source = ROOT / 'output/print/camera_mast.step'
mount = cq.importers.importStep(str(source)).val()
holes = {(x, y) for x, y, _ in hole_axes(mount, CAMERA_PILOT / 2)}
assert len(holes) == 4, 'Expected four camera pilot holes'
xs, ys = sorted({x for x, _ in holes}), sorted({y for _, y in holes})
assert len(xs) == len(ys) == 2
assert abs(xs[1] - xs[0] - 12.5) < .001 and abs(ys[1] - ys[0] - 21) < .001
b = mount.BoundingBox()
x, y = xs[0] - 4, ys[0] - 4
crop = box(x, y, b.zmin - 1, xs[-1] - x + 4, ys[-1] - y + 4, b.zlen + 2).val()
part = mount.intersect(crop)
assert part.isValid() and len(part.Solids()) == 1
assert len({(x, y) for x, y, _ in hole_axes(part, CAMERA_PILOT / 2)}) == 4
part = part.translate((-x, -y, -b.zmin))
for extension in ('step', 'stl'):
    cq.exporters.export(part, str(ROOT / f'output/print/camera_mount_fit.{extension}'),
                        tolerance=.05, angularTolerance=.1)
bounds = part.BoundingBox()
report = dict(source=str(source.relative_to(ROOT)), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              pilot_mm=CAMERA_PILOT, hole_pitch_mm=[12.5, 21],
              size_mm=[round(v, 3) for v in (bounds.xlen, bounds.ylen, bounds.zlen)],
              description='Unscaled crop; original 7 mm backing and 4.38 mm bosses, printed back down')
(ROOT / 'output/print/camera_mount_fit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
