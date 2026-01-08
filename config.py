# -*- coding: utf-8 -*-
"""
Configuration management for BESS simulation.

This module handles reading settings from Excel files and provides
a structured way to access simulation parameters.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Any

try:
    from .constants import MTU, HOUR, ONE_DAY
except ImportError:
    from constants import MTU, HOUR, ONE_DAY

def safe_isnan(value) -> bool:
    """Safely check if a value is NaN, handling non-numeric types."""
    try:
        return pd.isna(value) or np.isnan(float(value))
    except (TypeError, ValueError):
        return pd.isna(value)


@dataclass
class BESSParameters:
    """Technical parameters for a single BESS unit."""
    power_up: float  # MW, max discharge power
    power_down: float  # MW, max charge power
    capacity: float  # MWh, rated energy capacity
    min_SOC: float  # Minimum SOC limit
    max_SOC: float  # Maximum SOC limit
    ch_eff: float  # Charging efficiency
    disch_eff: float  # Discharging efficiency
    idle_loss: float  # Self-discharge rate (%/day)
    min_cycle: float  # Minimum cycling requirement
    SOC0: float  # Initial state of charge
    LER: bool  # Is qualified as LER
    live: bool  # Is BESS available/active
    SOC_str: int  # SOC strategy (0=Active, 1=Conservative)
    bess_id: int  # BESS identifier (1 or 2)
    min_unit: str  # Unit for min_SOC (% or MWh)
    max_unit: str  # Unit for max_SOC (% or MWh)
    SOC_unit: str  # Unit for initial SOC


@dataclass
class MarketSettings:
    """Market timing and trading settings."""
    GCT_FCR_cap: pd.Timestamp  # FCR capacity market GCT
    GCT_FRR_cap: pd.Timestamp  # FRR capacity market GCT
    GCT_FRR_en: pd.Timedelta  # FRR energy market GCT (before MTU)
    GCT_ID: pd.Timedelta  # Intraday market GCT (before MTU)
    t_prep_ID: pd.Timedelta  # Preparation time for ID decisions
    t_prep_FCR_cap: pd.Timedelta  # Preparation time for FCR capacity bids
    t_prep_FRR_cap: pd.Timedelta  # Preparation time for FRR capacity bids
    t_prep_FRR_en: pd.Timedelta  # Preparation time for FRR energy bids


@dataclass
class FrequencySettings:
    """Power system frequency parameters."""
    nom_frequency: float  # Nominal frequency (Hz)
    max_deviation: float  # Maximum frequency deviation for full FCR (Hz)
    deadband: float  # Frequency deadband (Hz)
    t_min_FCR: pd.Timedelta  # Minimum FCR full activation time (LER)
    t_FAT: pd.Timedelta  # Full activation time / transition time
    max_recover_time: pd.Timedelta  # Maximum recovery time after alert state


@dataclass
class SimulationSettings:
    """General simulation parameters."""
    working_resolution: pd.Timedelta
    ID_liquidity: float  # Probability of ID bid acceptance (0-1)
    freq_file: str  # Frequency input file path
    FRR_file: str  # FRR activation input file path
    scenario_name: str  # Name for result output
    do_min_cycling: bool  # Whether to ensure minimum cycling condition


@dataclass 
class ReserveProvisionSettings:
    """Reserve provision settings for a single BESS unit."""
    preset_FCR: List[float] = field(default_factory=list)
    preset_FRR_up: List[float] = field(default_factory=list)
    preset_FRR_down: List[float] = field(default_factory=list)
    vol_FRR: bool = True


@dataclass
class FleetReserveSettings:
    """Reserve provision settings for both BESS units."""
    # These will be populated after reading time-dependent settings
    preset_FCR_1: List[float] = field(default_factory=list)
    preset_FCR_2: List[float] = field(default_factory=list)
    preset_FRR_up_1: List[float] = field(default_factory=list)
    preset_FRR_up_2: List[float] = field(default_factory=list)
    preset_FRR_down_1: List[float] = field(default_factory=list)
    preset_FRR_down_2: List[float] = field(default_factory=list)
    vol_FRR_1: bool = True
    vol_FRR_2: bool = True


class ConfigurationManager:
    """
    Manages reading and parsing of simulation configuration from Excel files.
    """
    
    def __init__(self, settings_file: str = 'settings.xlsx'):
        """
        Initialize configuration manager.
        
        Args:
            settings_file: Path to the settings Excel file
        """
        self.settings_file = settings_file
        self._raw_settings = None
        self._load_raw_settings()
    
    def _load_raw_settings(self) -> None:
        """Load raw settings from Excel file."""
        self._raw_settings = pd.read_excel(
            self.settings_file, 0, 
            usecols="B:E", skiprows=2, nrows=54
        )
        # Clean up the dataframe
        self._raw_settings.drop(11, inplace=True)
        self._raw_settings.reset_index(inplace=True)
        self._raw_settings.drop('index', axis=1, inplace=True)
    
    def get_simulation_settings(self) -> SimulationSettings:
        """Extract general simulation settings."""
        settings = self._raw_settings
        
        working_resolution = pd.Timedelta(
            str(settings.BESS_1[16]) + ' ' + settings.Unit[16]
        )
        
        do_min_cycling = settings.BESS_1[10] == "yes"
        
        return SimulationSettings(
            working_resolution=working_resolution,
            ID_liquidity=settings.BESS_1[17] / 100,
            freq_file=settings.BESS_1[19],
            FRR_file=settings.BESS_1[20],
            scenario_name=settings.BESS_1[21],
            do_min_cycling=do_min_cycling
        )
    
    def get_bess_parameters(self, bess_id: int) -> BESSParameters:
        """
        Extract BESS technical parameters.
        
        Args:
            bess_id: 1 or 2 for BESS_1 or BESS_2
        
        Returns:
            BESSParameters dataclass with all technical parameters
        """
        settings = self._raw_settings
        col = 'BESS_1' if bess_id == 1 else 'BESS_2'
        
        # Row indices after drop(11) and reset_index:
        # 0: power_up, 1: power_down, 2: capacity
        # 3: min_SOC, 4: max_SOC
        # 5: ch_eff, 6: disch_eff, 7: rt_eff
        # 8: idle_loss, 9: min_cycle
        # 10: ensure_min_cycling, 11: header row
        # 12: SOC0, 13: LER, 14: live, 15: SOC_str
        
        # Handle round-trip efficiency
        rt_eff = settings[col][7]
        if safe_isnan(rt_eff):
            ch_eff = settings[col][5]
            disch_eff = settings[col][6]
        else:
            ch_eff = rt_eff
            disch_eff = 1.0
        
        # Handle idle loss
        idle_loss = settings[col][8]
        if safe_isnan(idle_loss):
            idle_loss = 0.0
        
        # Handle min_cycle
        min_cycle_val = settings[col][9]
        if safe_isnan(min_cycle_val):
            min_cycle_val = 0.0
        
        # LER and live status
        LER = settings[col][13] == "yes"
        live = settings[col][14] == "yes"
        
        # SOC strategy
        SOC_str = 0 if settings[col][15] == "Active" else 1
        
        return BESSParameters(
            power_up=settings[col][0],
            power_down=settings[col][1],
            capacity=settings[col][2],
            min_SOC=settings[col][3],
            max_SOC=settings[col][4],
            ch_eff=ch_eff,
            disch_eff=disch_eff,
            idle_loss=idle_loss,
            min_cycle=min_cycle_val,
            SOC0=settings[col][12],
            LER=LER,
            live=live,
            SOC_str=SOC_str,
            bess_id=bess_id,
            min_unit=settings.Unit[3],
            max_unit=settings.Unit[4],
            SOC_unit=settings.Unit[12]
        )
    
    def get_market_settings(self) -> MarketSettings:
        """Extract market timing settings."""
        settings = self._raw_settings
        
        GCT_FCR_cap = pd.to_datetime('2000-01-01 00:00:00') + pd.Timedelta(
            str(settings.BESS_1[33].hour) + ' h ' + 
            str(settings.BESS_1[33].minute) + ' min'
        )
        GCT_FRR_cap = pd.to_datetime('2000-01-01 00:00:00') + pd.Timedelta(
            str(settings.BESS_1[34].hour) + ' h ' + 
            str(settings.BESS_1[34].minute) + ' min'
        )
        
        return MarketSettings(
            GCT_FCR_cap=GCT_FCR_cap,
            GCT_FRR_cap=GCT_FRR_cap,
            GCT_FRR_en=pd.Timedelta(str(settings.BESS_1[37]) + 'min'),
            GCT_ID=pd.Timedelta(str(settings.BESS_1[38]) + 'min'),
            t_prep_ID=pd.Timedelta(str(settings.BESS_1[44]) + 'min'),
            t_prep_FCR_cap=pd.Timedelta(str(settings.BESS_1[41]) + 'min'),
            t_prep_FRR_cap=pd.Timedelta(str(settings.BESS_1[42]) + 'min'),
            t_prep_FRR_en=pd.Timedelta(str(settings.BESS_1[43]) + 'min')
        )
    
    def get_frequency_settings(self) -> FrequencySettings:
        """Extract frequency-related settings."""
        settings = self._raw_settings
        
        return FrequencySettings(
            nom_frequency=settings.BESS_1[47],
            max_deviation=settings.BESS_1[48],
            deadband=settings.BESS_1[49],
            t_min_FCR=pd.Timedelta(str(settings.BESS_1[50]) + 'min'),
            t_FAT=pd.Timedelta(str(settings.BESS_1[51]) + 'min'),
            max_recover_time=pd.Timedelta(str(settings.BESS_1[52]) + ' h')
        )
    
    def get_reserve_provision_settings(
        self, 
        bess_id: int
    ) -> ReserveProvisionSettings:
        """
        Extract reserve provision settings for a specific BESS.
        
        Args:
            bess_id: 1 or 2 for BESS_1 or BESS_2
        
        Returns:
            ReserveProvisionSettings with all reserve parameters for this BESS
        """
        settings = self._raw_settings
        
        # Calculate default ratio based on capacities
        # Using raw capacity values before efficiency adjustment
        bess_1_cap = settings.BESS_1[2]
        bess_2_cap = settings.BESS_2[2]
        def_ratio = bess_1_cap / (bess_1_cap + bess_2_cap)
        
        # Get fleet settings first
        fleet_settings = self._get_fleet_reserve_settings(def_ratio)
        
        # Return appropriate BESS settings
        if bess_id == 1:
            return ReserveProvisionSettings(
                preset_FCR=fleet_settings.preset_FCR_1,
                preset_FRR_up=fleet_settings.preset_FRR_up_1,
                preset_FRR_down=fleet_settings.preset_FRR_down_1,
                vol_FRR=fleet_settings.vol_FRR_1
            )
        else:
            return ReserveProvisionSettings(
                preset_FCR=fleet_settings.preset_FCR_2,
                preset_FRR_up=fleet_settings.preset_FRR_up_2,
                preset_FRR_down=fleet_settings.preset_FRR_down_2,
                vol_FRR=fleet_settings.vol_FRR_2
            )
    
    def _get_fleet_reserve_settings(
        self,
        def_ratio: float
    ) -> FleetReserveSettings:
        """
        Extract reserve provision settings for both BESS units.
        
        Args:
            def_ratio: Default ratio for splitting fleet reserves between BESS units
        
        Returns:
            FleetReserveSettings with all reserve parameters
        """
        settings = self._raw_settings
        result = FleetReserveSettings()
        
        # Time-invariant settings flags
        uniform_FCR_f = settings.Unit[24]
        uniform_FRR_f = settings.Unit[25]
        
        # Initialize with single values if uniform
        if settings.BESS_1[24] == 'yes':
            result.preset_FCR_1 = [settings.BESS_1[26]]
        if settings.BESS_2[24] == 'yes':
            result.preset_FCR_2 = [settings.BESS_2[26]]
        if settings.BESS_1[25] == 'yes':
            result.preset_FRR_up_1 = [settings.BESS_1[27]]
            result.preset_FRR_down_1 = [settings.BESS_1[28]]
        if settings.BESS_2[25] == 'yes':
            result.preset_FRR_up_2 = [settings.BESS_2[27]]
            result.preset_FRR_down_2 = [settings.BESS_2[28]]
        
        # Fleet-level uniform settings override individual
        if uniform_FCR_f == 'yes':
            preset_FCR_f = settings.Unit[26]
            result.preset_FCR_1 = [round(preset_FCR_f * def_ratio, 1)]
            result.preset_FCR_2 = [round(preset_FCR_f * (1 - def_ratio), 1)]
        
        if uniform_FRR_f == 'yes':
            preset_FRR_f_up = settings.Unit[27]
            preset_FRR_f_down = settings.Unit[28]
            result.preset_FRR_up_1 = [round(preset_FRR_f_up * def_ratio, 1)]
            result.preset_FRR_up_2 = [round(preset_FRR_f_up * (1 - def_ratio), 1)]
            result.preset_FRR_down_1 = [round(preset_FRR_f_down * def_ratio, 1)]
            result.preset_FRR_down_2 = [round(preset_FRR_f_down * (1 - def_ratio), 1)]
        
        # Read time-dependent settings from second sheet if needed
        self._load_time_dependent_reserves(result, settings, def_ratio, uniform_FCR_f, uniform_FRR_f)
        
        # Set voluntary FRR bid flags
        result.vol_FRR_1 = True
        result.vol_FRR_2 = True
        
        if settings.Unit[29] == "no":
            result.vol_FRR_1 = False
            result.vol_FRR_2 = False
        elif isinstance(settings.Unit[29], float):  # nan is float
            if settings.BESS_1[29] == "no":
                result.vol_FRR_1 = False
            if settings.BESS_2[29] == "no":
                result.vol_FRR_2 = False
        
        return result
    
    def _load_time_dependent_reserves(
        self,
        result: FleetReserveSettings,
        settings: pd.DataFrame,
        def_ratio: float,
        uniform_FCR_f: str,
        uniform_FRR_f: str
    ) -> None:
        """Load time-dependent reserve settings from second sheet."""
        
        # For fleet with time-varying settings
        if uniform_FCR_f == 'no' or uniform_FRR_f == 'no':
            obj = pd.read_excel(
                self.settings_file, 1, 
                usecols="C:E", skiprows=3, nrows=96
            )
            obj.columns = obj.columns.str.rstrip('.1')
            
            if 'FCR' in obj:
                preset_FCR_f = obj["FCR"]
                result.preset_FCR_1 = round(preset_FCR_f * def_ratio, 1).tolist()
                result.preset_FCR_2 = round(preset_FCR_f * (1 - def_ratio), 1).tolist()
            if 'FRR up' in obj:
                preset_FRR_up_f = obj["FRR up"]
                result.preset_FRR_up_1 = round(preset_FRR_up_f * def_ratio, 1).tolist()
                result.preset_FRR_up_2 = round(preset_FRR_up_f * (1 - def_ratio), 1).tolist()
            if 'FRR down' in obj:
                preset_FRR_down_f = obj["FRR down"]
                result.preset_FRR_down_1 = round(preset_FRR_down_f * def_ratio, 1).tolist()
                result.preset_FRR_down_2 = round(preset_FRR_down_f * (1 - def_ratio), 1).tolist()
        
        # For individual BESS time-varying settings
        if settings.BESS_1[24] == 'no' or settings.BESS_1[25] == 'no':
            obj = pd.read_excel(
                self.settings_file, 1, 
                usecols="C:E", skiprows=3, nrows=96
            )
            obj.columns = obj.columns.str.rstrip('.1')
            
            if 'FCR' in obj:
                result.preset_FCR_1 = obj["FCR"].tolist()
            if 'FRR up' in obj:
                result.preset_FRR_up_1 = obj["FRR up"].tolist()
            if 'FRR down' in obj:
                result.preset_FRR_down_1 = obj["FRR down"].tolist()
            
            obj = pd.read_excel(
                self.settings_file, 1, 
                usecols="G:I", skiprows=3, nrows=96
            )
            obj.columns = obj.columns.str.rstrip('.1')
            
            if 'FCR' in obj:
                result.preset_FCR_2 = obj["FCR"].tolist()
            if 'FRR up' in obj:
                result.preset_FRR_up_2 = obj["FRR up"].tolist()
            if 'FRR down' in obj:
                result.preset_FRR_down_2 = obj["FRR down"].tolist()
        
        # For if only BESS-2 has time-var settings
        if (settings.BESS_1[24] == 'yes' and settings.BESS_1[25] == 'yes' and 
            (settings.BESS_2[24] == 'no' or settings.BESS_2[25] == 'no')):
            obj = pd.read_excel(
                self.settings_file, 1, 
                usecols="C:E", skiprows=3, nrows=96
            )
            obj.columns = obj.columns.str.rstrip('.1')
            
            if 'FCR' in obj:
                result.preset_FCR_2 = obj["FCR"].tolist()
            if 'FRR up' in obj:
                result.preset_FRR_up_2 = obj["FRR up"].tolist()
            if 'FRR down' in obj:
                result.preset_FRR_down_2 = obj["FRR down"].tolist()
