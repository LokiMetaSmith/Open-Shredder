#!/usr/bin/env python3
"""
Interactive Configuration & Tuning CLI for OpenShredder.
Allows users to evaluate and tune machine design parameters for specific
plastic recycle streams (PET, HDPE, PVC, LDPE, PP) and motor choices.
"""

import sys
import os
import argparse
import copy

try:
    from parameters.shredder_config import ShredderSystemConfig, default_config
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'parameters'))
    from shredder_config import ShredderSystemConfig, default_config

from validate_design import DesignValidator
from simulate_stress import StressSimulator

# Plastic properties database: Shear strength in MPa, Typical Wall Thickness in mm
PLASTIC_DATABASE = {
    "PET": {"name": "Polyethylene terephthalate (Recycle #1)", "shear_mpa": 40.0, "default_thickness_mm": 1.0},
    "HDPE": {"name": "High-density polyethylene (Recycle #2)", "shear_mpa": 25.0, "default_thickness_mm": 2.0},
    "PVC": {"name": "Polyvinyl chloride (Recycle #3)", "shear_mpa": 50.0, "default_thickness_mm": 1.5},
    "LDPE": {"name": "Low-density polyethylene (Recycle #4)", "shear_mpa": 15.0, "default_thickness_mm": 1.5},
    "PP": {"name": "Polypropylene (Recycle #5)", "shear_mpa": 30.0, "default_thickness_mm": 1.5},
}

def evaluate_tuning(config: ShredderSystemConfig, plastic_code: str = "PET", plastic_thickness_mm: float = None):
    """
    Evaluates required torque, output torque, and shaft stresses for a selected plastic.
    """
    plastic_info = PLASTIC_DATABASE.get(plastic_code.upper(), PLASTIC_DATABASE["PET"])
    shear_mpa = plastic_info["shear_mpa"]
    thickness_m = (plastic_thickness_mm if plastic_thickness_mm is not None else plastic_info["default_thickness_mm"]) / 1000.0

    motor = config.motor
    gearbox = config.gearbox
    shredder = config.shredder

    # Shearing calculation: 2 simultaneous cuts, 10mm chunk width
    simultaneous_cuts = 2
    cut_width = 10.0e-3
    shear_area = thickness_m * cut_width * simultaneous_cuts
    shear_force_n = (shear_mpa * 1e6) * shear_area
    drum_radius_m = (shredder.drum_diameter_mm / 2.0) / 1000.0
    required_torque_nm = shear_force_n * drum_radius_m

    efficiency = 0.8
    available_torque_nm = motor.torque_nm * gearbox.ratio * efficiency
    torque_safety_factor = available_torque_nm / required_torque_nm if required_torque_nm > 0 else 999.0

    output_rpm = motor.max_rpm / gearbox.ratio

    sim = StressSimulator(config)
    stress_results = sim.simulate_combined_stress(verbose=False)

    return {
        "plastic": plastic_code.upper(),
        "plastic_desc": plastic_info["name"],
        "shear_strength_mpa": shear_mpa,
        "cut_thickness_mm": thickness_m * 1000.0,
        "required_torque_nm": required_torque_nm,
        "available_torque_nm": available_torque_nm,
        "torque_safety_factor": torque_safety_factor,
        "output_rpm": output_rpm,
        "shaft_von_mises_stress_mpa": stress_results["von_mises_stress_mpa"],
        "shaft_safety_factor": stress_results["safety_factor"]
    }

def print_tuning_report(metrics: dict):
    print("=" * 60)
    print(f"OpenShredder Tuning Evaluation for: {metrics['plastic']} - {metrics['plastic_desc']}")
    print("=" * 60)
    print(f"  Shear Strength:        {metrics['shear_strength_mpa']:.1f} MPa")
    print(f"  Plastic Wall Thickness:{metrics['cut_thickness_mm']:.2f} mm")
    print(f"  Required Shear Torque: {metrics['required_torque_nm']:.2f} Nm")
    print(f"  Gearbox Output Torque: {metrics['available_torque_nm']:.2f} Nm")
    print(f"  Torque Safety Factor:  {metrics['torque_safety_factor']:.2f} {'[OK]' if metrics['torque_safety_factor'] >= 1.5 else '[WARN: < 1.5]'}")
    print(f"  Drum Output Speed:     {metrics['output_rpm']:.1f} RPM")
    print(f"  Shaft Von Mises Stress:{metrics['shaft_von_mises_stress_mpa']:.2f} MPa")
    print(f"  Shaft Safety Factor:   {metrics['shaft_safety_factor']:.2f} {'[OK]' if metrics['shaft_safety_factor'] >= 2.0 else '[WARN: < 2.0]'}")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Tune OpenShredder for target plastic recyclable streams.")
    parser.add_argument("--config", type=str, default=None, help="Input config JSON")
    parser.add_argument("--plastic", type=str, default="PET", choices=list(PLASTIC_DATABASE.keys()), help="Target plastic type")
    parser.add_argument("--thickness", type=float, default=None, help="Custom plastic wall thickness (mm)")
    parser.add_argument("--ratio", type=float, default=None, help="Override gear reduction ratio")
    parser.add_argument("--drum-dia", type=float, default=None, help="Override drum outer diameter (mm)")
    parser.add_argument("--shaft-hex", type=float, default=None, help="Override shaft hex size (mm)")
    parser.add_argument("--save", type=str, default=None, help="Save updated configuration to specified JSON path")
    args = parser.parse_args()

    # Load base config
    if args.config and os.path.exists(args.config):
        cfg = ShredderSystemConfig.load_from_json(args.config)
    else:
        optimized_path = os.path.join(os.path.dirname(__file__), 'parameters', 'optimized_shredder_config.json')
        default_path = os.path.join(os.path.dirname(__file__), 'parameters', 'shredder_config.json')
        if os.path.exists(optimized_path):
            cfg = ShredderSystemConfig.load_from_json(optimized_path)
        elif os.path.exists(default_path):
            cfg = ShredderSystemConfig.load_from_json(default_path)
        else:
            cfg = default_config

    # Apply overrides
    if args.ratio is not None:
        cfg.gearbox.ratio = args.ratio
    if args.drum_dia is not None:
        cfg.shredder.drum_diameter_mm = args.drum_dia
    if args.shaft_hex is not None:
        cfg.gearbox.output_shaft_hex_mm = args.shaft_hex
        cfg.shredder.hex_bore_mm = args.shaft_hex

    metrics = evaluate_tuning(cfg, plastic_code=args.plastic, plastic_thickness_mm=args.thickness)
    print_tuning_report(metrics)

    if args.save:
        cfg.save_to_json(args.save)
        print(f"Saved tuned configuration to {args.save}")

if __name__ == "__main__":
    main()
