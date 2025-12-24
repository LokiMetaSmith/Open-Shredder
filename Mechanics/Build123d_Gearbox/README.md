# OpenShredder Gearbox & Components (Build123d)

This directory contains Python scripts to generate the 3D models for the OpenShredder gearbox and shredder mechanism using [build123d](https://github.com/gumyr/build123d).

## Prerequisites

You need `build123d` installed:
```bash
pip install build123d
```

## Scripts

### 1. `cycloidal_gear.py`
Generates the core cycloidal disk.
- Run: `python3 cycloidal_gear.py`
- Output: `cycloidal_disk.step`

### 2. `impact_drive.py`
Generates the slip-disk and impact hammer mechanism.
- Run: `python3 impact_drive.py`
- Output: `slip_disk.step`, `impact_hammer.step`

### 3. `shredder_components.py`
Generates the internal shredder parts:
- **Carbide Insert:** Standard CCMT060204 model.
- **Drum Disk:** Single slice of the shredder drum (150mm dia) with 25mm Hex bore.
- **Fixed Knife:** Counter-blade bar.
- Run: `python3 shredder_components.py`

### 4. `pusher_mechanism.py`
Generates the pusher plate.
- Run: `python3 pusher_mechanism.py`

### 5. `gearbox_assembly.py`
Generates the gearbox assembly.
- **Output Shaft:** 25mm Hex (configurable).
- Includes housing, input/output shafts, and impact drive.
- Run: `python3 gearbox_assembly.py`
- Output: `shredder_gearbox_assembly.step`

### 6. `full_machine_assembly.py`
Generates the complete machine model.
- Combines Gearbox, Helical Drum Stack (10 disks), Fixed Knife, and Pusher.
- Run: `python3 full_machine_assembly.py`
- Output: `open_shredder_full_assembly.step`

## Configuration
Adjust parameters in the respective python files (e.g., `drum_disk` diameter in `shredder_components.py` or `ratio` in `gearbox_assembly.py`).
