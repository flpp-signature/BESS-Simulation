#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BESS_sim.py - BESS Management Model Simulation Tool

This script serves as the main entry point for running the BESS simulation.
It maintains backward compatibility with the original monolithic script.

Usage:
    python BESS_sim.py [settings_file] [output_template]

Arguments:
    settings_file: Path to settings Excel file (default: settings.xlsx)
    output_template: Path to output template file (default: output_template.xlsx)
"""

import os
import sys

# Ensure the package directory is in the path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Ensure working directory is set correctly
try:
    os.chdir(script_dir)
except Exception:
    pass

from bess_sim import run_simulation

if __name__ == '__main__':
    # Parse command line arguments if provided
    settings_file = None
    output_template = None
    
    if len(sys.argv) > 1:
        settings_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_template = sys.argv[2]
    
    run_simulation(settings_file, output_template)
