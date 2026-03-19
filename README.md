# UCAG
Universal Custom Artifact Generator

A utility that automatically generates Magnet AXIOM-compatible Python artifact scripts from CSV files.

## Overview

If you have CSV output from a third-party tool — a mobile extraction script, drone data export, or any other source — `ucag` reads the column headers and generates ready-to-use custom artifact `.py` files for AXIOM Process.  This lets you bring external CSV results into an AXIOM case alongside natively processed artifacts, giving you a single, searchable, filterable workspace for all your evidence.

## Use Cases

- Running a third-party tool over a phone extraction that outputs CSVs → generate custom artifacts → run in AXIOM alongside a standard examination for a unified case
- Importing drone telemetry or vehicle data CSVs into AXIOM
- Rapidly onboarding any tabular data source into AXIOM without manually writing artifact scripts

## Requirements

- Python 3.7+
- Magnet AXIOM (Process or AUTOMATE)

No third-party Python packages are required.

## Installation

Clone or download this repository, then place the script anywhere accessible from your command line or PowerShell session.

```
git clone https://github.com/MagnetForensics/UCAG.git
```

## Usage

```
python ucag.py <input_csv_folder> <output_py_folder>
```

**Example:**

```
python ucag.py "./csvs" "./artifacts_py"
```

This reads every `.csv` file in `./csvs`, generates a corresponding `.py` artifact script in `./artifacts_py`, and clears any previously generated scripts from the output folder to prevent stale artifacts.

## Deploying Generated Artifacts

Copy the generated `.py` files to the appropriate plugins folder before running AXIOM Process:

| Product | Plugins Path |
|---|---|
| AXIOM GUI | `C:\Program Files\Magnet Forensics\Magnet AXIOM\AXIOM Process\plugins` |
| AUTOMATE Node | `C:\Program Files\Magnet Forensics\Magnet AUTOMATE\agent\AXIOM Process\plugins` |

After copying, run your case in AXIOM Process with the source CSV files as input.  The custom artifacts will appear alongside any other artifacts from the examination.

## Data Type Detection

`ucag` performs best-effort data type mapping based on column header names:

| Column Name Pattern | AXIOM Data Type |
|---|---|
| Contains `time`, `date`, or `timestamp` | DateTime |
| Contains `latitude` | Latitude (Float) |
| Contains `longitude` | Longitude (Float) |
| Contains `lat` or `lon` | Float |
| All others | String |

DateTime and GPS columns will be properly represented in AXIOM's timeline and mapping views.

## Example Workflow

```
[Third-party tool]
        │
        ▼
  CSV output files
        │
        ▼
  python ucag.py ./csvs ./artifacts_py
        │
        ▼
  Copy .py files → AXIOM plugins folder
        │
        ▼
  Run AXIOM Process with CSVs as source
        │
        ▼
  Unified AXIOM case with CSV results + native artifacts
        │
        ▼
  Export to Portable Case / AXIOM Review
```

## Notes

- CSV files must have a header row as the first line.
- UTF-8 and UTF-8-BOM encoded files are both supported.
- The script clears previously generated `.py` files from the output directory on each run to avoid stale artifact conflicts.
- Class names and output filenames are sanitized automatically to ensure valid Python syntax regardless of special characters in the CSV filename.


