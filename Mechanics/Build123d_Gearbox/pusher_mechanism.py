from build123d import *

def pusher_mechanism(
    width=250.0,  # Slightly less than drum length (254mm)
    depth=140.0,  # Matches drum diameter approx (150mm)
    thickness=20.0
):
    """
    Generates the Pusher Plate and Guide Rails.
    """

    # 1. Pusher Plate
    # A heavy block that pushes plastic down.
    with BuildPart() as pusher:
        Box(width, depth, thickness)

        # Add Handle / Actuator mount on top
        with Locations((0,0, thickness/2)):
            Box(50, 50, 20, mode=Mode.ADD)

    # 2. Guide Box (Simplified)
    # Just the rails or the hopper walls
    # For now, let's just return the plate as that's the moving part.

    return pusher.part

if __name__ == "__main__":
    print("Generating Pusher...")
    pusher = pusher_mechanism()
    export_step(pusher, "pusher_plate.step")
    print("Saved pusher_plate.step")
