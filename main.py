# -*- coding: utf-8 -*-
"""
BESS Simulation Tool - Main Entry Point

This is the main module that orchestrates the BESS reserve provision simulation.
It handles loading settings, initializing components, running the simulation,
and producing outputs.
"""

import os
import sys
import time
import shutil
import traceback
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

try:
    from .constants import MTU, HOUR, ONE_DAY, DEFAULT_SETTINGS_FILE, DEFAULT_OUTPUT_TEMPLATE
    from .utils import custom_print
    from .config import ConfigurationManager
    from .data_input import DataLoader
    from .bess_model import BESS
    from .simulation import SimulationEngine
    from .output import ResultsWriter, Visualizer, print_summary
except ImportError:
    # Spyder / direct execution (%runfile)
    from constants import MTU, HOUR, ONE_DAY, DEFAULT_SETTINGS_FILE, DEFAULT_OUTPUT_TEMPLATE
    from utils import custom_print
    from config import ConfigurationManager
    from data_input import DataLoader
    from bess_model import BESS
    from simulation import SimulationEngine
    from output import ResultsWriter, Visualizer, print_summary


def create_output_folder(scenario_name: str) -> str:
    """
    Create output folder for simulation results.
    
    Args:
        scenario_name: Base name for the scenario
    
    Returns:
        Full path to the created folder
    """
    folder_name = scenario_name + ' Run '
    run_idx = 1
    
    if not os.path.isdir(folder_name + str(run_idx)):
        os.mkdir(folder_name + str(run_idx))
    else:
        while os.path.isdir(folder_name + str(run_idx)):
            run_idx += 1
        os.mkdir(folder_name + str(run_idx))
    
    return folder_name + str(run_idx)


def run_simulation(settings_file: str = None, output_template: str = None) -> None:
    """
    Run the complete BESS simulation.
    
    Args:
        settings_file: Path to settings Excel file (default: settings.xlsx)
        output_template: Path to output template file (default: output_template.xlsx)
    """
    if settings_file is None:
        settings_file = DEFAULT_SETTINGS_FILE
    if output_template is None:
        output_template = DEFAULT_OUTPUT_TEMPLATE
    
    try:
        start_clock = time.time()
        
        print('starting execution...')
        print(os.getcwd())
        
        # Load configuration
        print('reading input settings and timeseries...')
        config = ConfigurationManager(settings_file)
        
        sim_settings = config.get_simulation_settings()
        market_settings = config.get_market_settings()
        freq_settings = config.get_frequency_settings()
        bess_1_params = config.get_bess_parameters(1)
        bess_2_params = config.get_bess_parameters(2)
        reserve_settings_1 = config.get_reserve_provision_settings(1)
        reserve_settings_2 = config.get_reserve_provision_settings(2)
        
        working_resolution = sim_settings.working_resolution
        
        # Prepare output folder
        scenario_name = create_output_folder(sim_settings.scenario_name)
        
        # Prepare log file
        log_name = scenario_name + "/" + scenario_name + ' LOG.txt'
        with open(log_name, 'w') as f:
            f.write('Log for ' + scenario_name + '\n')
        
        # Copy settings to results folder
        shutil.copy(
            settings_file, 
            scenario_name + '/' + settings_file[0:-5] + ' ' + scenario_name + '.xlsx'
        )
        
        # Load frequency data
        data_loader = DataLoader()
        frequency, start_time, end_time = data_loader.load_frequency_data(
            sim_settings.freq_file, 
            working_resolution
        )
        
        # Create time indexes
        time_indexes, MTUs, MTUs_24h = data_loader.create_time_indexes(
            start_time, end_time, working_resolution, MTU
        )
        
        # Load FRR activation data
        FRR_activ = data_loader.load_frr_data(
            sim_settings.FRR_file,
            start_time,
            end_time,
            working_resolution
        )
        
        custom_print('initializing timeseries...', log_name)
        
        # Create BESS models
        bess_1 = BESS(
            bess_1_params, reserve_settings_1,
            start_time, end_time, MTUs_24h, working_resolution,
            bess_id=1
        )
        
        bess_2 = BESS(
            bess_2_params, reserve_settings_2,
            start_time, end_time, MTUs_24h, working_resolution,
            bess_id=2
        )
        
        # Initialize reserve capacity series
        bess_1.FCR_series_init(start_time, end_time, working_resolution)
        bess_2.FCR_series_init(start_time, end_time, working_resolution)
        bess_1.FRR_series_init(start_time, end_time, working_resolution)
        bess_2.FRR_series_init(start_time, end_time, working_resolution)
        
        # Create and run simulation
        custom_print('starting simulations...\n', log_name)
        
        engine = SimulationEngine(
            bess_1=bess_1,
            bess_2=bess_2,
            frequency=frequency,
            FRR_activ=FRR_activ,
            time_indexes=time_indexes,
            start_time=start_time,
            end_time=end_time,
            sim_settings=sim_settings,
            market_settings=market_settings,
            freq_settings=freq_settings,
            log_name=log_name
        )
        
        results = engine.run()
        
        # Write results
        custom_print('writing results...', log_name)
        
        out_name = scenario_name + '/' + 'Results ' + scenario_name + '.xlsx'
        shutil.copy(output_template, out_name)
        
        ResultsWriter.write_results(
            results, out_name, freq_settings, working_resolution
        )
        
        # Create visualization
        custom_print('preparing figures...', log_name)
        
        visualizer = Visualizer(results, freq_settings, working_resolution)
        visualizer.create_figure()
        
        custom_print('\nDone!', log_name)
        custom_print(f"Execution time: {(time.time() - start_clock):.2f} seconds", log_name)
        
        visualizer.show()
        
        # Print summary
        print_summary(results, working_resolution)
        
    except Exception:
        print('An error occurred. Traceback below:\n\n')
        traceback.print_exc()
        
        with open('error_log.txt', 'w') as f:
            f.write(str(traceback.format_exc()))
        
        input('\nPress Enter to exit')


def main():
    """Main entry point for command-line execution."""
    # Ensure working directory is set correctly
    try:
        os.chdir(os.path.realpath(os.path.dirname(__file__)))
    except Exception:
        pass
    
    # Parse command line arguments if provided
    settings_file = None
    output_template = None
    
    if len(sys.argv) > 1:
        settings_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_template = sys.argv[2]
    
    run_simulation(settings_file, output_template)


if __name__ == '__main__':
    main()
