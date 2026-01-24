# BESS Simulation Tool

A Python-based simulation tool for Battery Energy Storage System (BESS) reserve provision, implementing the robust market-based management strategy described in:

> **Baltputnis, K., Broka, Z., Cingels, G., Sīlis, A., & Junghāns, G. (2024).** *Robust market-based battery energy storage management strategy for operation in European balancing markets.* Journal of Energy Storage, 102, 114082. https://doi.org/10.1016/j.est.2024.114082

The tool supports simultaneous FCR (Frequency Containment Reserve) and aFRR (automatic Frequency Restoration Reserve) market participation with market-based SOC restoration exclusively via the intraday market, fully compliant with EU System Operation Guideline requirements for Limited Energy Reservoirs (LERs).

## Methodology Overview

The simulation implements a **worst-case activation anticipation approach** where non-delivery of contracted reserves is never permitted. Key principles:

- **No activation overfulfilment** or FCR deadband utilization for SOC restoration
- **SOC restoration exclusively via scheduled ID market transactions**
- Full compliance with EU SOG requirements for LER FCR providers

### Three Decision-Making Modules

1. **BESS SOC Management** (`simulation.py`): Prepares ID market bids ensuring sufficient charge for worst-case reserve activation scenarios. Calculates worst-case energy requirements considering FCR, FRR capacity, scheduled ID trades, and self-discharge losses.

2. **LER Management in Alert State** (`bess_model.py`): Implements reserve mode/normal mode transitions with 5-min aFRR full activation time for transitions. Tracks ΔTminLER criterion fulfillment (30 min full FCR activation during alert state) and manages recovery status post-alert (max 2 hours per SOG).

3. **Voluntary FRR Energy Bid Preparation** (`bess_model.py`): Estimates additional FRR bids using surplus BESS capacity after ensuring worst-case scenario handling. Includes SOC violation subroutine to verify bids don't cause issues in other time periods.

### SOC Management Strategies

- **Conservative Strategy** (for LER): Takes advantage of lenient criteria for LER FCR providers during alert state. Lower worst-case energy requirements, less active ID trading.

- **Active Strategy** (for non-LER): Requires continuous BESS availability irrespective of system state. More frequent ID trades but ensures full FCR provision without reserve mode transitions.

### Market Parameters (Continental Europe defaults)

- FCR: Symmetric capacity product, ±200 mHz full activation, ±10 mHz deadband
- aFRR: 5-min full activation time
- Market Time Unit (MTU): 15 minutes
- ID GCT: Configurable (60 min Baltic, 5 min Germany)

## Features

- **Multi-BESS Simulation**: Two BESS units operating as a fleet with capacity allocation
- **Reserve Market Participation**: FCR and FRR capacity/energy market modeling
- **LER Support**: Full implementation including reserve mode, ΔTminLER tracking, and recovery
- **SOC Management**: Automatic ID market trading based on worst-case energy calculations
- **Voluntary FRR Bidding**: Automatic bidding of available capacity with exhaustive worst-case validation
- **Minimum Cycling**: Optional BESS-to-BESS energy exchange to meet cycling requirements
- **Trade Netting**: Physical energy exchange ~20% less than sum of individual market deliveries
- **Comprehensive Output**: Excel results and interactive matplotlib visualizations

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Dependencies

```bash
pip install numpy pandas matplotlib openpyxl
```

## Project Structure

```
bess_sim/
├── main.py                  # Entry point - run this
├── constants.py             # Physical and market constants (MTU, time deltas)
├── utils.py                 # Utility functions (logging, rounding, ID clearing)
├── config.py                # Configuration management from settings.xlsx
├── data_input.py            # Frequency and FRR activation data loading
├── bess_model.py            # BESS class: energy calculations, LER procedures, voluntary FRR
├── simulation.py            # Main loop: SOC management, Alert State, reserve activation
├── output.py                # Excel results and matplotlib figures
├── settings.xlsx            # Simulation settings
├── output_template.xlsx     # Excel output template
├── frequency_*.csv          # Frequency input data
├── FRR_*.csv                # FRR activation input data
└── README.md                # This file
```

## Configuration

### Settings File (settings.xlsx)

1. **BESS Technical Parameters**: Power ratings, capacity, efficiency (round-trip ~90.25%), SOC limits (10-90%)
2. **BESS Simulation Settings**: Initial SOC, LER qualification, availability, SOC management strategy
3. **Reserve Provision Settings**: FCR/FRR capacity obligations (uniform or per-MTU)
4. **Market Settings**: GCT timings (ID, FRR), preparation times, frequency parameters (deadband, full activation deviation), ΔTminLER, max recovery time

### Input Files

- **Frequency File**: CSV/Excel with `Time` and `Value` columns (1-second to 1-minute resolution recommended)
- **FRR Activation File**: CSV/Excel with `Start`, `End`, and `MW` columns (positive = up-regulation)

## Usage

```bash
python main.py
```

The simulation resolution is configurable (1-minute recommended for balance of accuracy and performance).

## Output

1. **Results Folder**: Named `{scenario_name} Run {n}/` containing:
   - Excel results with detailed time-series
   - Log file with console messages and warnings
   - Copy of settings used

2. **Results Excel**: Per-timestep data for both BESS units:
   - SOC trajectories
   - Contracted FCR/FRR availability
   - Activation expectations and actual delivery
   - Delivery failures (if any)
   - Reserve mode and recovery status

3. **Interactive Figures**:
   - Row 1: SOC trajectory and ID schedule with Alert State highlighting
   - Row 2: FCR activation vs frequency deviation with Normal/Reserve mode indication
   - Row 3: FRR activation vs contracted capacity

## Module Overview

| Module | Description |
|--------|-------------|
| `main.py` | Entry point, orchestrates simulation flow |
| `constants.py` | Time constants (MTU=15min, hour, etc.) |
| `config.py` | Reads settings.xlsx, provides configuration dataclasses |
| `data_input.py` | Loads and resamples frequency/FRR data |
| `bess_model.py` | BESS class with E_worst calculations, FCR/FRR logic, LER reserve mode, voluntary FRR bidding |
| `simulation.py` | Main simulation loop, SOC management decisions, Alert State detection, energy delivery |
| `output.py` | Excel output writing, matplotlib figure generation |
| `utils.py` | Helper functions (custom_print, true_round, ID_clearing) |

## Validation

The strategy has been validated against:
- **Extreme worst-case scenario**: 6-hour continuous full FCR + aFRR activation
- **Realistic scenarios**: Full-year simulations with German (CE) and Finnish (Nordic) frequency data
- **Sensitivity analysis**: ID GCT varied from 15-105 minutes

⚠️ **TODO:** sort out the information below here.

## Version History

- **v2.0.0**: Refactored into modular structure
- **v1.0.0**: Original monolithic script (2022-12-20)

## Authors

RTU Institute of Power Engineering (Riga Technical University)
- Kārlis Baltputnis
- Zane Broka

In collaboration with AS "Augstsprieguma tīkls" (Latvian TSO)

## References

- Baltputnis et al. (2024). *Robust market-based battery energy storage management strategy for operation in European balancing markets.* Journal of Energy Storage, 102, 114082, https://doi.org/10.1016/j.est.2024.114082
- Paper input data and results: https://doi.org/10.5281/zenodo.18199324
- `BESS_modela_apraksts_v2_2022-12-20.docx` - Algorithm description (Latvian)
- `BESS_sim_manual_v2_2022-12-20.docx` - User manual (English)

## License

This research was funded by the Latvian Council of Science, project "SignAture" (lzp-2021/1-0227).
