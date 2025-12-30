import math
from build123d import *
from cycloidal_gear import cycloidal_disk
from impact_drive import impact_drive_mechanism

def gearbox_assembly(
    ratio=10.0,
    motor_type="NEMA23",
    input_interface="KEYED_SHAFT", # or BELT_GT2
    use_impact_drive=True
):
    """
    Generates the full gearbox assembly.
    """

    # 1. Generate Cycloidal Components
    # Simplify ratio logic for demo: Ratio approx N/(N-n).
    # If N=11, n=10 => Ratio=10.
    num_lobes = 10
    num_pins = 11

    disk = cycloidal_disk(
        pin_circle_diameter=50.0,
        num_lobes=num_lobes,
        num_pins=num_pins
    )

    # 2. Configure Motor Interface
    if motor_type == "NEMA34":
        housing_od = 100.0
        mount_spacing = 69.6
        input_shaft_dia = 14.0
        # Pilot cutout for NEMA 34 is usually ~73mm.
        # We'll just ensure the inner cavity is large enough.
        inner_cavity_dia = 75.0
    else: # Default to NEMA23
        housing_od = 80.0
        mount_spacing = 47.14
        input_shaft_dia = 8.0
        inner_cavity_dia = 60.0

    # 3. Housing
    # A simple box housing the pins
    housing_height = 40.0

    with BuildPart() as housing:
        Cylinder(radius=housing_od/2, height=housing_height)
        with Locations((0,0)):
            Cylinder(radius=inner_cavity_dia/2, height=housing_height-5, mode=Mode.SUBTRACT) # Inner cavity

        # Motor Mount Holes
        hole_radius = 6.5 / 2 if motor_type == "NEMA34" else 5.5 / 2
        with Locations((0,0, -housing_height/2)):
            with GridLocations(mount_spacing, mount_spacing, 2, 2):
                Cylinder(radius=hole_radius, height=10, mode=Mode.SUBTRACT)

    # 4. Shafts
    output_shaft_hex = 25.0 # 25mm Hex

    with BuildPart() as input_shaft:
        Cylinder(radius=input_shaft_dia/2, height=60.0)

    with BuildPart() as output_shaft:
        # Hex Shaft
        hex_radius = output_shaft_hex / math.sqrt(3)
        with BuildSketch():
            RegularPolygon(radius=hex_radius, side_count=6)
        extrude(amount=100.0) # Longer output shaft for the drum

        # Add a circular bearing interface at the gearbox end?
        # For simplicity, we keep it hex and assume hex bearings or adapters.

    # 5. Assembly List
    parts_list = [
        housing.part,
        disk.move(Location((0,0,5))), # Shift disk up
        input_shaft.part.move(Location((0,0,-10))),
        output_shaft.part.move(Location((0,0,10)))
    ]

    # 6. Impact Drive (Optional)
    if use_impact_drive:
        slip, hammer = impact_drive_mechanism(shaft_diameter=input_shaft_dia)
        # Attach Slip Disk to Input Shaft (top)
        parts_list.append(slip.move(Location((0,0, 40))))
        parts_list.append(hammer.move(Location((0,0, 55))))

    assembly = Compound(children=parts_list)
    return assembly

if __name__ == "__main__":
    print("Generating Gearbox Assembly...")
    asm = gearbox_assembly()
    export_step(asm, "shredder_gearbox_assembly.step")
    print("Saved shredder_gearbox_assembly.step")
