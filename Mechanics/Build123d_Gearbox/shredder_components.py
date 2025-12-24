import math
from build123d import *

# =============================================================================
# 1. Carbide Insert Model
# =============================================================================
def carbide_insert_ccmt060204():
    """
    Generates a CCMT060204 Carbide Insert.
    Dimensions derived from standard or the provided SCAD file.
    """
    # Parameters for CCMT 06 02 04
    # l = 6.4mm (Cutting edge length)
    # s = 2.38mm (Thickness)
    # r = 0.4mm (Corner radius)
    # d1 = 2.8mm (Hole diameter) ? SCAD says 2.5/3-48
    # 80 degree diamond shape

    thickness = 2.38

    # Create the Diamond Profile
    # Side length ~ 6.35mm
    # Angle 80 deg.
    # We can model this as a Polygon or build it from lines.

    # SCAD logic:
    # linear_extrude(height=2.38, scale=...) of a square with minkowski...
    # Let's simplify: 80-degree rhombus with rounded corners.

    side_len = 6.35
    angle = 80

    with BuildPart() as insert:
        with BuildSketch() as profile:
            # Create a Rhombus/Diamond
            # Using RegularPolygon doesn't give 80deg easily.
            # Let's draw a trapezoid/rhombus manually.

            # Half-angles: 40 deg and 50 deg? No, 80 and 100.
            # 80 deg corner.

            # Coordinates for a rhombus with 80 deg angle at origin (or centered)
            # Let's Center it.

            # Width/Height calc
            # If side=6.35, angle=80.
            # We can use RegularPolygon(side_count=4) and scale non-uniformly? No, that changes lengths.

            # Let's use points.
            #   P1
            #  /  \
            # P0--P2
            #  \  /
            #   P3

            # Actually, standard ISO inserts (CCMT) are defined by inscribed circle (IC).
            # C = 80 deg Rhombic.
            # C06 -> IC = 6.35mm (1/4") ?
            # Wait, 06 refers to edge length usually for C-shape.
            # Let's stick to the SCAD approximation:
            # Square (rotated) + Minkowski circle.

            # SCAD: square(size=6.35-0.4) ... minkowski circle(r=0.4)
            # This results in a square with rounded corners.
            # WAIT. CCMT is a DIAMOND (Rhombus). SCAD file says "C - 80deg diamond shape" but uses `square()`?
            # `linear_extrude(scale=...)` with `translate([2.35*tan(7), 0, 0])` suggests it's making the relief angle (7 deg)
            # But `square` implies 90 degrees.
            # CCMT is indeed a Diamond. The SCAD might be using a transformation or I am misreading it.
            # "square(size=6.35-0.4)" -> This makes a rounded square (CNMG style? No C is diamond).
            # C-shape insert is 80-degree rhombus.
            # Maybe the SCAD is an approximation or for a generic square insert?
            # "C - 80deg diamond shape" comment vs `square()` code.
            # I will trust the "CCMT" designation (Diamond) over the possibly buggy SCAD code if they conflict.
            # I will build a proper 80-degree Rhombus.

            # Points for 80-deg Rhombus
            # Center at 0,0
            # Diagonals align with X/Y.
            # angle/2 = 40 deg.
            # hypotenuse = side_len = 6.35
            # x = 6.35 * cos(40)
            # y = 6.35 * sin(40)
            # Wait, no.

            # Let's use `RegularPolygon(4)` (Square) and `scale` Y?
            # A square has diagonals equal.
            # A rhombus has diagonals D1, D2.
            # tan(40) = (D2/2) / (D1/2) = D2/D1.
            # So if we scale Y by tan(40) ~ 0.839 relative to X?
            # Square rotated 45 deg has diagonals on axes.

            with Locations((0,0)):
                RegularPolygon(radius=6.35/math.sqrt(2), side_count=4) # Square with side ~6.35
                # Rotate to align diagonals with axes? RegularPolygon(4) is already aligned?
                # RegularPolygon(4) is a square with flat sides up/down usually? Or corners?
                # Build123d RegularPolygon(4) usually has a flat on bottom?
                # Let's just create points.

            # 80 deg rhombus.
            # Side = 6.35.
            # D_long = 2 * 6.35 * cos(40) = 9.72
            # D_short = 2 * 6.35 * sin(40) = 8.16

            # Pts: (D_long/2, 0), (0, D_short/2), (-D_long/2, 0), (0, -D_short/2)
            pts = [
                (4.86, 0),
                (0, 4.08),
                (-4.86, 0),
                (0, -4.08)
            ]
            with BuildLine():
                Polyline(pts, close=True)
            make_face()
            fillet(profile.vertices(), radius=0.4)

        # Extrude with Relief Angle (7 deg)
        # Taper Extrude?
        # C implies 7 deg relief.
        # Positive insert: bottom is smaller than top.
        # So we extrude Tapered?
        # extrude(taper=7) ?
        extrude(amount=thickness, taper=7)

        # Screw Hole (Countersunk)
        with Locations((0,0, thickness)): # Top face
            CounterSinkHole(radius=2.8/2, counter_sink_radius=4.5/2, depth=thickness)

    return insert.part

# =============================================================================
# 2. Shredder Drum Disk
# =============================================================================
def drum_disk(
    diameter=150.0,
    thickness=25.0, # 254mm / 10 disks ~ 25.4mm
    hex_shaft_size=25.0, # Flat-to-Flat
    num_teeth=2
):
    """
    Generates a single slice of the shredder drum.
    """
    with BuildPart() as disk:
        Cylinder(radius=diameter/2, height=thickness)

        # Hex Bore
        # Hexagon with flat-to-flat = hex_shaft_size
        # Radius (Center to Corner) = size / sqrt(3) * 2 ?
        # Flat-to-Flat (s) = 2 * r_inscribed
        # r_inscribed = s/2 = 12.5
        # r_circumscribed (Radius for RegularPolygon) = r_inscribed / cos(30) = (s/2) / (sqrt(3)/2) = s / sqrt(3)
        # 25 / 1.732 = 14.43

        hex_radius = hex_shaft_size / math.sqrt(3)
        with Locations((0,0)):
            with BuildSketch():
                RegularPolygon(radius=hex_radius, side_count=6)
            extrude(amount=thickness, mode=Mode.SUBTRACT)

        # Tooth Pockets
        # We cut out a recess for the Insert + backing.
        # For a shredder, we usually have a "Tooth" protruding, or the drum is the tooth?
        # Standard design: The disk IS the cutter. It has "Hooks".
        # The carbide insert is mounted on the leading face of the hook.

        # Let's model a "Hook" profile.
        # We start with a Cylinder, but we carve out "Gullets" to form teeth.

        # Hook depth
        tooth_depth = 20.0

        insert = carbide_insert_ccmt060204()

        for i in range(num_teeth):
            angle = i * (360.0 / num_teeth)

            # 1. Cut the Gullet (The space in front of the tooth)
            # A simple cylinder cut or box cut
            with Locations(Rotation(0,0, angle)):
                with Locations((diameter/2, 15, 0)): # Offset position
                    Cylinder(radius=25, height=thickness, mode=Mode.SUBTRACT)

            # 2. Mount the Insert
            # On the "Face" created by the gullet.
            # Position is approximate for this demo.
            with Locations(Rotation(0,0, angle)):
                 with Locations((diameter/2 - 5, -5, thickness/2)): # Position on the hook tip
                     with Locations(Rotation(90, -90, 0)): # Orient correctly (facing forward)
                         # We subtract the insert shape (pocket)
                         add(insert, mode=Mode.SUBTRACT)

                         # Add screw hole clearance if needed (simplified)

    return disk.part

# =============================================================================
# 3. Fixed Knife (Counter Blade)
# =============================================================================
def fixed_knife(
    length=254.0,
    drum_diameter=150.0,
    width=50.0,
    thickness=20.0
):
    """
    A simple rectangular bar with a profile matching the drum?
    Usually it's a comb shape.
    For this demo, we'll make a simple bar.
    """
    with BuildPart() as knife:
        Box(length, width, thickness)

        # If we had the full drum profile, we would cut "Teeth" into this knife
        # to interleave with the drum spacers.
        # Assuming the drum has spacers between disks?
        # Or if the disks are packed tight, the knife is just a straight bar
        # (simpler, but less efficient shearing).
        # Let's assume a straight bar for the MVP.

    return knife.part

if __name__ == "__main__":
    print("Generating Shredder Components...")

    # 1. Insert
    ins = carbide_insert_ccmt060204()
    export_step(ins, "carbide_insert.step")

    # 2. Drum Disk
    disk = drum_disk()
    export_step(disk, "shredder_drum_disk.step")

    # 3. Fixed Knife
    knife = fixed_knife()
    export_step(knife, "fixed_knife.step")

    print("Saved components.")
