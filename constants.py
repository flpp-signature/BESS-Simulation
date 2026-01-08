# -*- coding: utf-8 -*-
"""
Constants and default values for BESS simulation.

This module contains all fixed constants, time-related values, and default 
parameters used throughout the simulation.
"""

import pandas as pd

# =============================================================================
# Time Constants
# =============================================================================
MTU = pd.Timedelta('15 min')  # Market Time Unit (trading interval)
HOUR = pd.Timedelta('60 min')
MIN_5 = pd.Timedelta('5 min')
MIN_10 = pd.Timedelta('10 min')
ONE_DAY = pd.Timedelta('1 day')

# =============================================================================
# Market Constants
# =============================================================================
STEP_FRR = 1  # FRR bid step is assumed to be 1 MW

# =============================================================================
# Default File Names
# =============================================================================
DEFAULT_SETTINGS_FILE = 'settings.xlsx'
DEFAULT_OUTPUT_TEMPLATE = 'output_template.xlsx'

# =============================================================================
# Precision for floating point comparisons
# =============================================================================
FLOAT_PRECISION = 3
ENERGY_TOLERANCE = 0.001  # MWh tolerance for energy comparisons
