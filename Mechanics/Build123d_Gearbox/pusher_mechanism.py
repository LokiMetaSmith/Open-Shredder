import sys
import os

try:
    from parameters.shredder_config import ShredderSystemConfig, default_config
except ImportError:
    # Add parameters directory to sys.path if running as script
    sys.path.append(os.path.join(os.path.dirname(__file__), 'parameters'))
    from shredder_config import ShredderSystemConfig, default_config

from build123d import *

def hopper_assembly(config: ShredderSystemConfig):
    """
    Generates a full parametric hopper with guide rails, side walls,
    and a guided pusher block with guide slots.
    """
    shredder_conf = config.shredder

    drum_len = shredder_conf.drum_length_mm
    drum_dia = shredder_conf.drum_diameter_mm

    hopper_wall_thickness = 8.0
    rail_width = 12.0
    rail_depth = 10.0
    clearance = 2.0

    hopper_inner_width = drum_len + (2.0 * clearance)
    hopper_inner_depth = drum_dia + 20.0
    hopper_height = 160.0

    # 1. Hopper Body (Outer box minus inner cavity)
    with BuildPart() as hopper:
        Box(
            hopper_inner_width + (2 * hopper_wall_thickness),
            hopper_inner_depth + (2 * hopper_wall_thickness),
            hopper_height
        )
        with Locations((0, 0, 0)):
            Box(hopper_inner_width, hopper_inner_depth, hopper_height + 2, mode=Mode.SUBTRACT)

        # Guide Rails on Left and Right Inside Walls
        rail_x_left = -hopper_inner_width / 2.0 + rail_depth / 2.0
        rail_x_right = hopper_inner_width / 2.0 - rail_depth / 2.0
        with Locations((rail_x_left, 0, 0)):
            Box(rail_depth, rail_width, hopper_height, mode=Mode.ADD)
        with Locations((rail_x_right, 0, 0)):
            Box(rail_depth, rail_width, hopper_height, mode=Mode.ADD)

    # 2. Guided Pusher Block
    pusher_width = hopper_inner_width - (2.0 * clearance)
    pusher_depth = hopper_inner_depth - (2.0 * clearance)
    pusher_thickness = 25.0

    slot_width = rail_width + (2.0 * clearance)
    slot_depth = rail_depth + clearance

    with BuildPart() as pusher:
        Box(pusher_width, pusher_depth, pusher_thickness)

        # Guide Slots cut into the pusher sides to mate with rails
        with Locations((-pusher_width / 2.0 + slot_depth / 2.0, 0, 0)):
            Box(slot_depth, slot_width, pusher_thickness + 2, mode=Mode.SUBTRACT)
        with Locations((pusher_width / 2.0 - slot_depth / 2.0, 0, 0)):
            Box(slot_depth, slot_width, pusher_thickness + 2, mode=Mode.SUBTRACT)

        # Actuator / Handle Mount on Top
        with Locations((0, 0, pusher_thickness / 2.0 + 10.0)):
            Box(60.0, 60.0, 20.0, mode=Mode.ADD)
            with Locations((0, 0, 5)):
                Cylinder(radius=4.5, height=22, mode=Mode.SUBTRACT) # Mounting pin hole

    # Position pusher inside hopper
    pusher_in_hopper = pusher.part.move(Location((0, 0, hopper_height / 4.0)))

    return Compound(children=[hopper.part, pusher_in_hopper])

def pusher_mechanism(config: ShredderSystemConfig):
    """
    Backward-compatible entry point returning the complete hopper/pusher mechanism.
    """
    return hopper_assembly(config)

if __name__ == "__main__":
    print("Generating Hopper & Guided Pusher from Config...")
    config_path = os.path.join(os.path.dirname(__file__), 'parameters', 'shredder_config.json')
    if os.path.exists(config_path):
        print(f"Loading config from {config_path}")
        cfg = ShredderSystemConfig.load_from_json(config_path)
    else:
        print("Using default config")
        cfg = default_config

    hopper = hopper_assembly(cfg)
    export_step(hopper, "hopper_pusher_assembly.step")
    print("Saved hopper_pusher_assembly.step")
