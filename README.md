# BESS Simulation Tool

A Python-based simulation tool for Battery Energy Storage System (BESS) reserve provision, supporting FCR (Frequency Containment Reserve) and FRR (Frequency Restoration Reserve) market participation with LER (Limited Energy Reservoir) capabilities.

## Features

- **Multi-BESS Simulation**: Supports simulation of two BESS units operating together as a fleet
- **Reserve Market Participation**: Models FCR and FRR capacity and energy market participation
- **LER Support**: Full implementation of Limited Energy Reservoir requirements including:
  - Reserve Mode / Normal Mode transitions
  - TminLER criterion tracking
  - Recovery process after Alert State
- **SOC Management**: Automatic Intraday (ID) market trading for state-of-charge management
- **Voluntary FRR Bidding**: Automatic bidding of available capacity in FRR energy markets
- **Minimum Cycling**: Optional BESS-to-BESS energy exchange to meet minimum cycling requirements
- **Comprehensive Output**: Excel results files and interactive visualizations

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Dependencies

```bash
pip install numpy pandas matplotlib openpyxl
```

### Installation Options

**Option 1: Run from source**
```bash
cd bess_sim
python BESS_sim.py
```

**Option 2: Install as package**
```bash
pip install -e .
```

Then run:
```python
from bess_sim import run_simulation
run_simulation()
```

## Project Structure

```
bess_sim/
├── BESS_sim.py              # Main entry point (backward compatible)
├── settings.xlsx            # Simulation settings
├── output_template.xlsx     # Excel output template
├── frequency_*.csv          # Frequency input data
├── FRR_*.csv               # FRR activation input data
├── bess_sim/               # Main package
│   ├── __init__.py         # Package initialization
│   ├── constants.py        # Physical and market constants
│   ├── utils.py            # Utility functions
│   ├── config.py           # Configuration management
│   ├── data_input.py       # Data loading and preprocessing
│   ├── bess_model.py       # BESS technical model
│   ├── simulation.py       # Main simulation engine
│   ├── output.py           # Results and visualization
│   └── main.py             # Main entry point module
├── tests/                  # Test suite
│   └── __init__.py
├── setup.py                # Package setup
└── README.md               # This file
```

## Configuration

### Settings File (settings.xlsx)

The main settings file contains four categories of parameters:

1. **BESS Technical Parameters**: Power ratings, capacity, efficiency, SOC limits
2. **BESS Simulation Settings**: Initial SOC, LER qualification, availability
3. **Reserve Provision Settings**: FCR/FRR capacity obligations (uniform or time-varying)
4. **Market Settings**: GCT timings, preparation times, frequency parameters

### Input Files

- **Frequency File**: CSV/Excel with `Time` and `Value` columns
- **FRR Activation File**: CSV/Excel with `Start`, `End`, and `MW` columns

## Usage

### Basic Usage

```python
from bess_sim import run_simulation

# Run with default settings
run_simulation()

# Or specify custom files
run_simulation(
    settings_file='my_settings.xlsx',
    output_template='my_template.xlsx'
)
```

### Command Line

```bash
python BESS_sim.py [settings_file] [output_template]
```

## Output

The simulation produces:

1. **Results Excel File**: Detailed time-series data for both BESS units including:
   - SOC trajectories
   - Contracted availability (FCR, FRR)
   - Activation expectations
   - Delivery failures
   - Reserve mode status

2. **Interactive Figures**: Matplotlib visualizations showing:
   - SOC and ID schedule (Row 1)
   - FCR activation and frequency deviation (Row 2)
   - FRR activation (Row 3)

3. **Log File**: Console messages during simulation

## Module Documentation

### constants.py
Physical and market constants (MTU duration, time deltas, etc.)

### config.py
`ConfigurationManager` class for reading Excel settings files and parsing into dataclasses:
- `BESSParameters`
- `MarketSettings`
- `FrequencySettings`
- `SimulationSettings`
- `ReserveProvisionSettings`

### bess_model.py
`BESS` class implementing:
- Energy calculations (worst-case scenarios, available energy)
- FCR demand calculation with Reserve Mode support
- Recovery and Reserve Mode state management
- Voluntary FRR bidding logic

### simulation.py
`SimulationEngine` class orchestrating:
- Main simulation loop
- SOC management (ID trading)
- Alert State detection
- LER-specific procedures
- Energy delivery tracking
- Minimum cycling management

### output.py
- `ResultsWriter`: Excel file output
- `Visualizer`: Matplotlib figure generation
- `print_summary`: Console statistics

## Version History

- **v2.0.0**: Refactored into modular package structure
- **v1.0.0**: Original monolithic script (2022-12-20)

## Authors

RTU Institute of Power Engineering

## License

[Specify your license here]

## References

For detailed algorithm descriptions, see the accompanying documentation:
- `BESS_modela_apraksts_v2_2022-12-20.docx` (Latvian)
- `BESS_sim_manual_v2_2022-12-20.docx` (English)
