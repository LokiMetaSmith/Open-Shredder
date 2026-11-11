import os
import sys
import tempfile
import random
import csv
import pytest

# Ensure Mechanics and parameters directories are on sys.path
mechanics_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Build123d_Gearbox'))
parameters_dir = os.path.join(mechanics_dir, 'parameters')
if mechanics_dir not in sys.path:
    sys.path.insert(0, mechanics_dir)
if parameters_dir not in sys.path:
    sys.path.insert(0, parameters_dir)

from shredder_config import ShredderSystemConfig, default_config
from validate_design import DesignValidator, validate_config
from simulate_stress import StressSimulator
from generate_bom import BOMGenerator
from optimize_design import DesignOptimizerAgent

def test_config_load_and_save():
    default_cfg = ShredderSystemConfig()
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        tmp_name = f.name
    try:
        default_cfg.save_to_json(tmp_name)
        loaded = ShredderSystemConfig.load_from_json(tmp_name)
        assert loaded.motor.type == default_cfg.motor.type
        assert loaded.gearbox.ratio == default_cfg.gearbox.ratio
        assert loaded.shredder.num_disks == default_cfg.shredder.num_disks
        assert loaded.material.shaft_yield_strength_mpa == default_cfg.material.shaft_yield_strength_mpa
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)

def test_validation_detects_mismatches():
    cfg = ShredderSystemConfig()
    # 1. Hex mismatch
    cfg.gearbox.output_shaft_hex_mm = 20.0
    cfg.shredder.hex_bore_mm = 25.0
    validator = DesignValidator(cfg)
    valid = validator.run()
    assert not valid
    assert any("Mismatch: Gearbox output hex" in e for e in validator.errors)

    # 2. Shaft too short
    cfg.gearbox.output_shaft_hex_mm = 25.0
    cfg.shredder.hex_bore_mm = 25.0
    cfg.gearbox.output_shaft_length_mm = 50.0 # Way too short for 10 * 25.4 = 254mm stack
    validator = DesignValidator(cfg)
    valid = validator.run()
    assert not valid
    assert any("Shaft too short" in e for e in validator.errors)

def test_validation_insufficient_torque():
    cfg = ShredderSystemConfig()
    # High ratio and long shaft to pass geometry
    cfg.gearbox.output_shaft_length_mm = 300.0
    cfg.motor.torque_nm = 0.1 # Tiny motor torque
    cfg.gearbox.ratio = 2.0
    validator = DesignValidator(cfg)
    valid = validator.run()
    assert not valid
    assert any("Insufficient Torque" in e for e in validator.errors)

def test_validation_passes_on_valid_configuration():
    cfg = ShredderSystemConfig()
    cfg.gearbox.output_shaft_length_mm = 300.0
    cfg.gearbox.ratio = 20.0
    cfg.gearbox.output_shaft_hex_mm = 25.0
    cfg.shredder.hex_bore_mm = 25.0
    validator = DesignValidator(cfg)
    valid = validator.run()
    assert valid
    assert len(validator.errors) == 0

def test_simulate_torsion_and_combined_stress():
    cfg = ShredderSystemConfig()
    sim = StressSimulator(cfg)

    # Pure torsion
    torsion_res = sim.simulate_torsion(verbose=False)
    assert torsion_res["torque_nm"] > 0
    assert torsion_res["max_shear_stress_mpa"] > 0
    assert torsion_res["safety_factor"] > 0

    # Combined stress
    combined_res = sim.simulate_combined_stress(verbose=False)
    assert combined_res["torque_nm"] == torsion_res["torque_nm"]
    assert combined_res["cutting_force_n"] > 0
    assert combined_res["bending_moment_nm"] > 0
    assert combined_res["max_bending_stress_mpa"] > 0
    # Von Mises stress should be strictly greater than individual bending stress
    assert combined_res["von_mises_stress_mpa"] >= combined_res["max_bending_stress_mpa"]
    assert combined_res["safety_factor"] > 0

def test_bom_generation_and_csv_export():
    cfg = ShredderSystemConfig()
    bom = BOMGenerator(cfg)
    bom.generate()

    assert len(bom.items) > 0
    categories = {item.category for item in bom.items}
    assert "Electronics" in categories
    assert "Hardware" in categories
    assert "Printed" in categories

    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
        tmp_csv = f.name
    try:
        bom.write_csv(tmp_csv)
        assert os.path.exists(tmp_csv)
        with open(tmp_csv, 'r') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)
            assert len(rows) == len(bom.items) + 1 # Header + items
            assert rows[0][0] == "Category"
    finally:
        if os.path.exists(tmp_csv):
            os.remove(tmp_csv)

def test_optimizer_agent_deterministic_run():
    random.seed(42)
    cfg = ShredderSystemConfig()
    agent = DesignOptimizerAgent(cfg)
    optimized = agent.run(steps=30)

    # After optimization, errors should be resolved or reduced
    validator = DesignValidator(optimized)
    validator.check_geometry()
    assert not any("Shaft too short" in e for e in validator.errors)

def test_tune_shredder_evaluation():
    from tune_shredder import evaluate_tuning, PLASTIC_DATABASE
    cfg = ShredderSystemConfig()
    cfg.gearbox.ratio = 25.0

    for plastic in ["PET", "HDPE", "PP"]:
        metrics = evaluate_tuning(cfg, plastic_code=plastic)
        assert metrics["plastic"] == plastic
        assert metrics["required_torque_nm"] > 0
        assert metrics["available_torque_nm"] > 0
        assert metrics["shaft_von_mises_stress_mpa"] > 0
        assert metrics["shaft_safety_factor"] > 0

def test_hopper_assembly_build():
    from pusher_mechanism import hopper_assembly
    cfg = ShredderSystemConfig()
    hopper = hopper_assembly(cfg)
    assert hopper is not None
    # Verify compound has children (hopper body and guided pusher)
    assert len(hopper.children) >= 2
