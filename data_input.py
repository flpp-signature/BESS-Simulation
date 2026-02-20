# -*- coding: utf-8 -*-
"""
Data input handling for BESS simulation.

This module handles reading and processing input data files for frequency
measurements and FRR activation demands.
"""

import pandas as pd
import numpy as np
from typing import Tuple


class DataLoader:
    """
    Handles loading and processing of simulation input data files.
    """
    
    @staticmethod
    def load_frequency_data(
        freq_file: str,
        working_resolution: pd.Timedelta
    ) -> Tuple[pd.Series, pd.Timestamp, pd.Timestamp]:
        """
        Load and process frequency data from file.
        
        Args:
            freq_file: Path to frequency data file (csv, xls, or xlsx)
            working_resolution: Target time resolution for resampling
        
        Returns:
            Tuple of (frequency series, start_time, end_time)
        
        Raises:
            Exception: If file format is not supported
        """
        # Read file based on extension
        if freq_file.endswith('.csv'):
            frequency_data = pd.read_csv(freq_file)
        elif freq_file.endswith('.xlsx') or freq_file.endswith('.xls'):
            frequency_data = pd.read_excel(freq_file)
        else:
            raise Exception(
                f"Can't read {freq_file}. The frequency input file should "
                "have a .csv, .xls or .xlsx extension"
            )
        
        # Parse timestamps - use format='mixed' to handle various date formats
        # Try standard parsing first, fall back to mixed format if it fails
        try:
            frequency_data['Time'] = pd.to_datetime(
                frequency_data.Time, dayfirst=True
            )
        except ValueError:
            # Fall back to mixed format parsing if strict parsing fails
            frequency_data['Time'] = pd.to_datetime(
                frequency_data.Time, format='mixed', dayfirst=True
            )
        
        # Determine simulation time bounds
        start_time = frequency_data.Time.iloc[0].floor(working_resolution)
        end_time = frequency_data.Time.iloc[-1].ceil(working_resolution)
        
        # Resample to working resolution
        frequency_data_scaled = frequency_data.resample(
            working_resolution, on='Time'
        ).mean()
        
        # Create time index for simulation
        time_indexes = pd.to_datetime(
            np.arange(start_time, end_time, working_resolution)
        )
        
        # Create frequency series
        frequency = pd.Series(frequency_data_scaled.Value, time_indexes)
        
        return frequency, start_time, end_time
    
    @staticmethod
    def load_frr_data(
        frr_file: str,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        working_resolution: pd.Timedelta
    ) -> pd.Series:
        """
        Load and process FRR activation data from file.
        
        Args:
            frr_file: Path to FRR data file (csv, xls, or xlsx)
            start_time: Simulation start time
            end_time: Simulation end time
            working_resolution: Simulation time resolution
        
        Returns:
            Series with FRR activation values at each time step
        
        Raises:
            Exception: If file format is not supported
        """
        # Read file based on extension
        if frr_file.endswith('.csv'):
            FRR_data = pd.read_csv(frr_file)
        elif frr_file.endswith('.xlsx') or frr_file.endswith('.xls'):
            FRR_data = pd.read_excel(frr_file)
        else:
            raise Exception(
                f"Can't read {frr_file}. The FRR input file should "
                "have a .csv, .xls or .xlsx extension"
            )
        
        # Parse timestamps with fallback to mixed format handling
        try:
            FRR_data.Start = pd.to_datetime(FRR_data.Start, dayfirst=True)
        except ValueError:
            FRR_data.Start = pd.to_datetime(
                FRR_data.Start, format='mixed', dayfirst=True
            )
        
        try:
            FRR_data.End = pd.to_datetime(FRR_data.End, dayfirst=True)
        except ValueError:
            FRR_data.End = pd.to_datetime(
                FRR_data.End, format='mixed', dayfirst=True
            )
        
        # Create time index
        time_indexes = pd.to_datetime(
            np.arange(start_time, end_time, working_resolution)
        )
        
        # Initialize FRR activation series with zeros
        FRR_activ = pd.Series(
            [0] * int((end_time - start_time) / working_resolution), 
            time_indexes
        )
        
        FRR_data['MW'] = FRR_data['MW'].round(1) # fix issues from rounding cascade
        # Fill in activation periods
        for t in range(len(FRR_data)):
            FRR_activ[
                FRR_data.Start[t]:FRR_data.End[t] - working_resolution
            ] = FRR_data.MW[t]
        
        return FRR_activ
    
    @staticmethod
    def create_time_indexes(
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        working_resolution: pd.Timedelta,
        MTU: pd.Timedelta
    ) -> Tuple[pd.DatetimeIndex, pd.DatetimeIndex, pd.DatetimeIndex]:
        """
        Create time index arrays for simulation.
        
        Args:
            start_time: Simulation start time
            end_time: Simulation end time
            working_resolution: Simulation time resolution
            MTU: Market time unit (trading interval)
        
        Returns:
            Tuple of (time_indexes, MTUs, MTUs_24h)
        """
        # Main simulation time index
        time_indexes = pd.to_datetime(
            np.arange(start_time, end_time, working_resolution)
        )
        
        # MTU starts
        MTUs = pd.to_datetime(
            np.arange(
                start_time.floor(MTU), 
                end_time + pd.Timedelta('1 d'), 
                MTU
            )
        )
        
        # 24-hour MTU index (for daily patterns)
        MTUs_24h = pd.to_datetime(
            np.arange(
                start_time.floor(pd.Timedelta('1 d')),
                start_time.floor(pd.Timedelta('1 d')) + pd.Timedelta('1 d'),
                MTU
            )
        )
        
        return time_indexes, MTUs, MTUs_24h