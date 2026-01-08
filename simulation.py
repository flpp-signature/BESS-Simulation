# -*- coding: utf-8 -*-
"""
Simulation engine for BESS simulation.

This module contains the main simulation loop and orchestrates all
components of the BESS reserve provision simulation.
"""

import pandas as pd
import numpy as np
import random
from typing import Dict, List, Tuple, Optional

try:
    from .constants import MTU, HOUR, ONE_DAY, MIN_5, MIN_10, ENERGY_TOLERANCE
    from .utils import custom_print, true_round
    from .bess_model import BESS
    from .config import (
        SimulationSettings, MarketSettings, FrequencySettings,
        ReserveProvisionSettings
    )
except ImportError:    
    from constants import MTU, HOUR, ONE_DAY, MIN_5, MIN_10, ENERGY_TOLERANCE
    from utils import custom_print, true_round
    from bess_model import BESS
    from config import (
        SimulationSettings, MarketSettings, FrequencySettings,
        ReserveProvisionSettings
    )


class SimulationEngine:
    """
    Main simulation engine for BESS reserve provision simulation.
    
    This class orchestrates the time-step simulation, managing SOC,
    reserve activations, and market interactions.
    """
    
    def __init__(
        self,
        bess_1: BESS,
        bess_2: BESS,
        frequency: pd.Series,
        FRR_activ: pd.Series,
        time_indexes: pd.DatetimeIndex,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        sim_settings: SimulationSettings,
        market_settings: MarketSettings,
        freq_settings: FrequencySettings,
        log_name: str
    ):
        """
        Initialize simulation engine.
        
        Args:
            bess_1: First BESS model
            bess_2: Second BESS model
            frequency: Frequency timeseries
            FRR_activ: FRR activation timeseries
            time_indexes: Simulation time index
            start_time: Simulation start time
            end_time: Simulation end time
            sim_settings: Simulation settings
            market_settings: Market settings
            freq_settings: Frequency settings
            log_name: Path to log file
        """
        self.bess_1 = bess_1
        self.bess_2 = bess_2
        self.frequency = frequency
        self.FRR_activ = FRR_activ
        self.time_indexes = time_indexes
        self.start_time = start_time
        self.end_time = end_time
        self.sim_settings = sim_settings
        self.market_settings = market_settings
        self.freq_settings = freq_settings
        self.log_name = log_name
        
        # Working parameters
        self.working_resolution = sim_settings.working_resolution
        self.convert = self.working_resolution / HOUR
        self.convert_MTU = MTU / HOUR
        
        # Derived time parameters
        self.t_rec = (
            market_settings.t_prep_ID + market_settings.GCT_ID + MTU
        )
        self.t_res_exit = self.t_rec
        self.t_res_enter = self.t_rec
        self.t_FRR_look_ahead = (
            market_settings.t_prep_FRR_en + market_settings.GCT_FRR_en + MTU
        )
        
        # State variables
        self.alert_state = 0
        self.t_AS = pd.to_datetime('01-01-00')
        self.t_AS_over = pd.to_datetime('01-01-00')
        
        # Initialize output series
        self._init_output_series()
        
        # Calculate minimum cycling time if needed
        self._calc_min_cycling_params()
    
    def _init_output_series(self) -> None:
        """Initialize all output timeseries."""
        n_steps = int((self.end_time - self.start_time) / self.working_resolution)
        
        # Use float dtype to avoid FutureWarnings when assigning float values
        self.SOC_1 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.SOC_2 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.o_FCR_1 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.o_FCR_2 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.o_FRR_1 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.o_FRR_2 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.o_ID_1 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.o_ID_2 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.p_BESS_1 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.p_BESS_2 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.f_FCR_1 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.f_FCR_2 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.f_FRR_1 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.f_FRR_2 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.f_ID_1 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.f_ID_2 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.alert_status = pd.Series([0] * n_steps, self.time_indexes, dtype=int)
        self.pow_1 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.pow_2 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.res_1 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.res_2 = pd.Series([0.0] * n_steps, self.time_indexes, dtype=float)
        self.rec_1 = pd.Series([0] * n_steps, self.time_indexes, dtype=int)
        self.rec_2 = pd.Series([0] * n_steps, self.time_indexes, dtype=int)
    
    def _calc_min_cycling_params(self) -> None:
        """Calculate minimum cycling time parameters."""
        self.time_needed = pd.Timedelta('0')
        self.disch_prior = 1
        
        if ((self.bess_1.live and self.bess_1.min_cycle) or 
            (self.bess_2.live and self.bess_2.min_cycle)):
            
            # Time for BESS_1 charge/discharge cycle
            time_needed_1 = (
                self.bess_1.min_cycle / self.bess_1.power_down * 
                self.bess_1.ch_eff * self.bess_1.disch_eff + 
                self.bess_1.min_cycle / self.bess_1.power_up
            )
            
            # Time for BESS_2 to meet BESS_1 needs
            time_needed_2 = (
                self.bess_1.min_cycle / self.bess_2.power_up + 
                self.bess_1.min_cycle / self.bess_2.power_down * 
                self.bess_2.ch_eff * self.bess_2.disch_eff
            )
            
            # Time for BESS_2 charge/discharge cycle
            time_needed_3 = (
                self.bess_2.min_cycle / self.bess_2.power_down * 
                self.bess_2.ch_eff * self.bess_2.disch_eff + 
                self.bess_2.min_cycle / self.bess_2.power_up
            )
            
            # Time for BESS_1 to meet BESS_2 needs
            time_needed_4 = (
                self.bess_2.min_cycle / self.bess_1.power_up + 
                self.bess_2.min_cycle / self.bess_1.power_down * 
                self.bess_1.ch_eff * self.bess_1.disch_eff
            )
            
            self.time_needed = pd.Timedelta(
                str(max(time_needed_1, time_needed_2, 
                       time_needed_3, time_needed_4)) + ' hours'
            ).ceil(self.working_resolution)
            
            # Set priority for min cycling
            if self.bess_1.min_cycle > self.bess_2.min_cycle:
                self.disch_prior = 1
            else:
                self.disch_prior = 2
    
    def run(self) -> Dict:
        """
        Run the simulation.
        
        Returns:
            Dictionary containing all simulation results
        """
        custom_print(f'{self.start_time} → first time step', self.log_name)
        
        for t in self.time_indexes:
            self._simulate_timestep(t)
        
        custom_print(f'{t} → last time step\n', self.log_name)
        custom_print('simulation over...', self.log_name)
        
        return self._collect_results()
    
    def _simulate_timestep(self, t: pd.Timestamp) -> None:
        """
        Simulate a single timestep.
        
        Args:
            t: Current timestamp
        """
        # Record SOC at start of timestep
        self.SOC_1[t] = self.bess_1.SOC
        self.SOC_2[t] = self.bess_2.SOC
        
        # SOC management - ID trading decisions
        self._soc_management(t)
        
        # Get ID position
        m_ID = self._get_id_position(t)
        
        # Alert state management
        self._manage_alert_state(t)
        
        # LER recovery and reserve mode management
        self._manage_ler_modes(t)
        
        # Voluntary FRR bidding
        self._voluntary_frr_bidding(t)
        
        # FRR demand calculation
        m_FRR = self._calculate_frr_demand(t)
        
        # FCR demand calculation
        m_FCR = self._calculate_fcr_demand(t)
        
        # Energy management - delivery and failures
        self._energy_management(t, m_ID, m_FRR, m_FCR)
        
        # Minimum cycling management
        self._manage_min_cycling(t)
        
        # Record states
        self.alert_status[t] = self.alert_state
        self.rec_1[t] = self.bess_1.recovery_time
        self.rec_2[t] = self.bess_2.recovery_time
    
    def _soc_management(self, t: pd.Timestamp) -> None:
        """SOC management: prepare ID bids when decision time arrives."""
        ms = self.market_settings
        fs = self.freq_settings
        
        # Check if decision time for ID
        if t == t.ceil(MTU) - ((ms.t_prep_ID + ms.GCT_ID) % MTU):
            t_ID_next = (t + ms.t_prep_ID + ms.GCT_ID).floor(MTU)
            
            # Calculate worst-case and available energy
            E_worst_1 = self.bess_1.E_worst(
                0, t, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR
            )
            E_worst_2 = self.bess_2.E_worst(
                0, t, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR
            )
            E_avail_1 = self.bess_1.E_avail()
            E_avail_2 = self.bess_2.E_avail()
            
            ID_bid = [0, 0]
            
            # Check UP regulation insufficiency (need to charge)
            if E_worst_1[0] - E_avail_1[0] > ENERGY_TOLERANCE:
                max_pow_down = min(
                    -(self.bess_1.power_down - self.bess_1.cap_FCR[t_ID_next] - 
                      self.bess_1.cap_FRR_down[t_ID_next] - 
                      self.bess_1.en_FRR_down[t_ID_next]), 
                    0
                )
                ID_bid[0] = max(max_pow_down, -(E_worst_1[0] - E_avail_1[0]) * HOUR / MTU)
                if (true_round(E_worst_1[0] - E_avail_1[0], 2) > 
                    true_round(abs(ID_bid[0]) * MTU / HOUR, 2) and 
                    not self.alert_state and not self.bess_1.recovery_time):
                    custom_print(f'{t} → BESS 1 cannot prepare sufficient ID charge-bid for SOC management', self.log_name)
            
            if E_worst_2[0] - E_avail_2[0] > ENERGY_TOLERANCE:
                max_pow_down = min(
                    -(self.bess_2.power_down - self.bess_2.cap_FCR[t_ID_next] - 
                      self.bess_2.cap_FRR_down[t_ID_next] - 
                      self.bess_2.en_FRR_down[t_ID_next]), 
                    0
                )
                ID_bid[1] = max(max_pow_down, -(E_worst_2[0] - E_avail_2[0]) * HOUR / MTU)
                if (true_round(E_worst_2[0] - E_avail_2[0], 2) > 
                    true_round(abs(ID_bid[1]) * MTU / HOUR, 2) and 
                    not self.alert_state and not self.bess_1.recovery_time):
                    custom_print(f'{t} → BESS 2 cannot prepare sufficient ID charge-bid for SOC management', self.log_name)
            
            # Check DOWN regulation insufficiency (need to discharge)
            if E_worst_1[1] - E_avail_1[1] > ENERGY_TOLERANCE:
                max_pow_up = max(
                    self.bess_1.power_up - self.bess_1.cap_FCR[t_ID_next] - 
                    self.bess_1.cap_FRR_up[t_ID_next] - self.bess_1.en_FRR_up[t_ID_next], 
                    0
                )
                ID_bid[0] = min(max_pow_up, (E_worst_1[1] - E_avail_1[1]) * HOUR / MTU)
                if (true_round(E_worst_1[1] - E_avail_1[1], 2) > 
                    true_round(abs(ID_bid[0]) * MTU / HOUR, 2) and 
                    not self.alert_state and not self.bess_1.recovery_time):
                    custom_print(f'{t} → BESS 1 cannot prepare sufficient ID discharge-bid for SOC management', self.log_name)
            
            if E_worst_2[1] - E_avail_2[1] > ENERGY_TOLERANCE:
                max_pow_up = max(
                    self.bess_2.power_up - self.bess_2.cap_FCR[t_ID_next] - 
                    self.bess_2.cap_FRR_up[t_ID_next] - self.bess_2.en_FRR_up[t_ID_next], 
                    0
                )
                ID_bid[1] = min(max_pow_up, (E_worst_2[1] - E_avail_2[1]) * HOUR / MTU)
                if (true_round(E_worst_2[1] - E_avail_2[1], 2) > 
                    true_round(abs(ID_bid[1]) * MTU / HOUR, 2) and 
                    not self.alert_state and not self.bess_2.recovery_time):
                    custom_print(f'{t} → BESS 2 cannot prepare sufficient ID discharge-bid for SOC management', self.log_name)
            
            # Warning for infeasible situations
            if E_worst_1[0] > E_avail_1[0] and E_worst_1[1] > E_avail_1[1]:
                custom_print(f'{t} → Infeasible reserve obligations encountered for BESS-1 at intraday decision time', self.log_name)
                custom_print('Need both charge and discharge ID bids at the same time... attempting discharge bid only...', self.log_name)
            
            if E_worst_2[0] > E_avail_2[0] and E_worst_2[1] > E_avail_2[1]:
                custom_print(f'{t} → Infeasible reserve obligations encountered for BESS-2 at intraday decision time', self.log_name)
                custom_print('Need both charge and discharge ID bids at the same time... attempting discharge bid only...', self.log_name)
            
            # ID market clearing simulation
            ID_success = random.random() <= self.sim_settings.ID_liquidity
            
            # Store successful ID bids
            self.bess_1.en_ID[t_ID_next: t_ID_next + MTU - self.working_resolution] = ID_bid[0] * ID_success
            self.bess_2.en_ID[t_ID_next: t_ID_next + MTU - self.working_resolution] = ID_bid[1] * ID_success
    
    def _get_id_position(self, t: pd.Timestamp) -> List[float]:
        """Get ID position at current timestep."""
        m_ID = [-self.bess_1.en_ID[t], -self.bess_2.en_ID[t]]
        self.o_ID_1[t] = -m_ID[0]
        self.o_ID_2[t] = -m_ID[1]
        return m_ID
    
    def _manage_alert_state(self, t: pd.Timestamp) -> None:
        """Manage alert state transitions."""
        fs = self.freq_settings
        deviation = fs.nom_frequency - self.frequency[t]
        
        if not self.alert_state:
            # Check for Stage 2 Alert State
            if abs(deviation) > 0.1:
                t_first = max(self.start_time, t - pd.Timedelta('5 min'))
                if sum((fs.nom_frequency - self.frequency[t_first:t]).abs() <= 0.1) == 0:
                    self.alert_state = 1
            # Check for Stage 1 Alert State
            elif abs(deviation) > 0.05:
                t_first = max(self.start_time, t - pd.Timedelta('15 min'))
                if sum((fs.nom_frequency - self.frequency[t_first:t]).abs() <= 0.05) == 0:
                    self.alert_state = 1
            
            if self.alert_state:
                self.t_AS = t
                custom_print(f'{t} → ALERT STATE declared', self.log_name)
                
                # Start tracking TminLER
                if not self.bess_1.recovery_time:
                    self.bess_1.T_FCR = min(fs.max_deviation, abs(deviation)) * (not self.bess_1.reserve_mode) / fs.max_deviation * self.working_resolution
                    self.bess_1.TminLER_done = 0
                
                if not self.bess_2.recovery_time:
                    self.bess_2.T_FCR = min(fs.max_deviation, abs(deviation)) * (not self.bess_2.reserve_mode) / fs.max_deviation * self.working_resolution
                    self.bess_2.TminLER_done = 0
        else:
            # Exit Alert State if deviation is low
            if abs(deviation) <= 0.05:
                self.alert_state = 0
                self.t_AS_over = t
                custom_print(f'{t} → ALERT STATE revoked', self.log_name)
            else:
                # Track TminLER fulfillment
                if self.bess_1.LER:
                    if self.bess_1.T_FCR < fs.t_min_FCR and not self.bess_1.recovery_time:
                        self.bess_1.T_FCR += min(fs.max_deviation, abs(deviation)) * (not self.bess_1.reserve_mode) / fs.max_deviation * self.working_resolution
                
                if self.bess_2.LER:
                    if self.bess_2.T_FCR < fs.t_min_FCR and not self.bess_2.recovery_time:
                        self.bess_2.T_FCR += min(fs.max_deviation, abs(deviation)) * (not self.bess_2.reserve_mode) / fs.max_deviation * self.working_resolution
    
    def _manage_ler_modes(self, t: pd.Timestamp) -> None:
        """Manage LER recovery and reserve mode."""
        ms = self.market_settings
        fs = self.freq_settings
        
        if self.bess_1.live and self.bess_1.LER and any(self.bess_1.cap_FCR > 0):
            self.bess_1.check_recovery(t, self.t_AS_over, self.t_rec, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR, fs.max_recover_time, self.log_name)
            self.bess_1.reserve_mode_act(t, self.t_AS, self.alert_state, self.t_res_enter, self.t_res_exit, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR, self.log_name)
        
        if self.bess_2.live and self.bess_2.LER and any(self.bess_2.cap_FCR > 0):
            self.bess_2.check_recovery(t, self.t_AS_over, self.t_rec, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR, fs.max_recover_time, self.log_name)
            self.bess_2.reserve_mode_act(t, self.t_AS, self.alert_state, self.t_res_enter, self.t_res_exit, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR, self.log_name)
    
    def _voluntary_frr_bidding(self, t: pd.Timestamp) -> None:
        """Handle voluntary FRR bidding at decision time."""
        ms = self.market_settings
        fs = self.freq_settings
        
        # Check if decision time for FRR energy
        if t == t.ceil(MTU) - ((ms.t_prep_FRR_en + ms.GCT_FRR_en) % MTU):
            t_FRR_next = (t + ms.t_prep_FRR_en + ms.GCT_FRR_en).floor(MTU)
            
            self.bess_1.volunt_FRR(t, t_FRR_next, self.t_FRR_look_ahead, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR, self.convert_MTU)
            self.bess_2.volunt_FRR(t, t_FRR_next, self.t_FRR_look_ahead, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR, self.convert_MTU)
    
    def _calculate_frr_demand(self, t: pd.Timestamp) -> List[float]:
        """Calculate FRR demand for both BESS units."""
        m_FRR = [0, 0]
        
        # UP regulation
        total_FRR_up = self.bess_1.cap_FRR_up[t] + self.bess_1.en_FRR_up[t] + self.bess_2.cap_FRR_up[t] + self.bess_2.en_FRR_up[t]
        
        if self.FRR_activ[t] > 0 and total_FRR_up != 0:
            m_FRR_temp = min(self.FRR_activ[t], total_FRR_up)
            ratio_1 = (self.bess_1.cap_FRR_up[t] + self.bess_1.en_FRR_up[t]) / total_FRR_up
            m_FRR[0] = round(m_FRR_temp * ratio_1, 1)
            m_FRR[1] = round(m_FRR_temp - m_FRR[0], 1)
            self.o_FRR_1[t] = m_FRR[0]
            self.o_FRR_2[t] = m_FRR[1]
        
        # DOWN regulation
        total_FRR_down = self.bess_1.cap_FRR_down[t] + self.bess_1.en_FRR_down[t] + self.bess_2.cap_FRR_down[t] + self.bess_2.en_FRR_down[t]
        
        if self.FRR_activ[t] < 0 and total_FRR_down != 0:
            m_FRR_temp = -min(abs(self.FRR_activ[t]), abs(total_FRR_down))
            ratio_1 = (self.bess_1.cap_FRR_down[t] + self.bess_1.en_FRR_down[t]) / total_FRR_down
            m_FRR[0] = round(m_FRR_temp * ratio_1, 1)
            m_FRR[1] = round(m_FRR_temp - m_FRR[0], 1)
            self.o_FRR_1[t] = m_FRR[0]
            self.o_FRR_2[t] = m_FRR[1]
        
        # Change signs (from BESS POV it's the other way)
        m_FRR = np.negative(m_FRR)
        return m_FRR
    
    def _calculate_fcr_demand(self, t: pd.Timestamp) -> List[float]:
        """Calculate FCR demand for both BESS units."""
        fs = self.freq_settings
        deviation = fs.nom_frequency - self.frequency[t]
        m_FCR = [0, 0]
        
        if abs(deviation) >= fs.deadband:
            m_FCR[0], self.res_1[t] = self.bess_1.FCR_demand(t, deviation, fs.max_deviation, self.frequency, fs.t_FAT)
            m_FCR[1], self.res_2[t] = self.bess_2.FCR_demand(t, deviation, fs.max_deviation, self.frequency, fs.t_FAT)
        
        # Save obligations
        self.o_FCR_1[t] = -m_FCR[0]
        self.o_FCR_2[t] = -m_FCR[1]
        
        return m_FCR
    
    def _energy_management(self, t: pd.Timestamp, m_ID: List[float], m_FRR: List[float], m_FCR: List[float]) -> None:
        """Manage energy delivery and handle failures."""
        # BESS-1 delivery
        self._bess_energy_delivery(t, self.bess_1, m_ID[0], m_FRR[0], m_FCR[0], self.f_FCR_1, self.f_FRR_1, self.f_ID_1, self.pow_1, 1)
        
        # BESS-2 delivery
        self._bess_energy_delivery(t, self.bess_2, m_ID[1], m_FRR[1], m_FCR[1], self.f_FCR_2, self.f_FRR_2, self.f_ID_2, self.pow_2, 2)
    
    def _bess_energy_delivery(self, t: pd.Timestamp, bess: BESS, m_ID: float, m_FRR: float, m_FCR: float, f_FCR: pd.Series, f_FRR: pd.Series, f_ID: pd.Series, pow_series: pd.Series, bess_id: int) -> None:
        """Handle energy delivery for a single BESS."""
        # Calculate losses
        loss = bess.disch_eff * bess.SOC * bess.idle_loss / 100 / (ONE_DAY / self.working_resolution)
        
        full_energy = (m_FCR + m_FRR + m_ID) * self.convert - loss
        
        # Check if within SOC limits
        new_soc = bess.SOC + bess.energy_recalc(full_energy, 0)
        
        if true_round(bess.min_SOC, 6) <= true_round(new_soc, 6) <= true_round(bess.max_SOC, 6):
            # Everything OK
            bess.new_SOC(full_energy)
        else:
            # Handle over-discharge or over-charge
            if bess.min_SOC > new_soc:
                # Discharge too much
                avail_energy = bess.energy_recalc(bess.min_SOC - bess.SOC, 1)
                difference = full_energy - avail_energy
                
                if abs(round(difference / self.convert, 3)) > 0:
                    custom_print(f'{t} → BESS {bess_id} cannot fully discharge! Output power reduced by {-round(difference / self.convert, 3)} MW', self.log_name)
                
                bess.new_SOC(avail_energy)
                
                # Fail deliveries in order: ID, FRR, FCR
                if m_ID < 0:
                    f_ID[t] = -max(difference / self.convert, m_ID)
                    difference += f_ID[t] * self.convert
                if m_FRR < 0 and difference < 0:
                    f_FRR[t] = -max(difference / self.convert, m_FRR)
                    difference += f_FRR[t] * self.convert
                if m_FCR < 0 and difference < 0:
                    f_FCR[t] = -max(difference / self.convert, m_FCR)
                    difference += f_FCR[t] * self.convert
                
                if true_round(difference, 3) < 0:
                    custom_print(f'{t} → This should not be possible. Missing energy equal to {difference} MWh', self.log_name)
            else:
                # Charge too much
                avail_energy = bess.energy_recalc(bess.max_SOC - bess.SOC, 1)
                difference = full_energy - avail_energy
                
                if abs(round(difference / self.convert, 3)) > 0:
                    custom_print(f'{t} → BESS {bess_id} cannot fully charge! Input power reduced by {round(difference / self.convert, 3)} MW', self.log_name)
                
                bess.new_SOC(avail_energy)
                
                # Fail deliveries in order: ID, FRR, FCR
                if m_ID > 0:
                    f_ID[t] = -min(difference / self.convert, m_ID)
                    difference += f_ID[t] * self.convert
                if m_FRR > 0 and difference > 0:
                    f_FRR[t] = -min(difference / self.convert, m_FRR)
                    difference += f_FRR[t] * self.convert
                if m_FCR > 0 and difference > 0:
                    f_FCR[t] = -min(difference / self.convert, m_FCR)
                    difference += f_FCR[t] * self.convert
                
                if true_round(difference, 3) > 0:
                    custom_print(f'{t} → This should not be possible. Missing energy equal to {difference} MWh', self.log_name)
        
        # Calculate total power
        if bess_id == 1:
            pow_series[t] = self.o_FCR_1[t] + self.o_FRR_1[t] + self.o_ID_1[t] - f_FCR[t] - f_FRR[t] - f_ID[t]
        else:
            pow_series[t] = self.o_FCR_2[t] + self.o_FRR_2[t] + self.o_ID_2[t] - f_FCR[t] - f_FRR[t] - f_ID[t]
    
    def _manage_min_cycling(self, t: pd.Timestamp) -> None:
        """Manage minimum cycling requirements."""
        do_min_cycling = self.sim_settings.do_min_cycling
        
        # BESS-to-BESS exchange for minimum cycling
        if (do_min_cycling and not self.alert_state and 
            (self.bess_1.min_cycle > 0 or self.bess_2.min_cycle > 0) and 
            self.bess_1.live and self.bess_2.live and 
            not self.bess_1.recovery_time and not self.bess_2.recovery_time):
            
            if t >= self.start_time + ONE_DAY - self.time_needed:
                self._perform_min_cycling(t)
        
        # Check minimum cycling fulfillment
        self._check_min_cycling_fulfillment(t)
    
    def _perform_min_cycling(self, t: pd.Timestamp) -> None:
        """Perform BESS-to-BESS energy exchange for minimum cycling."""
        ms = self.market_settings
        fs = self.freq_settings
        
        start_point = max(self.start_time, t - ONE_DAY + self.time_needed)
        
        # Calculate discharge sums
        sum_en_1 = sum([en if en > 0 else 0 for en in self.pow_1[start_point: t]]) * self.convert
        sum_en_2 = sum([en if en > 0 else 0 for en in self.pow_2[start_point: t]]) * self.convert
        
        to_discharge_1 = self.bess_1.min_cycle - sum_en_1
        to_discharge_2 = self.bess_2.min_cycle - sum_en_2
        
        to_discharge_extra_1 = max(to_discharge_1, to_discharge_2 / self.bess_2.ch_eff)
        to_discharge_extra_2 = max(to_discharge_2, to_discharge_1 / self.bess_1.ch_eff)
        
        if to_discharge_extra_1 > ENERGY_TOLERANCE or to_discharge_extra_2 > ENERGY_TOLERANCE:
            # Calculate free energy
            free_energy_up_1 = self.bess_1.E_avail()[0] - self.bess_1.E_worst(0, t, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR)[0]
            free_energy_down_1 = self.bess_1.E_avail()[1] - self.bess_1.E_worst(0, t, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR)[1]
            free_energy_up_2 = self.bess_2.E_avail()[0] - self.bess_2.E_worst(0, t, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR)[0]
            free_energy_down_2 = self.bess_2.E_avail()[1] - self.bess_2.E_worst(0, t, ms.t_prep_ID, ms.GCT_ID, fs.t_FAT, fs.t_min_FCR)[1]
            
            if to_discharge_extra_1 > ENERGY_TOLERANCE and (self.disch_prior == 1 or to_discharge_extra_2 <= -ENERGY_TOLERANCE):
                # Discharge BESS-1, charge BESS-2
                avail_power = min(
                    free_energy_up_1 / self.convert,
                    self.bess_1.power_up - self.pow_1[t],
                    free_energy_down_2 / self.convert,
                    self.bess_2.power_down + self.pow_2[t],
                    to_discharge_extra_1 / self.convert
                )
                avail_energy = avail_power * self.convert
                
                if avail_power > 0.1:
                    self.pow_1[t] += avail_power
                    self.pow_2[t] -= avail_power
                    self.bess_1.new_SOC(-avail_energy)
                    self.bess_2.new_SOC(avail_energy)
                    self.disch_prior = 1
                else:
                    self.disch_prior = 2
            
            elif to_discharge_extra_2 > ENERGY_TOLERANCE:
                # Discharge BESS-2, charge BESS-1
                avail_power = min(
                    free_energy_down_1 / self.convert,
                    self.bess_1.power_down + self.pow_1[t],
                    free_energy_up_2 / self.convert,
                    self.bess_2.power_up - self.pow_2[t],
                    to_discharge_extra_2 / self.convert
                )
                avail_energy = avail_power * self.convert
                
                if avail_power > 0.1:
                    self.pow_1[t] -= avail_power
                    self.pow_2[t] += avail_power
                    self.bess_1.new_SOC(avail_energy)
                    self.bess_2.new_SOC(-avail_energy)
                    self.disch_prior = 2
                else:
                    self.disch_prior = 1
    
    def _check_min_cycling_fulfillment(self, t: pd.Timestamp) -> None:
        """Check and log minimum cycling fulfillment."""
        if self.bess_1.min_cycle > 0 or self.bess_2.min_cycle > 0:
            # BESS-1 check
            if t >= self.start_time + ONE_DAY - self.working_resolution and self.bess_1.min_cycle > 0 and self.bess_1.live:
                sum_en_1 = sum([en if en > 0 else 0 for en in self.pow_1[t - ONE_DAY + self.working_resolution: t]]) * self.convert
                
                if self.bess_1.min_cycle - sum_en_1 > ENERGY_TOLERANCE:
                    custom_print(f'{t} → BESS-1 24-hour minimum cycling fulfilled by {round(100 * sum_en_1 / self.bess_1.min_cycle, 2)}%', self.log_name)
            
            # BESS-2 check
            if t >= self.start_time + ONE_DAY - self.working_resolution and self.bess_2.min_cycle > 0 and self.bess_2.live:
                sum_en_2 = sum([en if en > 0 else 0 for en in self.pow_2[t - ONE_DAY + self.working_resolution: t]]) * self.convert
                
                if self.bess_2.min_cycle - sum_en_2 > ENERGY_TOLERANCE:
                    custom_print(f'{t} → BESS-2 24-hour minimum cycling fulfilled by {round(100 * sum_en_2 / self.bess_2.min_cycle, 2)}%', self.log_name)
    
    def _collect_results(self) -> Dict:
        """Collect all simulation results."""
        return {
            'SOC_1': self.SOC_1,
            'SOC_2': self.SOC_2,
            'o_FCR_1': self.o_FCR_1,
            'o_FCR_2': self.o_FCR_2,
            'o_FRR_1': self.o_FRR_1,
            'o_FRR_2': self.o_FRR_2,
            'o_ID_1': self.o_ID_1,
            'o_ID_2': self.o_ID_2,
            'f_FCR_1': self.f_FCR_1,
            'f_FCR_2': self.f_FCR_2,
            'f_FRR_1': self.f_FRR_1,
            'f_FRR_2': self.f_FRR_2,
            'f_ID_1': self.f_ID_1,
            'f_ID_2': self.f_ID_2,
            'pow_1': self.pow_1,
            'pow_2': self.pow_2,
            'res_1': self.res_1,
            'res_2': self.res_2,
            'rec_1': self.rec_1,
            'rec_2': self.rec_2,
            'alert_status': self.alert_status,
            'frequency': self.frequency,
            'bess_1': self.bess_1,
            'bess_2': self.bess_2,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'time_indexes': self.time_indexes
        }
