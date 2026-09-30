"""Photo-derived YAUNGEL puck reference, not a manufacturing drawing. Units: mm.
Run: .venv/bin/python generate_puck.py [--parameters path/to/parameters.json]
Disc diameter measured at 59.3 mm; all other dimensions remain provisional.
"""
import argparse
import json
import math
from pathlib import Path
import cadquery as cq
from generate import box, cylinder

ROOT = Path(__file__).resolve().parent
PARAMETERS = ROOT / 'references/yaungel-led-puck/parameters.json'


def rounded_box(width, depth, height, z, radius):
    return box(-width / 2, -depth / 2, z, width, depth, height).edges('|Z').fillet(radius)


def build(p):
    assert all(isinstance(v, (int, float)) and v > 0 for v in p.values())
    r, t = p['diameter_mm'] / 2, p['body_thickness_mm']
    vr, pitch = p['vent_diameter_mm'] / 2, p['vent_pitch_diameter_mm'] / 2
    assert pitch + vr < r - 1, 'Vent must stay inside rim'
    body = cylinder(0, 0, 0, r, t).edges().fillet(min(.3, t / 4))
    vents = [(pitch * math.cos(math.radians(a)), pitch * math.sin(math.radians(a)))
             for a in (45, 135, 225, 315)]
    for x, y in vents:
        body = body.cut(cylinder(x, y, -1, vr, t + 2))
    uw, ud, uh = p['usb_width_mm'], p['usb_depth_mm'], p['usb_height_above_body_mm']
    # Photo-visible top grip ribs. Internal electronics and hidden latches omitted.
    span, rt, rh = p['rib_span_mm'], p['rib_thickness_mm'], p['rib_height_mm']
    ribs = box(-span/2, -rt/2, t, span, rt, rh).union(box(-rt/2, -span/2, t, rt, span, rh))
    ribs = ribs.cut(rounded_box(uw + 1, ud + 1, rh + 2, t - 1, 1.2))
    body = body.union(ribs)
    peg = cylinder(0, 0, -p['retaining_peg_length_mm'], p['retaining_peg_diameter_mm']/2, p['retaining_peg_length_mm'])
    # Cross-split underside retaining nub; only its visible envelope is estimated.
    for a in (0, 90):
        slot = box(-r, -.3, -p['retaining_peg_length_mm']-.1, r*2, .6, p['retaining_peg_length_mm']*.65)
        peg = peg.cut(slot.rotate((0,0,0),(0,0,1),a))
    body = body.union(peg)
    shell = rounded_box(uw, ud, uh, t, min(1.4, ud/2-.1))
    shell = shell.cut(rounded_box(uw-.7, ud-.7, uh, t+.6, min(1.05, (ud-.7)/2-.1)))
    tongue = rounded_box(uw-2, .7, uh-1.2, t+.6, .2)
    groups = {'led_packages': [], 'warm_white_emitters': [], 'red_emitters': [], 'blue_emitters': []}
    for angle in (0,90,180,270):
        for i, material in enumerate(('warm_white_emitters','red_emitters','blue_emitters','warm_white_emitters')):
            y = p['led_group_radius_mm'] + (i-1.5)*2.65
            package = box(-1.6,y-1.2,-.55,3.2,2.4,.55)
            emitter = box(-1.15,y-.85,-.7,2.3,1.7,.15)
            for name, shape in (('led_packages',package),(material,emitter)):
                groups[name].append(shape.val().rotate((0,0,0),(0,0,1),angle))
    parts = {'green_body': (body.val(),'#176c4b'), 'usb_c_shell': (shell.val(),'#b9c3c8'),
             'usb_c_tongue': (tongue.val(),'#242a2d')}
    colors = {'led_packages':'#eeeada','warm_white_emitters':'#f0d54a','red_emitters':'#e38868','blue_emitters':'#add9e6'}
    parts.update({name:(cq.Compound.makeCompound(shapes),colors[name]) for name,shapes in groups.items()})
    for name,(shape,_) in parts.items():
        assert shape.isValid(), name
    assert len(body.val().Solids()) == 1
    assert len(groups['led_packages']) == 16
    for x,y in vents:
        assert body.val().intersect(cylinder(x,y,0,vr,t).val()).Volume() < .001
    for i,(name,(shape,_)) in enumerate(parts.items()):
        for other,(second,_) in list(parts.items())[i+1:]:
            assert shape.intersect(second).Volume() < .001, (name,other)
    return parts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',type=Path,default=PARAMETERS)
    parser.add_argument('--output',type=Path,default=ROOT/'output/led-puck')
    args = parser.parse_args();p=json.loads(args.parameters.read_text());parts=build(p)
    args.output.mkdir(parents=True,exist_ok=True)
    assembly=cq.Assembly(name='YAUNGEL_puck_PROVISIONAL')
    compound=cq.Compound.makeCompound([shape for shape,_ in parts.values()])
    bounds=compound.BoundingBox()
    size=[round(v,3) for v in (bounds.xlen,bounds.ylen,bounds.zlen)]
    assert abs(size[0]-p['diameter_mm'])<.001 and abs(size[1]-p['diameter_mm'])<.001
    entries=[]
    for name,(shape,color) in parts.items():
        assembly.add(shape,name=name,color=cq.Color(*(int(color[i:i+2],16)/255 for i in (1,3,5))))
        cq.exporters.export(shape,str(args.output/f'{name}.stl'),tolerance=.08,angularTolerance=.2)
        entries.append(dict(name=name,file=f'{name}.stl',color=color))
    assembly.save(str(args.output/'yaungel_puck_reference.step'))
    cq.exporters.export(compound,str(args.output/'yaungel_puck_reference.stl'),tolerance=.05,angularTolerance=.15)
    reopened=cq.importers.importStep(str(args.output/'yaungel_puck_reference.step')).val()
    assert reopened.isValid() and len(reopened.Solids())==len(compound.Solids())
    assert abs(reopened.Volume()-compound.Volume())<.01
    report=dict(status='Photo reconstruction; disc diameter measured, other dimensions provisional',parameters=p,
                envelope_mm=size,parts=entries,solid_count=len(compound.Solids()),
                checks='Valid solids, open vents, 16 LEDs, no component overlaps, STEP round-trip passed')
    (args.output/'model.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='parts'},indent=2))


if __name__=='__main__':main()
