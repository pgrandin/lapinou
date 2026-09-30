"""Parametric timelapse planter. Millimetres. Run with .venv/bin/python generate.py.

Imported electronics remain STEP geometry; only the manufactured parts are built
here. Default framing assumes Camera Module 3 standard at full sensor FoV.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
from itertools import combinations

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface

ROOT = Path(__file__).resolve().parent
CAMERA = ROOT / "references/camera-module-3-step/Camera_module_3_std_model_simple.stp"
PI = ROOT / "references/raspberry-pi-3b-plus/raspberry-pi-3b-plus.step"
PUCK = ROOT / "output/led-puck/yaungel_puck_reference.step"
RULER_BODY = 3.0
RULER_RELIEF = 0.8
RULER_CORNER = 1.5
DISTANCE_POSITIONS = (230, 250, 270, 290, 310)
MOVING_PARTS = ("plant_base", "catch_tray", "pot", "ruler_support", "ruler_shoe", "growth_ruler", "light_arm", "light_cradle")
JOINT_BOLTS = [(x, y) for x in (140, 160) for y in (-17, 17)]
JOINT_PILOT = 2.6  # Fit coupon checks this starting diameter with the actual PLA/screw.
CAMERA_PILOT = 1.7  # Starting M2 fit in PLA; verify with the actual screw and print.
PRINT_ROTATIONS = {"plant_base": (180, 0, 0), "camera_mast": (0, -90, 0),
                   "ruler_support": (0, 90, 0), "growth_ruler": (0, 90, 0), "light_arm": (0, 90, 0)}


def box(x, y, z, dx, dy, dz):
    return cq.Workplane("XY").box(dx, dy, dz, centered=False).translate((x, y, z))


def cylinder(x, y, z, radius, height):
    return cq.Workplane("XY").circle(radius).extrude(height).translate((x, y, z))


def soft_plate(part, radius=3.0, bevel=0.5):
    """Finish an undrilled horizontal outline; mating faces remain planar."""
    return part.edges("|Z").fillet(radius).faces(">Z or <Z").edges().chamfer(bevel)


def drill_z(part, points, diameter, bottom=-1, depth=40):
    for x, y in points:
        part = part.cut(cylinder(x, y, bottom, diameter / 2, depth))
    return part


def drill_x(part, points, diameter, x, length):
    for y, z in points:
        tool = cq.Workplane("YZ", origin=(x, y, z)).circle(diameter / 2).extrude(length)
        part = part.cut(tool)
    return part


def hole_axes(shape, radius):
    """Read cylindrical mounting faces from the actual imported STEP."""
    found = set()
    for face in shape.Faces():
        if face.geomType() == "CYLINDER":
            cyl = BRepAdaptor_Surface(face.wrapped).Cylinder()
            if abs(cyl.Radius() - radius) < 0.01:
                p = cyl.Location()
                found.add(tuple(round(v, 3) for v in (p.X(), p.Y(), p.Z())))
    return found


def build_light_mount(distance, soil, plant_height):
    """Two add-on prints; reuse the unchanged ruler/support through-holes."""
    p = json.loads((PUCK.parent / "model.json").read_text())["parameters"]
    radius, disc_thickness = p["diameter_mm"] / 2, p["body_thickness_mm"]
    # Puck LEDs project 0.7 mm below its disc in the provisional STEP reference.
    puck_bottom = soil + plant_height + 30 + 0.7
    cradle_bottom = puck_bottom - 4
    beam_bottom = cradle_bottom - 8
    arm = box(distance + 8, 80, soil, 8, 24, cradle_bottom - soil)
    arm = arm.union(box(distance + 8, 32, beam_bottom, 8, 72, 8))
    arm = arm.edges("|X").fillet(2).faces(">X or <X").edges().chamfer(.4)
    arm_holes = [(92, soil + 5), (92, soil + 15)]
    arm = drill_x(arm, arm_holes, 3.4, distance + 7, 10)
    cradle_holes = [(distance + 12, 44), (distance + 12, 62)]
    arm = drill_z(arm, cradle_holes, JOINT_PILOT, cradle_bottom - 6.2, 6.3)
    # Annular shelf touches only the outer 2 mm of the disc, leaving LEDs clear.
    cradle = cylinder(distance, 0, cradle_bottom, radius + 7, 4 + disc_thickness)
    cradle = cradle.cut(cylinder(distance, 0, cradle_bottom - 1, radius - 2, 10 + disc_thickness))
    cradle = cradle.cut(cylinder(distance, 0, puck_bottom, radius + .1, disc_thickness + 1))
    cradle = cradle.edges(">Z").chamfer(.3).edges("<Z").chamfer(.4)
    cradle = cradle.union(soft_plate(box(distance + 4, 24, cradle_bottom, 16, 46, 4), 2, .3))
    cradle = drill_z(cradle, cradle_holes, 3.3, cradle_bottom - 1, 6)
    retaining_holes = []
    for angle in (0, 120, 240):
        a = math.radians(angle)
        x, y = distance + (radius + 3.5)*math.cos(a), (radius + 3.5)*math.sin(a)
        retaining_holes.append((x, y))
        cradle = drill_z(cradle, [(x, y)], JOINT_PILOT, cradle_bottom - .1, 4 + disc_thickness + .2)
    puck = cq.importers.importStep(str(PUCK)).val().translate((distance, 0, puck_bottom))
    return {"light_arm": arm, "light_cradle": cradle}, puck, dict(
        light_puck_diameter_mm=radius*2, light_puck_bottom_z_mm=puck_bottom,
        light_led_above_soil_mm=plant_height + 30, light_mature_canopy_clearance_mm=30,
        light_cradle_bottom_z_mm=cradle_bottom, light_pocket_diametral_clearance_mm=.2,
        light_retaining_holes_mm=retaining_holes, light_cradle_holes_mm=cradle_holes,
        light_mount_screws="2 x M3 x 20 at ruler; 2 x M3 x 10 cradle; 3 x M3 x 6 with 9 mm OD washers",
        light_reference_status=f"Measured {radius*2:g} mm disc diameter; other puck dimensions provisional")


def build(plant_height=127.0, distance=250.0, plant_width=127.0):
    # ponytail: one supported camera and Pi; add adapters only for confirmed hardware.
    assert 100 <= plant_height <= 220, "Supported default mast/ruler range: 100–220 mm"
    assert distance in DISTANCE_POSITIONS, f"Choose an indexed distance: {DISTANCE_POSITIONS}"
    assert 30 <= plant_width <= 140, "Plant width must be 30–140 mm to clear the ruler"
    pot_id, wall, depth, floor = 50.8, 2.4, 76.2, 3.2
    radius = pot_id / 2 + wall
    base_top, tray_floor, pot_bottom = 8.0, 10.4, 14.4
    rim = pot_bottom + floor + depth
    soil = rim - 3  # Shallow rim clearance keeps emergence visible from the side.
    camera_z = soil + plant_height / 2
    frame_height = 2 * distance * math.tan(math.radians(41 / 2))
    near_frame_height = 2 * (distance - plant_width / 2) * math.tan(math.radians(41 / 2))
    # Geometry supports every index; report optical coverage instead of forbidding
    # close settings that are useful for seedlings but can crop a mature plant.
    shift = distance - DISTANCE_POSITIONS[0]
    joint_start, joint_end = 50, 170
    upper_end = distance - 30  # Lap overlaps into the pot deck for a clean union.
    joint_holes = JOINT_BOLTS
    index_holes = [(x + shift, y) for x in range(60, 161, 20) for y in (-17, 17)]
    mast_holes = [(x, y) for x in (-33, -5) for y in (-30, 30)]
    tray_base_holes = [(distance, y) for y in (-44, 44)]
    pot_holes = [(distance, y) for y in (-38, 38)]
    ruler_foot_holes = [(distance + x, y) for x in (-12, 12) for y in (85, 99)]
    pi_holes = [(45 - z, 100 - x) for x in (3.5, 52.5) for z in (23.5, 81.5)]
    parts = {}

    # Indexed lap: four fixed lower holes and six columns of upper holes.
    # Overlap stays at least 40 mm. Full-height feet keep both halves grounded.
    a = soft_plate(box(-45, -40, 0, joint_start + 45, 150, base_top))
    # Leave the lap's clamping faces square and flat.
    lower_lap = box(joint_start, -27, 0, joint_end - joint_start, 54, 4)
    lower_lap = lower_lap.edges("|Z").fillet(2).faces("<Z").edges().chamfer(0.3)
    a = a.union(lower_lap)
    for x, y in pi_holes:
        a = a.union(cylinder(x, y, 8, 3.1, 12))
    a = drill_z(a, joint_holes, JOINT_PILOT)
    a = drill_z(a, mast_holes, 3.4)
    a = drill_z(a, pi_holes, 2.8)
    for x, y in mast_holes + pi_holes:
        a = a.cut(cylinder(x, y, -0.1, 3.3, 2.1))
    parts["camera_base"] = a

    b = box(distance - 40, -52, 0, 80, 104, base_top)
    b = b.union(box(distance - 20, 42, 0, 40, 64, base_top))
    b = soft_plate(b)
    upper_lap = box(joint_start + shift, -27, 4, upper_end - joint_start - shift, 54, 4)
    upper_lap = upper_lap.edges("|Z").fillet(2).faces(">Z").edges().chamfer(0.3)
    b = b.union(upper_lap)
    b = drill_z(b, index_holes, 3.3)
    b = drill_z(b, tray_base_holes + ruler_foot_holes, 3.4)
    for setting in DISTANCE_POSITIONS:
        # Label lies between the two selected columns at each camera distance.
        label = cq.Workplane("XY", origin=(380 - setting + shift, 0, 7.4))
        b = b.cut(label.text(str(setting), 4, 0.7, font="DejaVu Sans", kind="bold", combine=False))
    for x, y in tray_base_holes + ruler_foot_holes:
        b = b.cut(cylinder(x, y, -0.1, 3.3, 2.1))
    parts["plant_base"] = b

    tray = cylinder(distance, 0, 8, 40, 14)
    basin = cylinder(distance, 0, tray_floor, 37.6, 20)
    for sign in (-1, 1):
        # Offset the 14 x 22 mm pot ears by 0.6 mm inside and 3 mm outside.
        outer = box(distance - 10, 24 if sign > 0 else -52, 8, 20, 28, 14)
        inner = box(distance - 7.6, 26.4 if sign > 0 else -49.6, tray_floor, 15.2, 23.2, 20)
        tray = tray.union(outer.edges("|Z").fillet(5))
        basin = basin.union(inner.edges("|Z").fillet(2.6))
    tray = tray.cut(basin)
    tray = tray.edges(">Z").fillet(0.6).edges("<Z").chamfer(0.5)
    for angle in (45, 135, 225, 315):
        x = distance + 21 * math.cos(math.radians(angle))
        y = 21 * math.sin(math.radians(angle))
        tray = tray.union(cylinder(x, y, tray_floor, 3.5, 4))
    for sign in (-1, 1):
        pad = box(distance - 5.5, 33 if sign > 0 else -49, 8, 11, 16, pot_bottom - 8)
        tray = tray.union(pad.edges("|Z").fillet(2))
    # Staggered blind pilots leave 2.2 mm closed ends and 3.4 mm between bores.
    # M3 x 10 below: 6 mm of base + 4 mm engagement. Above: 6 mm ear + 4 mm.
    tray = drill_z(tray, tray_base_holes, JOINT_PILOT, 7.9, 4.3)
    tray = drill_z(tray, pot_holes, JOINT_PILOT, pot_bottom - 4.2, 4.3)
    parts["catch_tray"] = tray

    pot = cylinder(distance, 0, pot_bottom, radius, depth + floor)
    pot = pot.cut(cylinder(distance, 0, pot_bottom + floor, pot_id / 2, depth + 1))
    pot = pot.edges(">Z").fillet(0.8).edges("<Z").chamfer(0.5)
    ear_bottom = pot_bottom
    for y in (-49, 27):
        pot = pot.union(soft_plate(box(distance - 7, y, ear_bottom, 14, 22, 6), 2, 0.5))
    pot = drill_z(pot, pot_holes, 3.3)
    drains = [(distance, 0)] + [(distance + x, y) for x, y in ((15, 0), (-15, 0), (0, 15), (0, -15))]
    pot = drill_z(pot, drains, 3, pot_bottom - 0.1, floor + 0.2)
    # Three short notches on the inside identify the intended soil level.
    for angle in (0, 120, 240):
        notch = box(distance + pot_id / 2 - 0.3, -2, soil - 0.4, 0.8, 4, 0.8)
        pot = pot.cut(notch.rotate((distance, 0, 0), (distance, 0, 1), angle))
    parts["pot"] = pot

    # Flat camera plate seats 24 mm into a low shoe. Screws pull its back onto
    # the original X datum; 0.4 mm front clearance and 0.2 mm end clearance.
    shoe = soft_plate(box(-41, -36, 8, 45, 72, 6))
    socket = box(-27, -23, 13.5, 23, 46, 24.5)
    socket = socket.edges("|Z").fillet(2).edges(">Z").chamfer(0.4)
    shoe = shoe.union(socket).cut(box(-19, -19.2, 14, 7.4, 38.4, 25))
    shoe = drill_z(shoe, mast_holes, 3.4)
    mast_clamp = [(-10, 26), (10, 26)]
    shoe = drill_x(shoe, mast_clamp, 3.3, -28, 9.1)
    parts["camera_shoe"] = shoe
    mast = box(-19, -19, 14, 7, 38, camera_z + 18 - 14)
    mast = mast.edges("|Z").fillet(1.5).edges(">Z").chamfer(0.5)
    mast = drill_x(mast, mast_clamp, JOINT_PILOT, -20, 9)
    cam_holes = [(y - 12.5, x + camera_z - 14.4) for x in (2, 14.5) for y in (2, 23)]
    for y, z in cam_holes:
        boss = cq.Workplane("YZ", origin=(-12, y, z)).circle(2.3).extrude(4.38)
        mast = mast.union(boss)
    mast = drill_x(mast, cam_holes, CAMERA_PILOT, -20, 14)
    # Cable ties go around a ribbon sleeve, never tighten directly on bare FFC.
    slot_heights = (55, 110, camera_z + 13)
    for z in slot_heights:
        mast = mast.cut(box(-20, -11, z, 9, 22, 3).edges("|X").fillet(0.8))
    slot_edges = []
    for edge in mast.val().Edges():
        eb = edge.BoundingBox()
        if eb.xlen < 1e-5 and any(abs(eb.xmin - x) < 1e-5 for x in (-19, -12)):
            if any(eb.zmin >= z - 1e-5 and eb.zmax <= z + 3 + 1e-5 for z in slot_heights):
                slot_edges.append(edge)
    assert slot_edges, "Cable slot edges not found"
    mast = mast.newObject(slot_edges).chamfer(0.3)
    parts["camera_mast"] = mast

    # Flat ruler support clamps against a rear datum; an open channel avoids
    # widening its existing foot and keeps the base mounting holes accessible.
    foot = soft_plate(box(distance - 17, 79, 8, 34, 26, 6), 2, 0.4)
    for x, width, y, span in ((distance - 3, 5.6, 81, 22), (distance + 8, 8, 88.5, 7)):
        # Narrow rear post leaves both existing foot nuts accessible from above.
        socket_wall = box(x, y, 13.5, width, span, 24.5)
        socket_wall = socket_wall.edges("|Z").fillet(0.3).edges(">Z").chamfer(0.2)
        foot = foot.union(socket_wall)
    ruler_clamp = [(92, 22), (92, 32)]
    foot = drill_z(foot, ruler_foot_holes, 3.4)
    foot = drill_x(foot, ruler_clamp, 3.3, distance + 7.9, 9)
    parts["ruler_shoe"] = foot
    support = box(distance + 3, 80, 14, 5, 24, soil + 20 - 14)
    support = support.edges("|Z").fillet(1).edges(">Z").chamfer(0.4)
    support = drill_x(support, ruler_clamp, JOINT_PILOT, distance + 2, 7)
    ruler_mount = [(92, soil + 5), (92, soil + 15)]
    support = drill_x(support, ruler_mount, 3.4, distance - 1, 12)
    parts["ruler_support"] = support
    # Ruler body front is coplanar with the plant centre, facing the camera.
    # A 2 mm lower margin keeps the zero tick fully supported behind the bevel.
    ruler = box(distance, 80, soil - 2, RULER_BODY, 24, plant_height + 7)
    ruler = ruler.edges("|X").fillet(RULER_CORNER)
    ruler = ruler.faces(">X or <X").edges().chamfer(0.3)
    ruler = drill_x(ruler, ruler_mount, 3.4, distance - 1, 6)
    for mm in range(0, int(plant_height) + 1, 5):
        length = 10 if mm % 10 == 0 else 5
        ruler = ruler.union(box(distance - RULER_RELIEF, 81, soil + mm,
                                RULER_RELIEF + 0.01, length, 0.8))
    # All markings rise from one plane, allowing one layer-based filament swap.
    for mm in range(0, int(plant_height) + 1, 50):
        label = cq.Workplane(cq.Plane(origin=(distance + 0.01, 96, soil + mm + 2),
                                      xDir=(0, -1, 0), normal=(-1, 0, 0)))
        ruler = ruler.union(label.text(str(mm), 4.5, RULER_RELIEF + 0.01,
                                       font="DejaVu Sans", kind="bold", combine=False))
    parts["growth_ruler"] = ruler

    light_parts, puck, light_dimensions = build_light_mount(distance, soil, plant_height)
    parts.update(light_parts)

    print("Importing camera STEP…", flush=True)
    camera_raw = cq.importers.importStep(str(CAMERA)).val()
    pcb = max(camera_raw.Solids(), key=lambda s: s.Volume())
    measured_camera_holes = {(p[0], p[1]) for p in hole_axes(pcb, 1.1)}
    assert measured_camera_holes == {(x, y) for x in (2, 14.5) for y in (2, 23)}
    camera = camera_raw.rotate((0, 0, 0), (0, 1, 0), -90).translate((-7.65, -12.5, camera_z - 14.4))
    print("Importing Pi 3B+ STEP…", flush=True)
    pi_raw = cq.importers.importStep(str(PI)).val()
    measured_pi_holes = {(p[0], p[2]) for p in hole_axes(pi_raw, 1.375)}
    assert measured_pi_holes == {(x, z) for x in (3.5, 52.5) for z in (23.5, 81.5)}
    pi = (pi_raw.rotate((0, 0, 0), (1, 0, 0), 90)
          .rotate((0, 0, 0), (0, 0, 1), -90).translate((45, 100, 20)))
    parts = {name: part.val() for name, part in parts.items()}
    electronics = {"camera_module_3_standard_REFERENCE": camera, "pi_3b_plus_REFERENCE": pi, "led_puck_REFERENCE": puck}
    dimensions = dict(pot_inside_diameter_mm=pot_id, pot_usable_depth_mm=depth,
                      pot_wall_mm=wall, rim_z_mm=rim, soil_z_mm=soil,
                      plant_height_mm=plant_height, plant_width_mm=plant_width, lens_to_stem_mm=distance,
                      lens_z_mm=camera_z, nominal_vertical_frame_mm=frame_height,
                      near_edge_vertical_frame_mm=near_frame_height,
                      pi_mount_pitch_mm=[58, 49], camera_mount_pitch_mm=[21, 12.5], camera_mount_pilot_mm=CAMERA_PILOT,
                      ruler_body_mm=RULER_BODY, ruler_relief_mm=RULER_RELIEF,
                      ruler_color_change_after_z_mm=RULER_BODY,
                      distance_positions_mm=list(DISTANCE_POSITIONS),
                      moving_parts=[*MOVING_PARTS, "led_puck_REFERENCE"],
                      joint_overlap_mm=joint_end - joint_start - shift,
                      joint_pilot_mm=JOINT_PILOT, joint_clearance_mm=3.3,
                      mount_socket_depth_mm=24, mount_front_clearance_mm=0.4,
                      pot_ear_bottom_mm=ear_bottom, pot_retaining_screw_length_mm=10,
                      tray_ear_clearance_mm=0.6, tray_mount_pilot_depth_mm=4.2,
                      full_growth_fits_with_margin=near_frame_height >= plant_height + 10)
    dimensions.update(light_dimensions)
    return parts, electronics, dimensions


def print_pose(name, shape, place_on_bed=True):
    for axis, degrees in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), PRINT_ROTATIONS.get(name, (0, 0, 0))):
        if degrees:
            shape = shape.rotate((0, 0, 0), axis, degrees)
    if not place_on_bed:
        return shape
    b = shape.BoundingBox()
    return shape.translate((-b.xmin, -b.ymin, -b.zmin))


def validate(parts, electronics, dimensions):
    report = {"parts": {}, "intersections_mm3": {}, "status": "CAD checks only; physical fit untested"}
    for name, part in parts.items():
        assert part.isValid(), f"Invalid BRep: {name}"
        assert len(part.Solids()) == 1, f"Disconnected solids: {name}"
        pose = print_pose(name, part)
        b = pose.BoundingBox()
        assert max(b.xlen, b.ylen) <= 220.01, f"Exceeds 220 mm bed: {name}"
        report["parts"][name] = dict(volume_mm3=round(part.Volume(), 2),
                                    print_size_mm=[round(v, 2) for v in (b.xlen, b.ylen, b.zlen)])
        if name == "pot":
            ear_faces = [face for face in part.Faces()
                         if face.geomType() == "PLANE" and abs(face.Center().y) > 29
                         and face.normalAt().z < -.999]
            assert len(ear_faces) == 2, "Missing flat ear undersides"
            assert all(abs(face.Center().z - part.BoundingBox().zmin) < 1e-5
                       for face in ear_faces), "Pot ears are above the bed"
            for y in (-38, 38):
                assert part.intersect(cylinder(dimensions["lens_to_stem_mm"], y, 0, 1.65, 100).val()).Volume() < .01
            report["parts"][name]["ears_flush_with_bottom"] = True
            report["parts"][name]["ear_bed_contact_area_mm2"] = round(sum(f.Area() for f in ear_faces), 2)
        if name == "catch_tray":
            d = dimensions["lens_to_stem_mm"]
            for sign in (-1, 1):
                for y, bottom in ((44 * sign, 8), (38 * sign, 10.2)):
                    pilot = cylinder(d, y, bottom, JOINT_PILOT / 2, 4.2).val()
                    assert part.intersect(pilot).Volume() < .01, "Blocked tray pilot"
                for y, bottom in ((44 * sign, 12.2), (38 * sign, 8)):
                    cap = cylinder(d, y, bottom, 2.5, 2.2).val()
                    assert part.intersect(cap).Volume() > cap.Volume() * .999, "Open tray fixing hole"
                head = cylinder(d, 38 * sign, 20.4, 3.2, 3).val()
                assert part.intersect(head).Volume() < .01, "Pot screw head hits tray rim"
            report["parts"][name]["blind_pilot_depth_mm"] = 4.2
            report["parts"][name]["closed_pilot_end_mm"] = 2.2
        if name == "camera_mast":
            expected = {(round(y-12.5, 3), round(x+dimensions["lens_z_mm"]-14.4, 3))
                        for x in (2, 14.5) for y in (2, 23)}
            measured = {(p[1], p[2]) for p in hole_axes(part, CAMERA_PILOT/2)}
            assert measured == expected, "Camera M2 pilots must match the four PCB holes"
            report["parts"][name]["camera_mount_pilot_mm"] = CAMERA_PILOT
        if name in ("camera_mast", "ruler_support"):
            expected_height = 11.38 if name == "camera_mast" else 5
            assert abs(b.zlen - expected_height) < 1e-5, f"Mount not flat: {name}"
            first_layer = pose.intersect(box(-1, -1, 0.05, b.xlen + 2, b.ylen + 2, 0.1).val()).Volume() / 0.1
            assert first_layer > b.xlen * b.ylen * 0.75, f"Insufficient flat contact: {name}"
            report["parts"][name]["flat_contact_area_mm2"] = round(first_layer, 2)
        if name == "growth_ruler":
            assert abs(b.zlen - RULER_BODY - RULER_RELIEF) < 1e-5
            # The first colour is a plate with only small perimeter edge relief.
            body = pose.intersect(box(-1, -1, 0, b.xlen + 2, b.ylen + 2, RULER_BODY).val())
            expected = (b.xlen * b.ylen - 2 * math.pi * 1.7**2) * RULER_BODY
            assert expected * 0.97 < body.Volume() <= expected + 0.01, "Excessive ruler body removal"
            # Equal sections just above the swap and near the top verify constant relief.
            areas = [pose.intersect(box(-1, -1, z, b.xlen + 2, b.ylen + 2, 0.1).val()).Volume() / 0.1
                     for z in (RULER_BODY + 0.05, RULER_BODY + RULER_RELIEF - 0.15)]
            assert 0 < areas[0] < b.xlen * b.ylen / 2
            assert abs(areas[0] - areas[1]) < 0.01, "Markings do not share a relief height"
            report["parts"][name]["color_change_after_z_mm"] = RULER_BODY
            report["parts"][name]["raised_marking_area_mm2"] = round(areas[0], 2)
    print("Checking bolt-on light mount and puck retention…", flush=True)
    d, soil = dimensions["lens_to_stem_mm"], dimensions["soil_z_mm"]
    bottom = dimensions["light_cradle_bottom_z_mm"]
    puck_bottom = dimensions["light_puck_bottom_z_mm"]
    puck = electronics["led_puck_REFERENCE"]
    top = puck_bottom + json.loads((PUCK.parent / "model.json").read_text())["parameters"]["body_thickness_mm"]
    for z in (soil + 5, soil + 15):
        shaft = cq.Workplane("YZ", origin=(d - 1, 92, z)).circle(1.7).extrude(18).val()
        for name in ("growth_ruler", "ruler_support", "light_arm"):
            assert parts[name].intersect(shaft).Volume() < .01, "Existing ruler hole blocked"
        nut_access = cq.Workplane("YZ", origin=(d + 16, 92, z)).circle(3.5).extrude(8).val()
        assert parts["light_arm"].intersect(nut_access).Volume() < .01
    for x,y in dimensions["light_cradle_holes_mm"]:
        assert parts["light_arm"].intersect(cylinder(x,y,bottom-6.2,JOINT_PILOT/2,6.2).val()).Volume() < .01
        assert parts["light_cradle"].intersect(cylinder(x,y,bottom,1.65,4).val()).Volume() < .01
        bearing = cylinder(x,y,bottom-.5,2.5,.3).cut(cylinder(x,y,bottom-.5,1.5,.3)).val()
        assert parts["light_arm"].intersect(bearing).Volume() > bearing.Volume()*.999
        assert puck.intersect(cylinder(x,y,bottom+4,3.2,5).val()).Volume() < .01
    for x,y in dimensions["light_retaining_holes_mm"]:
        assert parts["light_cradle"].intersect(cylinder(x,y,bottom,JOINT_PILOT/2,top-bottom).val()).Volume() < .01
        washer = cylinder(x,y,top,4.5,.5).cut(cylinder(x,y,top,1.6,.5)).val()
        assert puck.intersect(washer).Volume() < .01
        contact = washer.translate((0,0,-.5))
        assert puck.intersect(contact).Volume() > .01, "Washer does not overlap puck edge"
        assert parts["light_cradle"].intersect(contact).Volume() > .01
    arm_pose = print_pose("light_arm",parts["light_arm"])
    ab = arm_pose.BoundingBox()
    first_layer = arm_pose.intersect(box(-1,-1,.05,ab.xlen+2,ab.ylen+2,.1).val()).Volume()/.1
    assert first_layer > 3000 and abs(ab.zlen-8)<.001, "Light arm must print flat"
    # Full target canopy stays below the beam and inside the side-mounted tower.
    plant_envelope = box(d-dimensions["plant_width_mm"]/2,-dimensions["plant_width_mm"]/2,
                         soil,dimensions["plant_width_mm"],dimensions["plant_width_mm"],dimensions["plant_height_mm"]).val()
    for shape in (parts["light_arm"],parts["light_cradle"],puck):
        assert shape.intersect(plant_envelope).Volume() < .01
    report["light_mount"] = dict(new_printed_parts=2, existing_parts_to_reprint=0,
                                arm_flat_contact_area_mm2=round(first_layer,2),
                                existing_ruler_holes_aligned=True, puck_edge_retention_checked=True,
                                mature_canopy_clearance_mm=30, provisional_puck=True)
    print("Checking mount seating, clamp holes and foot nut access…", flush=True)
    d = dimensions["lens_to_stem_mm"]
    for shoe, panel, holes, entry_x, direction, seat_x in (
        ("camera_shoe", "camera_mast", [(-10, 26), (10, 26)], -27, 1, -19),
        ("ruler_shoe", "ruler_support", [(92, 22), (92, 32)], d + 16, -1, d + 8),
    ):
        for y, z in holes:
            clearance = cq.Workplane("YZ", origin=(entry_x, y, z)).circle(1.65).extrude(direction * 8).val()
            pilot = cq.Workplane("YZ", origin=(seat_x, y, z)).circle(JOINT_PILOT / 2).extrude(direction * 4).val()
            head = cq.Workplane("YZ", origin=(entry_x, y, z)).circle(3.2).extrude(-direction * 3).val()
            assert parts[shoe].intersect(clearance).Volume() < .01
            assert parts[panel].intersect(pilot).Volume() < .01
            assert parts[shoe].intersect(head).Volume() < .01
            ring = (cq.Workplane("YZ", origin=(seat_x + direction * 0.5, y, z))
                    .circle(2.5).circle(1.5).extrude(direction * 3).val())
            assert parts[panel].intersect(ring).Volume() > ring.Volume() * .999
        nut_points = ([(x, y) for x in (-33, -5) for y in (-30, 30)] if shoe == "camera_shoe"
                      else [(d + x, y) for x in (-12, 12) for y in (85, 99)])
        for x, y in nut_points:
            assert parts[shoe].intersect(cylinder(x, y, 14, 3.5, 30).val()).Volume() < .01
    report["flat_mounts"] = dict(socket_depth_mm=24, clamp_screws="4 x M3 x 12 mm into PLA",
                               pilot_mm=JOINT_PILOT, thread_engagement_mm=4,
                               aligned_pilots=True, foot_nut_access=True)
    for (a, sa), (b, sb) in combinations({**parts, **electronics}.items(), 2):
        if a in electronics and b in electronics:
            continue
        ba, bb = sa.BoundingBox(), sb.BoundingBox()
        if any(getattr(ba, axis + "max") <= getattr(bb, axis + "min") + 1e-5 or
               getattr(bb, axis + "max") <= getattr(ba, axis + "min") + 1e-5 for axis in "xyz"):
            continue
        volume = sa.intersect(sb).Volume()
        report["intersections_mm3"][f"{a} / {b}"] = round(volume, 6)
        assert volume < 0.01, f"Interference {a} / {b}: {volume:.3f} mm³"
    report["distance_settings"] = []
    for distance in DISTANCE_POSITIONS:
        print(f"Checking indexed distance {distance} mm…", flush=True)
        shift = distance - dimensions["lens_to_stem_mm"]
        plant_base = parts["plant_base"].translate((shift, 0, 0))
        overlap = 170 - (50 + distance - DISTANCE_POSITIONS[0])
        assert overlap >= 40
        assert parts["camera_base"].intersect(plant_base).Volume() < 0.01
        for x, y in JOINT_BOLTS:
            # Upper plate clears the screw; lower plate intentionally grips its thread.
            for shape, radius in ((parts["camera_base"], JOINT_PILOT / 2), (plant_base, 1.65)):
                shaft = cylinder(x, y, -1, radius, 14).val()
                assert shape.intersect(shaft).Volume() < 0.01, f"Bolt blocked at {distance} mm"
                head = cylinder(x, y, 8, 3.2, 3).val()
                assert shape.intersect(head).Volume() < 0.01, f"Head blocked at {distance} mm"
            # Full material ring around each bolt proves it stays away from edges
            # and other holes, with a real bearing surface on both lap plates.
            for shape, z in ((parts["camera_base"], 2.2), (plant_base, 4.2)):
                ring = cylinder(x, y, z, 3.5, 0.2).cut(cylinder(x, y, z, 1.8, 0.2)).val()
                assert shape.intersect(ring).Volume() >= ring.Volume() * 0.999
        # All wet-side parts and the scale move rigidly together. Their mutual
        # clearances stay unchanged; check their separation from fixed hardware.
        for name in MOVING_PARTS[1:]:
            moved = parts[name].translate((shift, 0, 0)).BoundingBox()
            assert moved.xmin > max(shape.BoundingBox().xmax for shape in
                                    (parts["camera_base"], parts["camera_mast"],
                                     *(s for n, s in electronics.items() if n != "led_puck_REFERENCE")))
        near_height = 2 * (distance - dimensions["plant_width_mm"] / 2) * math.tan(math.radians(20.5))
        report["distance_settings"].append(dict(distance_mm=distance, overlap_mm=overlap,
            four_pilots_and_clearances_aligned=True, bearing_rings_supported=True,
            near_edge_vertical_frame_mm=round(near_height, 2),
            full_growth_fits_with_margin=near_height >= dimensions["plant_height_mm"] + 10))
    return report


def preview(parts, electronics, dimensions, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import numpy as np

    fig = plt.figure(figsize=(15, 9), facecolor="#f5f3ec")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#f5f3ec")
    palette = {"pot": "#c8794b", "catch_tray": "#ae643b", "growth_ruler": "#f3d77c"}
    meshes, colors = [], []
    for name, shape in {**parts, **electronics}.items():
        vertices, triangles = shape.tessellate(0.35, 0.25)
        v = np.array([p.toTuple() for p in vertices])
        mesh = v[np.array(triangles)]
        color = palette.get(name, "#386775" if name in parts else "#48864f")
        # One collection sorts triangles across parts, including hollow pots.
        # Absolute lighting handles mixed winding in third-party STEP references.
        normals = np.cross(mesh[:, 1] - mesh[:, 0], mesh[:, 2] - mesh[:, 0])
        normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-12)
        light = np.array([-0.5, -0.7, 1.0])
        light /= np.linalg.norm(light)
        brightness = 0.6 + 0.4 * np.abs(normals @ light)
        meshes.append(mesh)
        colors.append(brightness[:, None] * np.array(to_rgb(color)))
    ax.add_collection3d(Poly3DCollection(np.concatenate(meshes), facecolors=np.concatenate(colors),
                                       linewidth=0, edgecolors="none", zsort="average"))
    d, soil, h = dimensions["lens_to_stem_mm"], dimensions["soil_z_mm"], dimensions["plant_height_mm"]
    # Dotted rectangle is a framing reference, not an imported/manufactured object.
    ax.plot([d]*5, [-dimensions["plant_width_mm"]/2, dimensions["plant_width_mm"]/2, dimensions["plant_width_mm"]/2, -dimensions["plant_width_mm"]/2, -dimensions["plant_width_mm"]/2], [soil, soil, soil+h, soil+h, soil],
            color="#669766", linestyle="--", linewidth=1.5)
    ax.plot([0, d], [0, 0], [dimensions["lens_z_mm"]]*2, "--", color="#bb7139", linewidth=1)
    ax.set(xlim=(-55, d+50), ylim=(-65, 115), zlim=(0, soil+h+55))
    ax.set_box_aspect((d+105, 180, soil+h+20))
    ax.view_init(elev=25, azim=-58)
    ax.set_axis_off()
    fig.suptitle("LAPINOU  /  growth timelapse planter", fontsize=22, color="#193841", x=.08, ha="left")
    fig.text(.08,.89, f"Pi 3B+ + Camera Module 3 standard • {d:g} mm baseline • {h:g} mm growth range", color="#48636a", fontsize=12)
    fig.text(.08,.06, "Actual CAD geometry · dotted outline = plant reference plane · electronics imported from STEP\nPrototype — verify small mounts and drainage before the full print", color="#48636a", fontsize=11)
    fig.savefig(output / "assembly.png", dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def print_bounds(name, shape):
    # Ignore cached tessellation: mesh deflection otherwise inflates bed bounds.
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    bounds = Bnd_Box()
    BRepBndLib.AddOptimal_s(print_pose(name, shape, place_on_bed=False).wrapped, bounds, False)
    values = bounds.Get()
    return [list(values[:3]), list(values[3:])]


def export_viewer(parts, electronics, dimensions, output):
    """Lightweight display meshes; editable source assets remain STEP."""
    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    entries = []
    colors = {"pot": "#c47c54", "catch_tray": "#a96543", "growth_ruler": "#d5b65d"}
    for name, shape in {**parts, **electronics}.items():
        path = assets / f"{name}.stl"
        round_container = name in ("pot", "catch_tray")
        cq.exporters.export(shape, str(path), tolerance=0.15 if round_container else 0.3,
                            angularTolerance=0.2 if round_container else 0.65)
        if name in electronics:
            # Display-only simplification; original STEP references stay intact.
            import vtk
            reader = vtk.vtkSTLReader()
            reader.SetFileName(str(path))
            reader.Update()
            count = reader.GetOutput().GetNumberOfCells()
            if count > 15000:
                decimate = vtk.vtkQuadricDecimation()
                decimate.SetInputConnection(reader.GetOutputPort())
                decimate.SetTargetReduction(1 - 15000 / count)
                writer = vtk.vtkSTLWriter()
                writer.SetFileName(str(path))
                writer.SetFileTypeToBinary()
                writer.SetInputConnection(decimate.GetOutputPort())
                writer.Write()
        entry = dict(name=name, file=f"assets/{name}.stl",
                            color=colors.get(name, "#386775" if name in parts else "#428658"),
                            printable=name in parts,
                            print_rotation_deg=PRINT_ROTATIONS.get(name, (0, 0, 0)))
        if name in parts:
            entry["print_bounds_mm"] = print_bounds(name, shape)
        entries.append(entry)
    (output / "model.json").write_text(json.dumps(dict(parts=entries, dimensions=dimensions), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plant-height", type=float, default=127)
    parser.add_argument("--distance", type=int, choices=DISTANCE_POSITIONS, default=250)
    parser.add_argument("--plant-width", type=float, default=127)
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    parts, electronics, dimensions = build(args.plant_height, args.distance, args.plant_width)
    json.dumps(dimensions)  # Catch invalid metadata before lengthy geometric checks.
    print("Checking solid validity, print envelopes and assembly interference…", flush=True)
    report = validate(parts, electronics, dimensions)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    (out / "print").mkdir(exist_ok=True)
    # Same 4 mm threaded depth as the joint, with three pilot choices.
    coupon = soft_plate(box(0, 0, 0, 48, 18, 4), 2, 0.3)
    for x, diameter in ((8, 2.5), (24, 2.6), (40, 2.7)):
        coupon = drill_z(coupon, [(x, 6)], diameter)
        label = cq.Workplane("XY", origin=(x, 13, 3.4)).text(str(diameter), 3, 0.7, font="DejaVu Sans", combine=False)
        coupon = coupon.cut(label)
    assert coupon.val().isValid() and len(coupon.val().Solids()) == 1
    for extension in ("step", "stl"):
        cq.exporters.export(coupon, str(out / "print" / f"m3_pilot_coupon.{extension}"))
    (out / "web" / "assets").mkdir(parents=True, exist_ok=True)
    cq.exporters.export(coupon, str(out / "web" / "assets" / "m3_pilot_coupon.stl"),
                        tolerance=0.3, angularTolerance=0.65)
    assembly = cq.Assembly(name="lapinou")
    for name, shape in parts.items():
        color = cq.Color(0.74, 0.40, 0.24) if name in ("pot", "catch_tray") else cq.Color(0.18, 0.39, 0.44)
        assembly.add(shape, name=name, color=color)
        posed = print_pose(name, shape)
        cq.exporters.export(posed, str(out / "print" / f"{name}.step"))
        cq.exporters.export(posed, str(out / "print" / f"{name}.stl"), tolerance=0.05, angularTolerance=0.1)
        # Validate exported meshes as well as their analytic source solids.
        import vtk
        reader = vtk.vtkSTLReader()
        reader.SetFileName(str(out / "print" / f"{name}.stl"))
        reader.MergingOn()
        reader.Update()
        edges = vtk.vtkFeatureEdges()
        edges.SetInputConnection(reader.GetOutputPort())
        edges.BoundaryEdgesOn()
        edges.NonManifoldEdgesOn()
        edges.FeatureEdgesOff()
        edges.ManifoldEdgesOff()
        edges.Update()
        assert edges.GetOutput().GetNumberOfCells() == 0, f"Non-manifold STL: {name}"
        report["parts"][name]["stl_boundary_or_nonmanifold_edges"] = 0
    assembly.save(str(out / "printed_assembly.step"))
    for name, shape in electronics.items():
        assembly.add(shape, name=name, color=cq.Color(0.15, 0.48, 0.25))
    print("Exporting complete STEP assembly…", flush=True)
    assembly.save(str(out / "assembly.step"))
    report["dimensions"] = dimensions
    report["reference_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (PI, CAMERA, PUCK)}
    (out / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Rendering CAD preview…", flush=True)
    preview(parts, electronics, dimensions, out)
    export_viewer(parts, electronics, dimensions, out / "web")
    print(f"Done: {out.resolve()}", flush=True)


if __name__ == "__main__":
    main()
