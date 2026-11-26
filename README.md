<p align="center">
  <img src="imagens/logo.png" alt="BatSignal logo" width="200">
</p>

# BatSignal

**Understand your Wi-Fi coverage, one room at a time.**

BatSignal is a Python desktop application that records Wi-Fi signal strength across rooms and turns the measurements into charts and reports. Use it to compare locations for your computer, investigate areas with weaker reception, and document changes to your setup.

Built with Tkinter, pandas, and Matplotlib. Signal collection currently targets **Windows**, and the application interface is in **Portuguese**.

## Features

- **Room-by-room collection:** assign a room name and configure the collection duration and sampling interval.
- **Live measurement log:** follow signal readings as they are collected.
- **Room summaries:** review minimum, maximum, and average signal strength.
- **Visual comparisons:** inspect readings in line charts and compare room averages in a sorted bar chart.
- **Saved surveys:** save measurements as JSON, reload previous surveys, or delete saved files through the interface.
- **Excel export:** create an `.xlsx` workbook with one worksheet per room and a summary worksheet.

## Requirements

- Windows with an active Wi-Fi connection and access to `netsh`.
- **Portuguese `netsh` output:** the current collector looks for the field named `Sinal`. Output in other languages is not currently handled.
- Python with Tkinter support. **Python 3.11 is the suggested starting point for the repository's existing dependency pins**; newer Python versions may require dependency updates.
- Git to clone the repository, or a downloaded copy of its source files.

BatSignal records the signal percentage reported by Windows. It does not measure download speed, latency, packet loss, or internet availability.

## Installation

Run the following commands in PowerShell.

### 1. Download the source

```powershell
git clone https://github.com/theycallmefreire/BatSignal-wifi.git
cd BatSignal-wifi
```

### 2. Create a virtual environment

With Python 3.11 installed and available through the Windows Python launcher:

```powershell
py -3.11 -m venv .venv
```

If you use `python -m venv .venv` instead, first check that `python --version` points to your intended Python installation.

### 3. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install "numpy<2" -r requeriments.txt Pillow
```

The dependency file is currently named **`requeriments.txt`**, exactly as shown above. Pillow is imported by the application for image handling and is included explicitly in this command. The NumPy constraint helps avoid binary compatibility problems with the older pandas and Matplotlib versions pinned in the repository; see the [NumPy troubleshooting guide](https://numpy.org/doc/stable/user/troubleshooting-importerror.html#downstream-importerror-attributeerror-or-c-api-abi-incompatibility).

### 4. Launch BatSignal

```powershell
.\.venv\Scripts\python.exe app_main.py
```

Run the application from the repository root so it can locate the `imagens/` assets and use the expected `dados/` storage folder. These commands use the virtual environment directly, so activation is optional.

## Usage

1. Connect your computer to the Wi-Fi network you want to evaluate.
2. Move to the first location and enter a room name in **Nome do cômodo**.
3. Set **Duração (segundos)** and **Intervalo (segundos)**. The defaults are **60 seconds** and **5 seconds**, respectively. Both values must be positive integers, and the interval must not exceed the duration.
4. Click **Iniciar Coleta** (Start collection) and keep the device in place until collection finishes. Successful readings appear in the status log.
5. Review the summary. Choose **Refazer Coleta** (Repeat collection) to measure the same room again, or **Próximo Cômodo** (Next room) to prepare another room.
6. Click **Ver Gráficos** (View charts) to inspect the collected measurements.
7. Enter a survey name in **Nome do Mapeamento**, then click **Salvar Mapeamento** (Save survey).
8. Use **Exportar Tudo** (Export all) to save an Excel workbook, or **Carregar Mapeamento** (Load survey) to open a previously saved survey.

A new successful collection using an existing room name replaces that room's measurements in the current survey. Save separate surveys when you want to preserve results from different sessions.

## Understanding the results

### Line charts

Each room has its own subplot showing signal strength by **measurement number**, with a dashed line marking the room average. The horizontal axis is a sample index, not elapsed time.

### Bar chart

Rooms are ordered from highest to lowest average signal strength. The current color rules are:

| Average signal | Color |
| --- | --- |
| Greater than 95% | Green |
| Greater than 92%, up to and including 95% | Orange |
| 92% or lower | Red |

These are application-specific thresholds, not guarantees of connection performance. The chart legend currently uses simplified boundary labels; the table above reflects the implemented comparisons.

### Collecting comparable measurements

- Use the same device, sampling settings, and device orientation across locations.
- Stay in one position during each collection.
- Use distinct room names for multiple measurement points, such as `Office - Desk` and `Office - Door`.
- Save separate surveys before and after moving a router or changing your setup.

## Data and exports

Saved surveys are stored locally in `dados/`, relative to the directory from which the application is launched. The folder is created when needed. Filenames combine the survey name with a timestamp.

Example of the current JSON format:

```json
{
  "nome": "Home - Baseline",
  "data": "2026-04-01 14:30:00",
  "comodos": {
    "Office": [
      { "tempo": "14:29:00", "forca": 94 },
      { "tempo": "14:29:05", "forca": 93 }
    ],
    "Living Room": [
      { "tempo": "14:30:00", "forca": 98 }
    ]
  }
}
```

The keys retain their current Portuguese names: `nome` is the survey name, `data` is its save date and time, `comodos` contains the rooms, `tempo` is the reading time, and `forca` is the signal percentage.

Excel exports contain the raw readings for each room and a **Resumo** (Summary) worksheet with minimum, maximum, average, and measurement count. JSON saving and Excel export are separate actions.

## Project structure

```text
BatSignal-wifi/
├── app_main.py          # Tkinter interface, collection workflow, and Excel export
├── wifi_coleta.py       # Wi-Fi signal collection through Windows netsh
├── wifi_dados.py        # JSON persistence and saved-survey management
├── wifi_graficos.py     # Matplotlib line and bar charts
├── requeriments.txt     # Pinned Python dependencies (current filename)
├── imagens/            # Application logo and icon assets
├── dados/              # Local surveys; created at runtime
├── PROJECT_CONTEXT.md  # Additional project background and future ideas
└── README.md
```

## Current limitations

- Collection depends on Windows `netsh` output and the Portuguese `Sinal` label. Linux, macOS, and other output languages are not currently supported by the collector.
- Both chart types use a fixed vertical range of **80–105%**, so weaker readings can fall outside the visible area. Check raw data or Excel exports when interpreting low signal levels.
- The line chart has a fixed palette of **five colors**; plotting more than five rooms currently raises an error.
- Readings store a time of day and a signal percentage, without network or access-point identifiers. Surveys cannot automatically distinguish changes in network or access point.
- The application provides room comparisons; it does not generate a floor-plan heatmap.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| No signal readings appear | Run `netsh wlan show interfaces` in a terminal. Confirm that Wi-Fi is connected and the output contains a numeric `Sinal` field. |
| The icon or other assets cannot be found | Launch the application from the repository root and keep the `imagens/` folder in place. |
| A Python module is missing | Install dependencies with the same `.venv` interpreter used to launch the app. The `PIL` import is supplied by Pillow. |
| NumPy or pandas reports a binary incompatibility | Recreate the environment using the suggested Python version and the installation command above, including `numpy<2`. |
| Charts fail or omit weak readings | Check the room count and the chart limits described above; use the Excel export to inspect raw values. |
| Excel export fails for a room name | Use short, distinct names without `:`, `\`, `/`, `?`, `*`, `[` or `]`. Avoid `Resumo`, which is reserved for the summary worksheet, and names that become identical after truncation to 31 characters. |

## Contributing

Bug reports and focused pull requests are welcome. When reporting a problem, include your Windows display language, Python version, steps to reproduce it, and any error messages. Remove personal network information from logs or screenshots before sharing them.

For a proposed change, describe the behavior it addresses and how you verified it. Useful areas for contributions include collection reliability, chart handling, automated tests, and interface translation.

## License

The repository does not currently include a `LICENSE` file. A license should be added to explicitly document the terms for reuse and distribution.
