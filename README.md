### *NOTE*

This parser is no longer being maintained. Consider using the `masstrace` parser built into [yadg](https://github.com/dgbowl/yadg) for an up to date version.

---

# quadstarfiles

This little package parses and converts `.sac` files from Pfeiffer's Quadstar 32-bit (QMS 422 & QMS 400 Quadrupole Mass Spectrometers) into Pandas DataFrames, Excel files and CSV files.

There is a quirk in Quadstar 32-bit's *Dispsav* utility: The program does not allow you to write multiple/all cycles stored in a `.sac` file as human-readable ASCII. Instead you have to select one cycle after the other. With this parser/converter you can export all the cycles stored in a `.sac` in one go.

The [sac2dat.c](https://www.bubek.org/sac2dat.php) code from Dr. Moritz Bubek was a really useful stepping stone for this.

## Installation
Use [pip](https://pip.pypa.io/en/stable/) to install quadstarfiles.

```bash
> cd ./quadstarfiles
> pip install .
```

## Example Usage

### `process`: Processing Into Dictionaries
Process the data as it is stored in the corresponding file. The method
automatically determines filetype and tries to apply the respective
parser.

```python
import quadstarfiles as qsf
cycles, meta = qsf.process("./sac_files/airdemo.sac")
```

See [Filetypes and Processed Data Structure](#filetypes-and-processed-data-structure)
to learn how the returned data is structured.

### `to_df`: Processing Into Dataframe
Processes the file and converts it into a [Pandas `DataFrame`](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html) with a [hierarchical index](https://pandas.pydata.org/pandas-docs/stable/user_guide/advanced.html#multiindex-advanced-indexing). The top-level
index is the cycle number and the second index corresponds to scan
number within each cycle.

The `pd.DataFrame.attrs` will contain all the processed metadata.

```python
import quadstarfiles as qsf
df = qsf.to_df("./sac_files/airdemo.sac")
```

### `to_csv`: Converting to CSV
Process the file and write the data part into a `.csv` file at the
specified location.

```python
import quadstarfiles as qsf
qsf.to_csv("./sac_files/airdemo.sac", csv_fn="./csv_files/airdemo.csv")
```

The `csv_fn` parameter is optional. If left away, the method writes a
`.csv` file into the same folder as the input file.

### `to_excel`: Converting to Excel
Process the file and write the data part into an Excel `.xlsx` file at
the specified location.

```python
import quadstarfiles as qsf
qsf.to_excel("./sac_files/airdemo.sac")
```

The `excel_fn` parameter is optional. If left away, the method writes
a `.xlsx` file at the location of the input file.

## Filetypes and Processed Data Structure.
### `.sac` File Structure
```python
# General header
0x00 "data_index"
0x02 "software_id"
0x06 "software_version_major"
0x07 "software_version_minor"
0x08 "measure_second"
0x09 "measure_minute"
0x0a "measure_hour"
0x0b "measure_day"
0x0c "measure_month"
0x0d "measure_year"
0x0f "author"
0x64 "n_cycles"
0x68 "n_scans"
0x6a "cycle_length"
...
# Not sure what sits from 0x6e to 0xc2.
0xc2 "uts_base_s"
0xc6 "uts_base_ms"
# Scan header: read these 9 bytes n_scans times.
0xc8 + (n * 0x09) "type"
0xc9 + (n * 0x09) "info_position"
0xcd + (n * 0x09) "data_position"
...
# Scan info: read these 137 bytes (n_scans where type == 0x11) times.
info_position + 0x00 "data_format"
info_position + 0x02 "data_title"
info_position + 0x0f "data_unit"
info_position + 0x1d "scan_title"
info_position + 0x2a "scan_unit"
info_position + 0x38 "comment"
info_position + 0x7a "first_mass"
info_position + 0x7e "scan_width"
info_position + 0x80 "values_per_mass"
info_position + 0x81 "zoom_start"
info_position + 0x85 "zoom_end"
...
# UTS offset: read these 6 bytes for every cycle.
0xc2 + (n * cycle_length) "uts_offset_s"
0xc6 + (n * cycle_length) "uts_offset_ms"
# Read everything below for every cycle.
# Datapoints info: read these 6 bytes (n_scans where type == 0x11) times.
data_position + (n * cycle_length) + 0x00 "n_datapoints"
data_position + (n * cycle_length) + 0x04 "data_range"
# Datapoints: read these 4 bytes (scan_width * values_per_mass) times
data_position + (n * cycle_length) + 0x06 "datapoints"
...
```

### Processed `.sac` Files
```python
cycles, meta = qsf.process("./sac_files/airdemo.sac")
```

The `cycles` returned from the `process` function are a nested list. The
outer list corresponds to the cycles, the inner one to the scans in each
cycle.

```python
[
    [
        {
            "{{ scan_title }}": list[float],
            "{{ data_title }}": list[float],
        },
        {
            "{{ scan_title }}": list[float],
            "{{ data_title }}": list[float],
        },
        ...
    ],
    ...
]

```

The metadata dictionary is structured into a general header and
information on the cycles/scans. The "cycles" entry maps directly onto
the data.

The `meta` processed from `.sac` files looks like this:


```python
{
    "general": {
        "software_id": str
        "software_version": str
        "measure_uts": float
        "author": str
        "n_cycles": int
        "n_scans": int
    },
    "cycles": [
        [
            {
                "uts": float,
                "comment": str,
                "data_format": int,
                "fsr": float,
                "scan_unit": str
                "data_unit": str,
            },
            {
                "uts": float,
                "comment": str,
                "data_format": int,
                "fsr": float,
                "scan_unit": str
                "data_unit": str,
            },
        ],
    ],
}
```
