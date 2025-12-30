from build123d import *
import math
from gearbox_assembly import gearbox_assembly
from shredder_components import drum_disk, fixed_knife
from pusher_mechanism import pusher_mechanism

def full_machine_assembly():
    """
    Assembles the Gearbox, Shredder Drum, Fixed Knife, and Pusher.
    """

    # 1. Gearbox
    # (Includes Housing, Input Shaft, Output Hex Shaft, Impact Drive)
    # Using NEMA 34 Stepper Motor for high torque and home use
    gearbox = gearbox_assembly(ratio=10.0, motor_type="NEMA34", use_impact_drive=True)

    # Extract the output shaft location relative to the gearbox?
    # The gearbox output shaft was generated at (0,0,10) in the sub-assembly.
    # It extends 100mm.

    # 2. Shredder Drum
    # Stack of disks.
    # Length 254mm. Disk thickness ~25.4mm => 10 disks.
    num_disks = 10
    disk_thickness = 25.4

    drum_parts = []

    # We want a helical pattern.
    # Each disk has 2 teeth.
    # Total twist? 180 degrees? Or 360?
    # Let's offset each disk by 360 / (num_disks * num_teeth) ?
    # 360 / 20 = 18 degrees per step.

    angle_step = 360.0 / (num_disks * 2)

    # Create one master disk to copy?
    master_disk_shape = drum_disk(thickness=disk_thickness, hex_shaft_size=25.0, num_teeth=2)

    # We need to position the drum ON the shaft.
    # Gearbox is at origin?
    # Let's say Gearbox is at Z=0 to Z=50. Output shaft sticks up to Z=150.
    # Wait, the gearbox script made the shaft 100mm long. We need 254mm + extra.
    # We might need to extend the shaft here or modify the gearbox script to be parametric on shaft length.
    # For now, let's just place the drum "above" the gearbox and assume the shaft continues (visual assembly).

    drum_start_z = 60.0 # Clear the gearbox housing

    for i in range(num_disks):
        z_pos = drum_start_z + (i * disk_thickness)
        angle = i * angle_step

        # Copy and move
        d = master_disk_shape.rotate(Axis.Z, angle).move(Location((0,0, z_pos)))
        drum_parts.append(d)

    # 3. Fixed Knife
    # Positioned next to the drum.
    # Drum Radius = 75mm.
    # Knife should be at X = 75 + clearance?
    # Or usually, the knife interlocks.
    knife_shape = fixed_knife(length=254.0, drum_diameter=150.0)

    # Center the knife along the drum length
    drum_center_z = drum_start_z + (254.0 / 2)
    knife_loc = Location((80, 0, drum_center_z)) # X=80 (just outside 75 radius), Centered Z

    knife_part = knife_shape.move(knife_loc) # Knife was created centered?
    # fixed_knife() -> Box(length, width, thickness). Box is centered at 0,0,0.
    # Length is X dimension? No, Box(length, width, thickness). usually X, Y, Z.
    # Let's check fixed_knife implementation: Box(length, width, thickness).
    # So X=254. We want Length along Z axis.
    # So we need to rotate the knife.

    knife_part = knife_shape.rotate(Axis.Y, 90).move(knife_loc)

    # 4. Pusher
    # Above the drum?
    # Usually pushing down into the nip.
    # If the knife is at X+, the nip is maybe at Top?
    # Let's put the pusher above the drum (Z+ is shaft axis?).
    # Wait, single shaft shredders usually have a horizontal shaft.
    # Our generated gearbox has Z as the shaft axis.
    # So the machine is "Vertical" (like a blender) currently.
    # Most industrial shredders are horizontal.
    # Let's Rotate the whole Gearbox+Drum to be Horizontal for the final assembly?
    # Or just leave it vertical for the model.
    # Let's leave it vertical (Z-axis shaft) as it's easier given the current coordinates.
    # So "Pusher" pushes radially inwards? Or axially?
    # Single Shaft Shredder (Horizontal Shaft): Pusher pushes horizontally towards the drum.
    # Vertical Shaft Shredder: Gravity fed? Or pusher pushes from side?
    # Let's assume standard Horizontal layout.
    # So we should Rotate everything.

    # Let's keep Z-axis for generating, but the "Pusher" is actually a "Ram" on the side.
    # If Knife is at X=80, Pusher might be at X=-80?
    # Or Y axis?
    pusher_shape = pusher_mechanism(width=250.0, depth=140.0)
    # Pusher is Box(width, depth, thickness).
    # We want it to push towards the drum.
    # Let's place it at Y = -100.
    pusher_loc = Location((0, -120, drum_center_z))
    pusher_part = pusher_shape.rotate(Axis.X, 90).move(pusher_loc) # Rotate to face drum

    # Combine Everything
    full_assembly = Compound(children=[
        gearbox,
        *drum_parts,
        knife_part,
        pusher_part
    ])

    return full_assembly

if __name__ == "__main__":
    print("Generating Full Machine Assembly...")
    asm = full_machine_assembly()
    export_step(asm, "open_shredder_full_assembly.step")
    print("Saved open_shredder_full_assembly.step")
