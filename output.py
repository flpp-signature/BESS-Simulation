# -*- coding: utf-8 -*-
"""
Output handling for BESS simulation.

This module handles writing results to Excel files and generating
visualization plots.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
from typing import Dict, List, Tuple

try:
    from .constants import HOUR
    from .utils import true_round
except ImportError:
    from constants import HOUR
    from utils import true_round

# Suppress matplotlib deprecation warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)


class ResultsWriter:
    """
    Handles writing simulation results to Excel files.
    """
    
    @staticmethod
    def write_results(
        results: Dict,
        output_file: str,
        freq_settings,
        working_resolution: pd.Timedelta
    ) -> None:
        """
        Write simulation results to Excel file.
        
        Args:
            results: Dictionary containing all simulation results
            output_file: Path to output Excel file
            freq_settings: Frequency settings object
            working_resolution: Simulation time resolution
        """
        bess_1 = results['bess_1']
        bess_2 = results['bess_2']
        start_time = results['start_time']
        end_time = results['end_time']
        
        sheet = 'Results'
        
        with pd.ExcelWriter(
            output_file, 
            engine='openpyxl', 
            mode='a', 
            if_sheet_exists='overlay',
            engine_kwargs={"keep_vba": False}
        ) as writer:
            # Time column
            pd.Series(results['frequency'].index).to_excel(
                writer, header=0, index=0, startrow=4, startcol=0, sheet_name=sheet
            )
            
            # Frequency deviation
            round((results['frequency'] - freq_settings.nom_frequency), 4).to_excel(
                writer, header=0, index=0, startrow=4, startcol=1, sheet_name=sheet
            )
            
            # Alert status
            results['alert_status'].to_excel(
                writer, header=0, index=0, startrow=4, startcol=2, sheet_name=sheet
            )
            
            # BESS-1 results
            round((results['SOC_1'] / bess_1.capacity * 100), 2).to_excel(
                writer, header=0, index=0, startrow=4, startcol=4, sheet_name=sheet
            )
            round(bess_1.cap_FCR[start_time:end_time - working_resolution], 1).to_excel(
                writer, header=0, index=0, startrow=4, startcol=5, sheet_name=sheet
            )
            round((bess_1.cap_FRR_up[start_time:end_time - working_resolution] + 
                   bess_1.en_FRR_up[start_time:end_time - working_resolution]), 1).to_excel(
                writer, header=0, index=0, startrow=4, startcol=6, sheet_name=sheet
            )
            round((bess_1.cap_FRR_down[start_time:end_time - working_resolution] + 
                   bess_1.en_FRR_down[start_time:end_time - working_resolution]), 1).to_excel(
                writer, header=0, index=0, startrow=4, startcol=7, sheet_name=sheet
            )
            round(results['o_FCR_1'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=8, sheet_name=sheet
            )
            round(results['o_FRR_1'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=9, sheet_name=sheet
            )
            round(results['o_ID_1'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=10, sheet_name=sheet
            )
            round(results['f_FCR_1'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=11, sheet_name=sheet
            )
            round(results['f_FRR_1'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=12, sheet_name=sheet
            )
            round(results['f_ID_1'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=13, sheet_name=sheet
            )
            round(results['pow_1'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=14, sheet_name=sheet
            )
            results['res_1'].to_excel(
                writer, header=0, index=0, startrow=4, startcol=15, sheet_name=sheet
            )
            results['rec_1'].to_excel(
                writer, header=0, index=0, startrow=4, startcol=16, sheet_name=sheet
            )
            
            # BESS-2 results
            round((results['SOC_2'] / bess_2.capacity * 100), 2).to_excel(
                writer, header=0, index=0, startrow=4, startcol=18, sheet_name=sheet
            )
            round(bess_2.cap_FCR[start_time:end_time - working_resolution], 1).to_excel(
                writer, header=0, index=0, startrow=4, startcol=19, sheet_name=sheet
            )
            round((bess_2.cap_FRR_up[start_time:end_time - working_resolution] + 
                   bess_2.en_FRR_up[start_time:end_time - working_resolution]), 1).to_excel(
                writer, header=0, index=0, startrow=4, startcol=20, sheet_name=sheet
            )
            round((bess_2.cap_FRR_down[start_time:end_time - working_resolution] + 
                   bess_2.en_FRR_down[start_time:end_time - working_resolution]), 1).to_excel(
                writer, header=0, index=0, startrow=4, startcol=21, sheet_name=sheet
            )
            round(results['o_FCR_2'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=22, sheet_name=sheet
            )
            round(results['o_FRR_2'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=23, sheet_name=sheet
            )
            round(results['o_ID_2'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=24, sheet_name=sheet
            )
            round(results['f_FCR_2'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=25, sheet_name=sheet
            )
            round(results['f_FRR_2'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=26, sheet_name=sheet
            )
            round(results['f_ID_2'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=27, sheet_name=sheet
            )
            round(results['pow_2'], 3).to_excel(
                writer, header=0, index=0, startrow=4, startcol=28, sheet_name=sheet
            )
            results['res_2'].to_excel(
                writer, header=0, index=0, startrow=4, startcol=29, sheet_name=sheet
            )
            results['rec_2'].to_excel(
                writer, header=0, index=0, startrow=4, startcol=30, sheet_name=sheet
            )


class Visualizer:
    """
    Handles visualization of simulation results.
    """
    
    def __init__(self, results: Dict, freq_settings, working_resolution: pd.Timedelta):
        """
        Initialize visualizer.
        
        Args:
            results: Dictionary containing all simulation results
            freq_settings: Frequency settings object
            working_resolution: Working resolution timedelta
        """
        self.results = results
        self.freq_settings = freq_settings
        self.working_resolution = working_resolution
        self.bess_1 = results['bess_1']
        self.bess_2 = results['bess_2']
        self.time_indexes = results['time_indexes']
        self.start_time = results['start_time']
        self.end_time = results['end_time']
        
        # Prepare data for plotting
        self._prepare_plot_data()
    
    def _prepare_plot_data(self) -> None:
        """Prepare data arrays for plotting."""
        # Round data
        self.o_ID_1 = true_round(self.results['o_ID_1'])
        self.o_ID_2 = true_round(self.results['o_ID_2'])
        self.o_FRR_1 = true_round(self.results['o_FRR_1'])
        self.o_FRR_2 = true_round(self.results['o_FRR_2'])
        self.o_FCR_1 = true_round(self.results['o_FCR_1'])
        self.o_FCR_2 = true_round(self.results['o_FCR_2'])
        
        # Create duplicated time index for step plots
        self.p_time_indexes = [
            sub[item] 
            for item in range(len(self.time_indexes)) 
            for sub in [self.time_indexes, self.time_indexes]
        ]
        self.p_time_indexes.pop(0)
        self.p_time_indexes.append(self.end_time)
        
        # Calculate delivered values
        self.d_ID_1 = true_round(self.o_ID_1 - self.results['f_ID_1'])
        self.d_ID_2 = true_round(self.o_ID_2 - self.results['f_ID_2'])
        self.d_FCR_1 = true_round(self.o_FCR_1 - self.results['f_FCR_1'])
        self.d_FCR_2 = true_round(self.o_FCR_2 - self.results['f_FCR_2'])
        self.d_FRR_1 = true_round(self.o_FRR_1 - self.results['f_FRR_1'])
        self.d_FRR_2 = true_round(self.o_FRR_2 - self.results['f_FRR_2'])
        
        # Create step plot data
        self._create_step_data()
        
        # Find alert and reserve mode transitions
        self._find_transitions()
    
    def _create_step_data(self) -> None:
        """Create step plot arrays."""
        def duplicate_for_step(data):
            return [sub[item] for item in range(len(self.time_indexes)) for sub in [data, data]]
        
        self.p_d_ID_1 = duplicate_for_step(self.d_ID_1)
        self.p_d_ID_2 = duplicate_for_step(self.d_ID_2)
        self.p_o_ID_1 = duplicate_for_step(self.o_ID_1)
        self.p_o_ID_2 = duplicate_for_step(self.o_ID_2)
        
        self.p_d_FCR_1 = duplicate_for_step(self.d_FCR_1)
        self.p_d_FCR_2 = duplicate_for_step(self.d_FCR_2)
        self.p_o_FCR_1 = duplicate_for_step(self.o_FCR_1)
        self.p_o_FCR_2 = duplicate_for_step(self.o_FCR_2)
        
        self.p_d_FRR_1 = duplicate_for_step(self.d_FRR_1)
        self.p_d_FRR_2 = duplicate_for_step(self.d_FRR_2)
        self.p_o_FRR_1 = duplicate_for_step(self.o_FRR_1)
        self.p_o_FRR_2 = duplicate_for_step(self.o_FRR_2)
        
        # Capacity series
        self.cap_FCR_1 = duplicate_for_step(self.bess_1.cap_FCR)
        self.cap_FCR_2 = duplicate_for_step(self.bess_2.cap_FCR)
        
        cap_FRR_up_1 = self.bess_1.cap_FRR_up + self.bess_1.en_FRR_up
        cap_FRR_up_2 = self.bess_2.cap_FRR_up + self.bess_2.en_FRR_up
        cap_FRR_down_1 = self.bess_1.cap_FRR_down + self.bess_1.en_FRR_down
        cap_FRR_down_2 = self.bess_2.cap_FRR_down + self.bess_2.en_FRR_down
        
        self.cap_FRR_up_1 = duplicate_for_step(cap_FRR_up_1)
        self.cap_FRR_up_2 = duplicate_for_step(cap_FRR_up_2)
        self.cap_FRR_down_1 = duplicate_for_step(cap_FRR_down_1)
        self.cap_FRR_down_2 = duplicate_for_step(cap_FRR_down_2)
    
    def _find_transitions(self) -> None:
        """Find alert state and reserve mode transition points."""
        alert_status = self.results['alert_status']
        res_1 = self.results['res_1']
        res_2 = self.results['res_2']
        
        self.alert_on = []
        self.alert_off = []
        self.res_1_on = []
        self.res_1_off = []
        self.res_2_on = []
        self.res_2_off = []
        self.tran_1_on = []
        self.tran_1_off = []
        self.tran_2_on = []
        self.tran_2_off = []
        
        for it, t in enumerate(self.time_indexes):
            if it > 0:
                if alert_status.iloc[it - 1] == 0 and alert_status.iloc[it] == 1:
                    self.alert_on.append(t)
                if alert_status.iloc[it - 1] == 1 and alert_status.iloc[it] == 0:
                    self.alert_off.append(t)
                if res_1.iloc[it - 1] < 1 and res_1.iloc[it] == 1:
                    self.res_1_on.append(t)
                if res_1.iloc[it - 1] == 1 and res_1.iloc[it] < 1:
                    self.res_1_off.append(t)
                if res_2.iloc[it - 1] < 1 and res_2.iloc[it] == 1:
                    self.res_2_on.append(t)
                if res_2.iloc[it - 1] == 1 and res_2.iloc[it] < 1:
                    self.res_2_off.append(t)
                if not 1 > res_1.iloc[it - 1] > 0 and 1 > res_1.iloc[it] > 0:
                    self.tran_1_on.append(t)
                if 1 > res_1.iloc[it - 1] > 0 and not 1 > res_1.iloc[it] > 0:
                    self.tran_1_off.append(t)
                if not 1 > res_2.iloc[it - 1] > 0 and 1 > res_2.iloc[it] > 0:
                    self.tran_2_on.append(t)
                if 1 > res_2.iloc[it - 1] > 0 and not 1 > res_2.iloc[it] > 0:
                    self.tran_2_off.append(t)
        
        # Handle edge cases
        if alert_status[self.start_time]:
            self.alert_on.insert(0, self.start_time)
        if alert_status[self.end_time - self.working_resolution]:
            self.alert_off.append(self.end_time - self.working_resolution)
        if res_1[self.end_time - self.working_resolution]:
            self.res_1_off.append(self.end_time - self.working_resolution)
        if res_2[self.end_time - self.working_resolution]:
            self.res_2_off.append(self.end_time - self.working_resolution)
    
    def create_figure(self) -> plt.Figure:
        """
        Create the main visualization figure.
        
        Returns:
            matplotlib Figure object
        """
        fig = plt.figure()
        
        # Common parameters
        zero_width = 0.7
        legend_color = 'white'
        leg_font = 6
        
        SOC_1 = self.results['SOC_1']
        SOC_2 = self.results['SOC_2']
        frequency = self.results['frequency']
        nom_frequency = self.freq_settings.nom_frequency
        
        # First row - ID schedule and SOC
        ax1 = plt.subplot(321)
        ax1.set_title('BESS-1')
        ax1.set_facecolor('honeydew')
        ax1.set_xlim([self.start_time, self.end_time])
        
        sax1 = ax1.twinx()
        sax1.plot(self.time_indexes, SOC_1 / self.bess_1.capacity * 100, color='dimgrey')
        
        for start_t, end_t in zip(self.alert_on, self.alert_off):
            ax1.axvspan(start_t, end_t, facecolor='pink')
        
        ax1.fill_between(self.p_time_indexes, self.p_d_ID_1, color='dodgerblue', alpha=0.8, linewidth=0)
        ax1.fill_between(self.p_time_indexes, self.p_d_ID_1, self.p_o_ID_1, color='red', alpha=0.8, linewidth=0)
        
        sax1.set_ylim([0, 100])
        sax1.set_zorder(4)
        ax1.set_zorder(3)
        ax1.set_ylabel('Intraday schedule, MW', color='dodgerblue', weight='bold')
        ax1.tick_params(axis='y', colors='dodgerblue')
        sax1.set_ylabel('State of charge, %', color='dimgray', weight='bold')
        sax1.tick_params(axis='y', colors='dimgray')
        
        entry_1_1 = mpatches.Patch(color='honeydew', label='Normal State')
        entry_1_2 = mpatches.Patch(color='pink', label='Alert State')
        if any(self.results['alert_status']):
            ax1.legend(handles=[entry_1_1, entry_1_2], facecolor=legend_color, fontsize=leg_font, ncol=3)
        
        ax2 = plt.subplot(322, sharex=ax1, sharey=ax1)
        ax2.set_title('BESS-2')
        ax2.set_facecolor('honeydew')
        ax2.set_xlim([self.start_time, self.end_time])
        
        sax2 = ax2.twinx()
        sax2.sharey(sax1)
        sax2.plot(self.time_indexes, SOC_2 / self.bess_2.capacity * 100, color='dimgrey')
        
        for start_t, end_t in zip(self.alert_on, self.alert_off):
            ax2.axvspan(start_t, end_t, facecolor='pink')
        
        ax2.fill_between(self.p_time_indexes, self.p_d_ID_2, color='dodgerblue', alpha=0.8, linewidth=0)
        ax2.fill_between(self.p_time_indexes, self.p_d_ID_2, self.p_o_ID_2, color='red', alpha=0.8, linewidth=0)
        
        sax2.set_ylim([0, 100])
        sax2.set_zorder(4)
        ax2.set_zorder(3)
        
        if any(self.results['alert_status']):
            ax2.legend(handles=[entry_1_1, entry_1_2], facecolor=legend_color, fontsize=leg_font, ncol=3)
        
        ax2.set_ylabel('Intraday schedule, MW', color='dodgerblue', weight='bold')
        ax2.tick_params(axis='y', colors='dodgerblue')
        sax2.set_ylabel('State of charge, %', color='dimgray', weight='bold')
        sax2.tick_params(axis='y', colors='dimgray')
        
        ax1.set_ylim([-max(np.absolute(ax1.get_ylim())), max(np.absolute(ax1.get_ylim()))])
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=zero_width)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=zero_width)
        
        # Second row - FCR activation
        ax3 = plt.subplot(323, sharex=ax1)
        ax3.set_facecolor('ivory')
        sax3 = ax3.twinx()
        sax3.plot(self.time_indexes, frequency - nom_frequency, color='dimgrey', linewidth=0.7, alpha=0.5)
        
        for start_t, end_t in zip(self.res_1_on, self.res_1_off):
            ax3.axvspan(start_t, end_t, facecolor='wheat')
        for start_t, end_t in zip(self.tran_1_on, self.tran_1_off):
            ax3.axvspan(start_t, end_t, facecolor='cornsilk')
        
        ax3.plot(self.p_time_indexes, self.cap_FCR_1, color='navy')
        ax3.plot(self.p_time_indexes, np.negative(self.cap_FCR_1), color='navy')
        ax3.fill_between(self.p_time_indexes, self.p_d_FCR_1, color='dodgerblue', alpha=0.8, linewidth=0)
        ax3.fill_between(self.p_time_indexes, self.p_d_FCR_1, self.p_o_FCR_1, color='red', alpha=0.8, linewidth=0)
        
        sax3.set_zorder(4)
        ax3.set_zorder(3)
        ax3.set_ylabel('Activated FCR, MW', color='dodgerblue', weight='bold')
        ax3.tick_params(axis='y', colors='dodgerblue')
        sax3.set_ylabel('Frequency deviation, Hz', color='dimgray', weight='bold')
        sax3.tick_params(axis='y', colors='dimgray')
        
        entry_3_1 = mpatches.Patch(color='ivory', label='Normal mode')
        entry_3_2 = mpatches.Patch(color='cornsilk', label='Transition')
        entry_3_3 = mpatches.Patch(color='wheat', label='Reserve mode')
        if any(self.results['res_1']):
            ax3.legend(handles=[entry_3_1, entry_3_2, entry_3_3], facecolor=legend_color, fontsize=leg_font, ncol=3)
        
        ax4 = plt.subplot(324, sharex=ax1, sharey=ax3)
        ax4.set_facecolor('ivory')
        sax4 = ax4.twinx()
        sax4.sharey(sax3)
        sax4.plot(self.time_indexes, frequency - nom_frequency, color='dimgrey', linewidth=0.7, alpha=0.5)
        
        for start_t, end_t in zip(self.res_2_on, self.res_2_off):
            ax4.axvspan(start_t, end_t, facecolor='wheat')
        for start_t, end_t in zip(self.tran_2_on, self.tran_2_off):
            ax4.axvspan(start_t, end_t, facecolor='cornsilk')
        
        ax4.plot(self.p_time_indexes, self.cap_FCR_2, color='navy')
        ax4.plot(self.p_time_indexes, np.negative(self.cap_FCR_2), color='navy')
        ax4.fill_between(self.p_time_indexes, self.p_d_FCR_2, color='dodgerblue', alpha=0.8, linewidth=0)
        ax4.fill_between(self.p_time_indexes, self.p_d_FCR_2, self.p_o_FCR_2, color='red', alpha=0.8, linewidth=0)
        
        sax4.set_zorder(4)
        ax4.set_zorder(3)
        ax4.set_ylabel('Activated FCR, MW', color='dodgerblue', weight='bold')
        ax4.tick_params(axis='y', colors='dodgerblue')
        sax4.set_ylabel('Frequency deviation, Hz', color='dimgray', weight='bold')
        sax4.tick_params(axis='y', colors='dimgray')
        
        if any(self.results['res_2']):
            ax4.legend(handles=[entry_3_1, entry_3_2, entry_3_3], facecolor=legend_color, fontsize=leg_font, ncol=3)
        
        ax3.set_ylim([-max(np.absolute(ax3.get_ylim())), max(np.absolute(ax3.get_ylim()))])
        sax3.set_ylim([-max(np.absolute(sax3.get_ylim())), max(np.absolute(sax3.get_ylim()))])
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=zero_width)
        ax4.axhline(y=0, color='black', linestyle='-', linewidth=zero_width)
        
        # Third row - FRR activation
        ax5 = plt.subplot(325, sharex=ax1)
        ax5.plot(self.p_time_indexes, self.cap_FRR_up_1, color='navy')
        ax5.plot(self.p_time_indexes, np.negative(self.cap_FRR_down_1), color='navy')
        ax5.fill_between(self.p_time_indexes, self.p_d_FRR_1, color='dodgerblue', alpha=0.8, linewidth=0)
        ax5.fill_between(self.p_time_indexes, self.p_d_FRR_1, self.p_o_FRR_1, color='red', alpha=0.8, linewidth=0)
        ax5.set_ylabel('Activated FRR, MW', color='dodgerblue', weight='bold')
        ax5.tick_params(axis='y', colors='dodgerblue')
        
        ax6 = plt.subplot(326, sharex=ax1, sharey=ax5)
        ax6.plot(self.p_time_indexes, self.cap_FRR_up_2, color='navy')
        ax6.plot(self.p_time_indexes, np.negative(self.cap_FRR_down_2), color='navy')
        ax6.fill_between(self.p_time_indexes, self.p_d_FRR_2, color='dodgerblue', alpha=0.8, linewidth=0)
        ax6.fill_between(self.p_time_indexes, self.p_d_FRR_2, self.p_o_FRR_2, color='red', alpha=0.8, linewidth=0)
        ax6.set_ylabel('Activated FRR, MW', color='dodgerblue', weight='bold')
        ax6.tick_params(axis='y', colors='dodgerblue')
        
        ax5.set_ylim([-max(np.absolute(ax5.get_ylim())), max(np.absolute(ax5.get_ylim()))])
        ax5.axhline(y=0, color='black', linestyle='-', linewidth=zero_width)
        ax6.axhline(y=0, color='black', linestyle='-', linewidth=zero_width)
        
        # Maximize window
        self._maximize_figure()
        
        return fig
    
    def _maximize_figure(self) -> None:
        """Attempt to maximize the figure window."""
        backend = plt.get_backend()
        cfm = plt.get_current_fig_manager()
        
        try:
            if backend == "wxAgg":
                cfm.frame.Maximize(True)
            elif backend == "TkAgg":
                cfm.resize(*cfm.window.maxsize())
            elif backend == "QT4Agg":
                cfm.window.showMaximized()
            elif callable(getattr(cfm, "full_screen_toggle", None)):
                if not getattr(cfm, "flag_is_max", None):
                    cfm.full_screen_toggle()
                    cfm.flag_is_max = True
        except Exception:
            print('Please maximize the figure window manually!')
    
    def show(self) -> None:
        """Display the figure."""
        plt.show()
        plt.tight_layout()


def print_summary(results: Dict, working_resolution: pd.Timedelta) -> None:
    """
    Print summary statistics of the simulation.
    
    Args:
        results: Dictionary containing all simulation results
        working_resolution: Simulation time resolution
    """
    kof = HOUR / working_resolution

    def _print_bess_summary(label: str, o_FCR, o_FRR, o_ID, f_FCR, f_FRR, f_ID):
        print(f'\n{label}')
        print('delivery expectation')
        print(f'FCR up = {round(sum(o_FCR[o_FCR > 0]) / kof, 3)}')
        print(f'FCR down = {round(sum(o_FCR[o_FCR < 0]) / kof, 3)}')
        print(f'FRR up = {round(sum(o_FRR[o_FRR > 0]) / kof, 3)}')
        print(f'FRR down = {round(sum(o_FRR[o_FRR < 0]) / kof, 3)}')
        print(f'ID bought = {round(sum(o_ID[o_ID < 0]) / kof, 3)}')
        print(f'ID sold = {round(sum(o_ID[o_ID > 0]) / kof, 3)}')

        print('failed deliveries')
        print(f'FCR up = {round(sum(f_FCR[f_FCR > 0]) / kof, 3)}')
        print(f'FCR down = {round(sum(f_FCR[f_FCR < 0]) / kof, 3)}')
        print(f'FRR up = {round(sum(f_FRR[f_FRR > 0]) / kof, 3)}')
        print(f'FRR down = {round(sum(f_FRR[f_FRR < 0]) / kof, 3)}')
        print(f'ID bought = {round(sum(f_ID[f_ID < 0]) / kof, 3)}')
        print(f'ID sold = {round(sum(f_ID[f_ID > 0]) / kof, 3)}')

    # ---- BESS 1 ----
    _print_bess_summary(
        label='BESS-1',
        o_FCR=results['o_FCR_1'],
        o_FRR=results['o_FRR_1'],
        o_ID=results['o_ID_1'],
        f_FCR=results['f_FCR_1'],
        f_FRR=results['f_FRR_1'],
        f_ID=results['f_ID_1'],
    )

    # ---- BESS 2 ----
    _print_bess_summary(
        label='BESS-2',
        o_FCR=results['o_FCR_2'],
        o_FRR=results['o_FRR_2'],
        o_ID=results['o_ID_2'],
        f_FCR=results['f_FCR_2'],
        f_FRR=results['f_FRR_2'],
        f_ID=results['f_ID_2'],
    )
