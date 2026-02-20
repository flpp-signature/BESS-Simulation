# -*- coding: utf-8 -*-
"""
BESS (Battery Energy Storage System) model class.

This module contains the core BESS class that models the behavior of a
battery energy storage system participating in FCR and FRR reserve markets.
"""

import pandas as pd
import numpy as np
import math
from typing import List, Tuple, Optional

try:
    from .constants import MTU, HOUR, ONE_DAY, MIN_5, MIN_10, ENERGY_TOLERANCE
    from .config import BESSParameters
except ImportError:
    from constants import MTU, HOUR, ONE_DAY, MIN_5, MIN_10, ENERGY_TOLERANCE
    from config import BESSParameters


def safe_isnan(value) -> bool:
    """Safely check if a value is NaN, handling non-numeric types."""
    try:
        return pd.isna(value) or np.isnan(float(value))
    except (TypeError, ValueError):
        return pd.isna(value)


class BESS:
    """
    Battery Energy Storage System model.
    
    This class represents a single BESS unit with its technical parameters,
    state variables, and methods for reserve provision calculations.
    
    Attributes:
        power_up: Maximum discharge power (MW)
        power_down: Maximum charge power (MW) 
        capacity: Energy capacity (MWh)
        min_SOC: Minimum allowed SOC (MWh)
        max_SOC: Maximum allowed SOC (MWh)
        ch_eff: Charging efficiency (0-1)
        disch_eff: Discharging efficiency (0-1)
        idle_loss: Self-discharge rate (%/day)
        min_cycle: Minimum cycling requirement (MWh)
        SOC: Current state of charge (MWh)
        reserve_mode: Current reserve mode status (0 or 1)
        recovery_time: Recovery status (0 or 1)
        LER: Whether qualified as LER
        ID: BESS identifier
        live: Whether BESS is active
        SOC_str: SOC management strategy (0=Active, 1=Conservative)
    """
    
    def __init__(
        self,
        params: BESSParameters,
        reserve_settings,  # ReserveProvisionSettings
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        MTUs_24h: pd.DatetimeIndex,
        working_resolution: pd.Timedelta,
        bess_id: int = 1
    ):
        """
        Initialize BESS model.
        
        Args:
            params: BESSParameters dataclass with technical parameters
            reserve_settings: ReserveProvisionSettings with reserve capacities
            start_time: Simulation start time
            end_time: Simulation end time
            MTUs_24h: DatetimeIndex for 24-hour MTU timestamps
            working_resolution: Simulation time resolution
            bess_id: BESS identifier (1 or 2)
        """
        # Handle efficiency settings
        self.ch_eff = params.ch_eff
        self.disch_eff = params.disch_eff
        
        # Store capacity accounting for efficiency
        # In settings, capacity denotes dischargeable energy,
        # but in calculations we need stored energy
        capacity = params.capacity / self.disch_eff
        
        self.power_up = params.power_up
        self.power_down = params.power_down
        self.capacity = capacity
        
        # Handle SOC limits based on unit type
        if params.min_unit == "%":
            self.min_SOC = params.min_SOC / 100 * capacity
        else:
            self.min_SOC = params.min_SOC / self.disch_eff
        
        if params.max_unit == "%":
            self.max_SOC = params.max_SOC / 100 * capacity
        else:
            self.max_SOC = params.max_SOC / self.disch_eff
        
        # Handle idle loss
        self.idle_loss = params.idle_loss if not safe_isnan(params.idle_loss) else 0
        
        # Handle minimum cycling
        self.min_cycle = params.min_cycle * capacity * self.disch_eff
        if safe_isnan(params.min_cycle):
            self.min_cycle = 0
        
        # Set initial SOC
        if params.SOC_unit == "%":
            self.SOC = params.SOC0 / 100 * capacity
        else:
            self.SOC = params.SOC0 / self.disch_eff
        
        # State variables
        self.reserve_mode = 0
        self.recovery_time = 0
        self.t_RM = start_time  # Timestamp of Reserve Mode initialization
        self.t_NM = start_time  # Timestamp of Normal Mode restoration
        self.t_RT = start_time  # Recovery time tracker
        self.max_recover_time = pd.Timedelta('0')  # Will be set during recovery
        
        # LER-specific attributes
        self.LER = params.LER
        self.T_FCR = pd.Timedelta('0')  # TminLER counter
        self.TminLER_done = 0  # Flag for TminLER completion
        
        # General attributes
        self.ID = bess_id
        self.live = 1 if params.live else 0
        self.SOC_str = 0 if params.SOC_str == 0 else 1
        
        # Set preset capacity values from reserve settings
        self.preset_FCR = reserve_settings.preset_FCR if reserve_settings.preset_FCR else [0]
        self.preset_FRR_up = reserve_settings.preset_FRR_up if reserve_settings.preset_FRR_up else [0]
        self.preset_FRR_down = reserve_settings.preset_FRR_down if reserve_settings.preset_FRR_down else [0]
        self.vol_FRR = reserve_settings.vol_FRR
        
        # Store MTUs_24h for later use
        self._MTUs_24h = MTUs_24h
        
        # Initialize capacity timeseries
        self._init_capacity_timeseries(
            start_time, end_time, MTUs_24h, working_resolution
        )
        
        # Store working resolution for calculations
        self._working_resolution = working_resolution
        self._start_time = start_time
        self._end_time = end_time
    
    def _init_capacity_timeseries(
        self,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        MTUs_24h: pd.DatetimeIndex,
        working_resolution: pd.Timedelta
    ) -> None:
        """Initialize capacity and energy bid timeseries."""
        next_day = pd.Timedelta('1 d')
        
        # Initialize with two days of zeros
        self.en_FRR_up = pd.concat([
            pd.Series([0.0] * len(MTUs_24h), MTUs_24h),
            pd.Series([0.0] * len(MTUs_24h), MTUs_24h + next_day)
        ])
        self.en_FRR_down = pd.concat([
            pd.Series([0.0] * len(MTUs_24h), MTUs_24h),
            pd.Series([0.0] * len(MTUs_24h), MTUs_24h + next_day)
        ])
        self.en_ID = pd.concat([
            pd.Series([0.0] * len(MTUs_24h), MTUs_24h),
            pd.Series([0.0] * len(MTUs_24h), MTUs_24h + next_day)
        ])
        
        # Extend for larger simulation datasets
        while self.en_FRR_up.tail(1).index[0] < end_time + ONE_DAY:
            next_day += pd.Timedelta('1 d')
            self.en_FRR_up = pd.concat([
                self.en_FRR_up, 
                pd.Series([0.0] * len(MTUs_24h), MTUs_24h + next_day)
            ])
            self.en_FRR_down = pd.concat([
                self.en_FRR_down, 
                pd.Series([0.0] * len(MTUs_24h), MTUs_24h + next_day)
            ])
            self.en_ID = pd.concat([
                self.en_ID, 
                pd.Series([0.0] * len(MTUs_24h), MTUs_24h + next_day)
            ])
        
        # Resample to working resolution
        self.en_FRR_up = self.en_FRR_up.resample(working_resolution).ffill()
        self.en_FRR_down = self.en_FRR_down.resample(working_resolution).ffill()
        self.en_ID = self.en_ID.resample(working_resolution).ffill()
    
    def FCR_series_init(
        self, 
        start_time: pd.Timestamp = None, 
        end_time: pd.Timestamp = None,
        working_resolution: pd.Timedelta = None
    ) -> None:
        """
        Initialize FCR capacity timeseries.
        
        Args:
            start_time: Override start time (optional)
            end_time: Override end time (optional)
            working_resolution: Override working resolution (optional)
        """
        MTUs_24h = self._MTUs_24h
        start_time = start_time or self._start_time
        end_time = end_time or self._end_time
        working_resolution = working_resolution or self._working_resolution
        
        next_day = pd.Timedelta('1 d')
        
        if self.live:
            if len(self.preset_FCR) > 1:
                cap_FCR_temp = pd.Series(self.preset_FCR, MTUs_24h)
            else:
                cap_FCR_temp = pd.Series(
                    self.preset_FCR * len(MTUs_24h), MTUs_24h
                )
        else:
            cap_FCR_temp = pd.Series([0.0] * len(MTUs_24h), MTUs_24h)
        
        self.cap_FCR = cap_FCR_temp[start_time <= cap_FCR_temp.index]
        self.cap_FCR = pd.concat([
            self.cap_FCR, 
            pd.Series(cap_FCR_temp.values, MTUs_24h + next_day)
        ])
        
        # Extend for larger simulation datasets
        while self.cap_FCR.tail(1).index[0] < end_time + ONE_DAY:
            next_day += pd.Timedelta('1 d')
            self.cap_FCR = pd.concat([
                self.cap_FCR, 
                pd.Series(cap_FCR_temp.values, MTUs_24h + next_day)
            ])
        
        self.cap_FCR = self.cap_FCR.resample(working_resolution).ffill()
    
    def FRR_series_init(
        self,
        start_time: pd.Timestamp = None,
        end_time: pd.Timestamp = None,
        working_resolution: pd.Timedelta = None
    ) -> None:
        """
        Initialize FRR capacity timeseries.
        
        Args:
            start_time: Override start time (optional)
            end_time: Override end time (optional)
            working_resolution: Override working resolution (optional)
        """
        MTUs_24h = self._MTUs_24h
        start_time = start_time or self._start_time
        end_time = end_time or self._end_time
        working_resolution = working_resolution or self._working_resolution
        
        next_day = pd.Timedelta('1 d')
        
        if self.live:
            if len(self.preset_FRR_up) > 1:
                cap_FRR_up_temp = pd.Series(self.preset_FRR_up, MTUs_24h)
                cap_FRR_down_temp = pd.Series(self.preset_FRR_down, MTUs_24h)
            else:
                cap_FRR_up_temp = pd.Series(
                    self.preset_FRR_up * len(MTUs_24h), MTUs_24h
                )
                cap_FRR_down_temp = pd.Series(
                    self.preset_FRR_down * len(MTUs_24h), MTUs_24h
                )
        else:
            cap_FRR_up_temp = pd.Series([0.0] * len(MTUs_24h), MTUs_24h)
            cap_FRR_down_temp = pd.Series([0.0] * len(MTUs_24h), MTUs_24h)
        
        self.cap_FRR_up = cap_FRR_up_temp[
            start_time <= cap_FRR_up_temp.index
        ]
        self.cap_FRR_down = cap_FRR_down_temp[
            start_time <= cap_FRR_down_temp.index
        ]
        
        self.cap_FRR_up = pd.concat([
            self.cap_FRR_up, 
            pd.Series(cap_FRR_up_temp.values, MTUs_24h + pd.Timedelta('1 d'))
        ])
        self.cap_FRR_down = pd.concat([
            self.cap_FRR_down, 
            pd.Series(cap_FRR_down_temp.values, MTUs_24h + pd.Timedelta('1 d'))
        ])
        
        # Extend for larger simulation datasets
        while self.cap_FRR_up.tail(1).index[0] < end_time + ONE_DAY:
            next_day += pd.Timedelta('1 d')
            self.cap_FRR_up = pd.concat([
                self.cap_FRR_up, 
                pd.Series(cap_FRR_up_temp.values, MTUs_24h + next_day)
            ])
            self.cap_FRR_down = pd.concat([
                self.cap_FRR_down, 
                pd.Series(cap_FRR_down_temp.values, MTUs_24h + next_day)
            ])
        
        self.cap_FRR_up = self.cap_FRR_up.resample(
            working_resolution
        ).ffill()
        self.cap_FRR_down = self.cap_FRR_down.resample(
            working_resolution
        ).ffill()
    
    # =========================================================================
    # Energy Calculation Methods
    # =========================================================================
    
    def energy_recalc(self, energy: float, from_BESS: int) -> float:
        """
        Recalculate energy accounting for efficiency losses.
        
        Args:
            energy: Energy amount (positive = charge, negative = discharge)
            from_BESS: 1 if calculating from BESS perspective, 0 if from grid
        
        Returns:
            Energy amount adjusted for efficiency
        """
        if energy > 0:  # charge
            SOC_change = (
                energy * self.ch_eff * (1 - from_BESS) + 
                energy / self.ch_eff * from_BESS
            )
        else:  # discharge
            SOC_change = (
                energy / self.disch_eff * (1 - from_BESS) + 
                energy * self.disch_eff * from_BESS
            )
        return SOC_change
    
    def new_SOC(self, energy: float) -> None:
        """
        Update SOC based on energy exchange.
        
        Args:
            energy: Energy exchanged (positive = charge, negative = discharge)
        """
        self.SOC += self.energy_recalc(energy, 0)
    
    def E_avail(self) -> List[float]:
        """
        Calculate available energy for up and down regulation.
        
        Returns:
            List of [E_avail_up, E_avail_down] in MWh
        """
        E_avail_up = (self.SOC - self.min_SOC) * self.disch_eff
        E_avail_down = (self.max_SOC - self.SOC) / self.ch_eff
        return [E_avail_up, E_avail_down]
    
    def FCR_alter(
        self, 
        t_end: pd.Timestamp, 
        after_alert: pd.Timedelta,
        t: pd.Timestamp,
        t_FAT: pd.Timedelta,
        t_min_FCR: pd.Timedelta
    ) -> float:
        """
        Calculate worst-case FCR delivery for LER alternative scenario.
        
        This implements the special LER FCR activation calculation that
        considers the stepped activation pattern before and during Alert State.
        
        Args:
            t_end: End time for calculation
            after_alert: Time remaining after alert state
            t: Current time
            t_FAT: Full activation time
            t_min_FCR: Minimum FCR duration
        
        Returns:
            Worst-case FCR energy requirement
        """
        working_resolution = self._working_resolution
        
        t_100 = t_end + working_resolution - t_FAT - t_min_FCR - MIN_5
        t_100_prim = max(t_100, t)
        add_1 = sum(self.cap_FCR[t_100_prim: t_end])
        
        if t_100 > t:  # Room for 50% activation
            t_50 = t_100_prim - MIN_10
            t_50_prim = max(t_50, t)
            add_1 += 0.5 * sum(self.cap_FCR[t_50_prim: t_100_prim - working_resolution])
            
            if t_50 > t:  # Room for 25% activation
                add_1 += 0.25 * sum(self.cap_FCR[t: t_50_prim - working_resolution])
        
        if after_alert > pd.Timedelta('0'):
            # Add 25% activation after Alert State
            add_1 += 0.25 * sum(self.cap_FCR[t_end + working_resolution: t_end + after_alert])
        
        return add_1
    
    def E_worst(
        self, 
        t_look: pd.Timedelta,
        t: pd.Timestamp,
        t_prep_ID: pd.Timedelta,
        GCT_ID: pd.Timedelta,
        t_FAT: pd.Timedelta,
        t_min_FCR: pd.Timedelta
    ) -> List[float]:
        """
        Calculate worst-case energy requirements for up and down regulation.
        
        Args:
            t_look: Look-ahead time (0 for ID management, timedelta otherwise)
            t: Current time
            t_prep_ID: ID preparation time
            GCT_ID: ID gate closure time
            t_FAT: Full activation time
            t_min_FCR: Minimum FCR duration
        
        Returns:
            List of [E_worst_up, E_worst_down] in MWh
        """
        working_resolution = self._working_resolution
        
        if self.live:
            time_idx_1 = t
            LER_flag = self.LER
            
            if t_look == 0:
                time_idx_3 = t + t_prep_ID + GCT_ID + MTU - working_resolution
                if self.LER:
                    LER_flag = self.SOC_str
            else:
                time_idx_3 = t + t_look - working_resolution
            
            add_1 = 0
            
            if LER_flag:  # Lower worst-case for LER
                # Check if all FCR values are equal and nonzero
                if (self.cap_FCR[time_idx_1: time_idx_3] == 
                    self.cap_FCR[time_idx_1]).all():
                    add_1 = self.FCR_alter(
                        time_idx_3, pd.Timedelta('0'), t, t_FAT, t_min_FCR
                    )
                elif not (self.cap_FCR[time_idx_1: time_idx_3] == 0).all():
                    # Full enumeration needed
                    t_end = time_idx_3
                    while t_end >= t + MIN_5 + t_min_FCR + t_FAT - working_resolution:
                        add_1 = max(
                            add_1, 
                            self.FCR_alter(
                                t_end, time_idx_3 - t_end, t, t_FAT, t_min_FCR
                            )
                        )
                        t_end = t_end - working_resolution
            else:
                add_1 = sum(self.cap_FCR[t: time_idx_3])
            
            add_2 = self.cap_FRR_up[t: time_idx_3]
            add_3 = self.cap_FRR_down[t: time_idx_3]
            add_4 = self.en_FRR_up[t: time_idx_3]
            add_5 = self.en_FRR_down[t: time_idx_3]
            add_6 = self.en_ID[t: time_idx_3]
            
            # Self-discharge losses
            add_7 = (
                0 * add_6 + 
                self.disch_eff * self.idle_loss / 100 * self.max_SOC / 
                (ONE_DAY / working_resolution)
            )
            
            E_worst_up = (
                (add_1 + sum(add_2 + add_4 + add_6)) * 
                working_resolution / HOUR + sum(add_7)
            )
            E_worst_down = (
                (add_1 + sum(add_3 + add_5 - add_6)) * 
                working_resolution / HOUR
            )
        else:
            E_worst_up = E_worst_down = 0
        
        if np.isnan(E_worst_up):
            raise Exception(
                'Infeasible state obtained. Please check input reserve '
                'provision settings'
            )
        
        return [E_worst_up, E_worst_down]
    
    def exhaustive_worst_case(
        self,
        t_enter: pd.Timedelta,
        t: pd.Timestamp,
        t_prep_ID: pd.Timedelta,
        GCT_ID: pd.Timedelta,
        t_FAT: pd.Timedelta,
        t_min_FCR: pd.Timedelta,
        include: str = 'both'
    ) -> bool:
        """
        Check if BESS can withstand an exhaustive worst-case scenario.
        
        Args:
            t_enter: Look-ahead time for entering reserve mode
            t: Current time
            t_prep_ID: ID preparation time
            GCT_ID: ID gate closure time
            t_FAT: Full activation time
            t_min_FCR: Minimum FCR duration
            include: Which direction to check ('both', 'up', or 'down')
        
        Returns:
            True if BESS can withstand worst-case, False otherwise
        """
        working_resolution = self._working_resolution
        
        a_up = 1 if include != 'down' else 0
        a_down = 1 if include != 'up' else 0
        
        can_withstand = True
        E_avail = self.E_avail()
        
        for t_look in np.arange(t_enter, 0, -working_resolution):
            E_worst = self.E_worst(
                t_look, t, t_prep_ID, GCT_ID, t_FAT, t_min_FCR
            )
            if (a_up * (E_worst[0] - E_avail[0] > ENERGY_TOLERANCE) or 
                a_down * (E_worst[1] - E_avail[1] > ENERGY_TOLERANCE)):
                can_withstand = False
                break
        
        return can_withstand
    
    # =========================================================================
    # FCR Demand and Reserve Mode Methods
    # =========================================================================
    
    def FCR_demand(
        self,
        t: pd.Timestamp,
        deviation: float,
        max_deviation: float,
        frequency: pd.Series,
        t_FAT: pd.Timedelta
    ) -> Tuple[float, float]:
        """
        Calculate FCR demand based on frequency deviation.
        
        Args:
            t: Current time
            deviation: Current frequency deviation
            max_deviation: Maximum frequency deviation for full activation
            frequency: Frequency timeseries
            t_FAT: Full activation time
        
        Returns:
            Tuple of (FCR power, transition coefficient T)
        """
        working_resolution = self._working_resolution
        
        # Calculate transition coefficient T
        if self.reserve_mode == 0:
            T = 0
        elif self.t_RM <= t < self.t_RM + t_FAT:
            # Transition period to reserve mode
            T = (t - self.t_RM) / t_FAT
        elif self.t_NM <= t < self.t_NM + t_FAT:
            # Transition period to normal mode
            T = (self.t_NM - t) / t_FAT + 1
        else:
            T = 1  # Proper Reserve mode
        
        if self.cap_FCR[t] > 0:
            dev = 0
            freq_asked = np.sign(deviation) * min(abs(deviation), max_deviation)
            
            if self.reserve_mode == 1:
                # Use zero-mean deviation for Reserve mode
                dev = self._zero_mean(t, frequency, t_FAT)
                dev = np.sign(dev) * min(abs(dev), max_deviation)
            
            out = (
                -self.cap_FCR[t] * dev / max_deviation * T - 
                (1 - T) * self.cap_FCR[t] * freq_asked / max_deviation
            )
            return out, T
        else:
            return 0, T
    
    def _zero_mean(
        self, 
        t: pd.Timestamp, 
        frequency: pd.Series,
        t_FAT: pd.Timedelta
    ) -> float:
        """
        Calculate zero-mean deviation for Reserve mode and transitions.
        
        Args:
            t: Current time
            frequency: Frequency timeseries
            t_FAT: Full activation time
        
        Returns:
            Zero-mean deviation value
        """
        return frequency[t - t_FAT: t].mean() - frequency[t]
    
    def check_recovery(
        self,
        t: pd.Timestamp,
        t_AS_over: pd.Timestamp,
        t_rec: pd.Timedelta,
        t_prep_ID: pd.Timedelta,
        GCT_ID: pd.Timedelta,
        t_FAT: pd.Timedelta,
        t_min_FCR: pd.Timedelta,
        max_recover_time: pd.Timedelta,
        log_name: str
    ) -> None:
        """
        Check and manage recovery state after Alert State.
        
        Args:
            t: Current time
            t_AS_over: Time when Alert State ended
            t_rec: Recovery look-ahead time
            t_prep_ID: ID preparation time
            GCT_ID: ID gate closure time
            t_FAT: Full activation time
            t_min_FCR: Minimum FCR duration
            max_recover_time: Maximum allowed recovery time
            log_name: Path to log file
        """
        try:
            from .utils import custom_print
        except ImportError:
            from utils import custom_print
            
        working_resolution = self._working_resolution
        
        # When Alert State ends, check if recovery is needed
        if (t == t_AS_over and not self.recovery_time and 
            not self.exhaustive_worst_case(
                (t + t_rec).floor(MTU) - t, t, t_prep_ID, GCT_ID, t_FAT, t_min_FCR
            )):
            self.recovery_time = 1
            self.t_RT = t
            self.max_recover_time = (
                min(max(self.T_FCR, self.TminLER_done * t_min_FCR), t_min_FCR) / 
                t_min_FCR * max_recover_time
            ).ceil(working_resolution)
            custom_print(
                f'{t} → BESS {self.ID} starts recovery. '
                f'Max. recovery time is {t + self.max_recover_time}', 
                log_name
            )
        
        # Check if recovery can/must end
        if self.recovery_time:
            if self.exhaustive_worst_case(
                (t + t_rec).floor(MTU) - t, t, t_prep_ID, GCT_ID, t_FAT, t_min_FCR
            ):
                self.recovery_time = 0
                custom_print(
                    f'{t} → BESS {self.ID} has successfully concluded recovery', 
                    log_name
                )
                self.TminLER_done = 0
                self.T_FCR = pd.Timedelta('0')
            elif t == self.t_RT + self.max_recover_time + working_resolution:
                self.recovery_time = 0
                custom_print(
                    f'{t} → BESS {self.ID} failed to fully recover within '
                    f'the allocated time of '
                    f'{self.max_recover_time.components.hours} hours '
                    f'{self.max_recover_time.components.minutes} minutes', 
                    log_name
                )
                self.TminLER_done = 0
                self.T_FCR = pd.Timedelta('0')
                
                if self.reserve_mode:
                    self.t_NM = t
                    custom_print(
                        f'{t} → BESS {self.ID} starts transition to Normal '
                        f'mode despite incomplete recovery', 
                        log_name
                    )
    
    def reserve_mode_act(
        self,
        t: pd.Timestamp,
        t_AS: pd.Timestamp,
        alert_state: int,
        t_res_enter: pd.Timedelta,
        t_res_exit: pd.Timedelta,
        t_prep_ID: pd.Timedelta,
        GCT_ID: pd.Timedelta,
        t_FAT: pd.Timedelta,
        t_min_FCR: pd.Timedelta,
        log_name: str
    ) -> None:
        """
        Manage reserve mode activation and deactivation.
        
        Args:
            t: Current time
            t_AS: Time when Alert State started
            alert_state: Current alert state (0 or 1)
            t_res_enter: Look-ahead for reserve mode entry
            t_res_exit: Look-ahead for reserve mode exit
            t_prep_ID: ID preparation time
            GCT_ID: ID gate closure time
            t_FAT: Full activation time
            t_min_FCR: Minimum FCR duration
            log_name: Path to log file
        """
        try:
            from .utils import custom_print
        except ImportError:
            from utils import custom_print
        
        # If Alert State starts while in recovery, switch to Reserve Mode immediately
        if t_AS == t and self.recovery_time:
            self.reserve_mode = 1
            self.t_RM = t - t_FAT
        
        # Finalize switch to Reserve Mode
        if self.reserve_mode and t == self.t_RM + t_FAT:
            custom_print(f'{t} → BESS {self.ID} enters Reserve mode', log_name)
        
        # Switch to Reserve Mode during Alert State if TminLER fulfilled
        if (not self.reserve_mode and alert_state and not self.recovery_time and 
            self.T_FCR >= t_min_FCR):
            if not self.exhaustive_worst_case(
                (t + t_res_enter).floor(MTU) - t, t, t_prep_ID, GCT_ID, 
                t_FAT, t_min_FCR
            ):
                self.reserve_mode = 1
                self.t_RM = t
                custom_print(
                    f"{t} → BESS {self.ID} starts transition to Reserve mode", 
                    log_name
                )
                self.TminLER_done = 1
                self.T_FCR = pd.Timedelta('0')
        
        # Exit Reserve Mode if possible
        if (self.reserve_mode and t >= self.t_RM + t_FAT and 
            t > self.t_NM + t_FAT and 
            (not alert_state or self.exhaustive_worst_case(
                (t + t_res_exit).floor(MTU) - t, t, t_prep_ID, GCT_ID, 
                t_FAT, t_min_FCR
            ))):
            self.t_NM = t
            custom_print(
                f'{t} → BESS {self.ID} starts transition to Normal mode', 
                log_name
            )
        
        # Cancel transition to Reserve Mode if Alert State ends during transition
        if (self.reserve_mode and t < self.t_RM + t_FAT and not alert_state):
            self.t_NM = t - (t_FAT - (t - self.t_RM))
            self.t_RM = self._start_time
            custom_print(
                f'{t} → BESS {self.ID} transition to Reserve Mode cancelled', 
                log_name
            )
        
        # Finalize exiting Reserve Mode
        if self.reserve_mode and t == self.t_NM + t_FAT:
            self.reserve_mode = 0
            custom_print(
                f"{t} → BESS {self.ID} enters Normal mode", 
                log_name
            )
    
    def volunt_FRR(
        self,
        t: pd.Timestamp,
        t_FRR_next: pd.Timestamp,
        t_FRR_look_ahead: pd.Timedelta,
        t_prep_ID: pd.Timedelta,
        GCT_ID: pd.Timedelta,
        t_FAT: pd.Timedelta,
        t_min_FCR: pd.Timedelta,
        convert_MTU: float
    ) -> None:
        """
        Calculate and set voluntary FRR bids.
        
        Args:
            t: Current time
            t_FRR_next: Next FRR window start time
            t_FRR_look_ahead: FRR look-ahead time
            t_prep_ID: ID preparation time
            GCT_ID: ID gate closure time
            t_FAT: Full activation time
            t_min_FCR: Minimum FCR duration
            convert_MTU: Conversion factor for MTU energy
        """
        working_resolution = self._working_resolution
        
        if self.live and self.vol_FRR:
            # Check available power for additional bids
            P_avail_up = math.floor(
                self.power_up - self.cap_FCR[t_FRR_next] - 
                self.cap_FRR_up[t_FRR_next] - self.en_FRR_up[t_FRR_next] - 
                self.en_ID[t_FRR_next]
            )
            P_avail_down = math.floor(
                self.power_down - self.cap_FCR[t_FRR_next] - 
                self.cap_FRR_down[t_FRR_next] - self.en_FRR_down[t_FRR_next] + 
                self.en_ID[t_FRR_next]
            )
            
            if P_avail_up > 0 or P_avail_down > 0:
                E_avail = self.E_avail()
                E_worst = self.E_worst(
                    t_FRR_look_ahead, t, t_prep_ID, GCT_ID, t_FAT, t_min_FCR
                )
                
                # UP direction
                if P_avail_up > 0 and E_avail[0] > E_worst[0]:
                    self.en_FRR_up[t_FRR_next: t_FRR_next + MTU - working_resolution] = max(
                        0, 
                        min(P_avail_up, math.floor(
                            (E_avail[0] - E_worst[0]) / convert_MTU
                        ))
                    )
                    
                    # Check exhaustive worst-case, reduce if necessary
                    while self.en_FRR_up[t_FRR_next] > 0:
                        if self.exhaustive_worst_case(
                            max(
                                (t + t_prep_ID + GCT_ID + MTU).ceil(MTU) - t, 
                                t_FRR_look_ahead
                            ),
                            t, t_prep_ID, GCT_ID, t_FAT, t_min_FCR,
                            include='up'
                        ):
                            break
                        else:
                            self.en_FRR_up[
                                t_FRR_next: t_FRR_next + MTU - working_resolution
                            ] -= 1
                
                # DOWN direction
                if P_avail_down > 0 and E_avail[1] > E_worst[1]:
                    self.en_FRR_down[t_FRR_next: t_FRR_next + MTU - working_resolution] = max(
                        0, 
                        min(P_avail_down, math.floor(
                            (E_avail[1] - E_worst[1]) / convert_MTU
                        ))
                    )
                    
                    # Check exhaustive worst-case, reduce if necessary
                    while self.en_FRR_down[t_FRR_next] > 0:
                        if self.exhaustive_worst_case(
                            max(
                                (t + t_prep_ID + GCT_ID + MTU).ceil(MTU) - t, 
                                t_FRR_look_ahead
                            ),
                            t, t_prep_ID, GCT_ID, t_FAT, t_min_FCR,
                            include='down'
                        ):
                            break
                        else:
                            self.en_FRR_down[
                                t_FRR_next: t_FRR_next + MTU - working_resolution
                            ] -= 1