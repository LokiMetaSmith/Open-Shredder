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

    # 2. Housing
    # A simple box housing the pins
    housing_od = 80.0
    housing_height = 40.0

    with BuildPart() as housing:
        Cylinder(radius=housing_od/2, height=housing_height)
        with Locations((0,0)):
            Cylinder(radius=60.0/2, height=housing_height-5, mode=Mode.SUBTRACT) # Inner cavity

        # Motor Mount Holes (NEMA 23 standard: 47.14mm spacing)
        mount_spacing = 47.14
        with Locations((0,0, -housing_height/2)):
            with GridLocations(mount_spacing, mount_spacing, 2, 2):
                Cylinder(radius=5.0/2, height=10, mode=Mode.SUBTRACT)

    # 3. Shafts
    input_shaft_dia = 8.0
    output_shaft_dia = 12.0

    with BuildPart() as input_shaft:
        Cylinder(radius=input_shaft_dia/2, height=60.0)

    with BuildPart() as output_shaft:
        Cylinder(radius=output_shaft_dia/2, height=60.0)

    # 4. Assembly List
    parts_list = [
        housing.part,
        disk.move(Location((0,0,5))), # Shift disk up
        input_shaft.part.move(Location((0,0,-10))),
        output_shaft.part.move(Location((0,0,10)))
    ]

    # 5. Impact Drive (Optional)
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
