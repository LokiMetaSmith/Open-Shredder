# OpenShredder Gearbox Generator (Build123d)

This directory contains Python scripts to generate the 3D models for the OpenShredder gearbox using [build123d](https://github.com/gumyr/build123d).

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

### 3. `gearbox_assembly.py`
Generates the full assembly including housing, shafts, gears, and the impact drive.
- Run: `python3 gearbox_assembly.py`
- Output: `shredder_gearbox_assembly.step`

## Configuration
Open `gearbox_assembly.py` to adjust parameters:
- `ratio`: Gear reduction ratio.
- `motor_type`: NEMA23 or other mounts.
- `use_impact_drive`: Toggle the impact mechanism.
