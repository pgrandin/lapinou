"""Slice the ruler white to Z=3.0 mm, then pause for black. Does not upload or print.

Requires the PrusaSlicer Flatpak, MK3 profiles, and a Hatchbox PLA profile.
Run from any directory: python3 slice_ruler.py
"""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parent
output = root / 'output/gcode/lapinou_growth_ruler_mk3_0.2mm_white_black.gcode'
output.parent.mkdir(parents=True, exist_ok=True)
change = (';AFTER_LAYER_CHANGE\n;[layer_z]\n{if layer_num == 15}\n'
          ';COLOR_CHANGE,T0,#000000\nM117 Load BLACK PLA\nM600\n'
          'G1 E0.3 F1500 ; prime after color change\n{endif}')
subprocess.run([
    'flatpak', 'run', '--command=prusa-slicer', 'com.prusa3d.PrusaSlicer',
    '--printer-profile', 'Original Prusa i3 MK3', '--material-profile', 'Hatchbox PLA',
    '--print-profile', '0.20mm QUALITY @MK3', '--perimeters', '5', '--fill-density', '20%',
    '--first-layer-height', '0.2', '--z-offset', '0', '--layer-gcode', change,
    '--center', '125,105', '--export-gcode', '--output', str(output),
    str(root / 'output/print/growth_ruler.stl')], check=True)
gcode = output.read_text()
assert len(re.findall(r'^M600$', gcode, re.M)) == 1, 'Expected one filament change'
before = gcode.split('\nM600\n')[0]
assert before.count(';LAYER_CHANGE') == 16
assert re.findall(r'^;Z:(.+)$', before, re.M)[-1] == '3.2'
assert gcode.count(';LAYER_CHANGE') == 19
print(f'Checked: white body, M600 at layer 16 / Z=3.2 mm, four black layers.\n{output}')
