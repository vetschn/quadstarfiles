# quadstarfiles

This little package parses and converts `.sac` files from Pfeiffer's Quadstar 32-bit (QMS 422 & QMS 400 Quadrupole Mass Spectrometers) into Pandas DataFrames, Excel files and CSV files.

There is a quirk in Quadstar 32-bit's *Dispsav* utility: The program does not allow you to write multiple/all cycles stored in a `.sac` file as human-readable ASCII. Instead you have to select one cycle after the other. With this parser/converter you can export all the cycles stored in a `.sac` in one go.

```bash
> cd ./quadstarfiles
> pip install .
```

## Example Usage

### `parse`

Parse the data as it is stored in the corresponding file. The method automatically determines filetype and tries to apply the respective parser.

```python
>>> import quadstarfiles as qsf
>>> qsf.parse("./sac_files/airdemo.sac")
```


### `to_df`

Parse the file and transform only the data part into a Pandas `DataFrame`.

```python
>>> import quadstarfiles as qsf
>>> qsf.to_df("./sac_files/airdemo.sac")
```


### `to_csv`

Parse the file and write the data part into a `.csv` file.

```python
>>> import quadstarfiles as qsf
>>> qsf.to_csv("./sac_files/airdemo.sac")
```


### `to_xlsx`

Parse the file and write the data part into an Excel `.xlsx` file.

```python
>>> import quadstarfiles as qsf
>>> qsf.to_xlsx("./sac_files/airdemo.sac")
```

## `.sac` File Structure
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
...
0x64 "n_cycles"
0x68 "n_scans"
0x6a "cycle_length"
...
0xc2 "uts_base_s"
0xc6 "uts_base_ms"
# Scan header: read these 9 bytes n_scans times.
0xc8 + (n * 0x09) "type"
0xc9 + (n * 0x09) "info_position"
0xcd + (n * 0x09) "data_position"
...
# Scan info: read these 137 bytes (n_scans where type == 0x11) times.
info_position + (n * 0x89) + 0x00 "data_format"
info_position + (n * 0x89) + 0x02 "data_title"
info_position + (n * 0x89) + 0x0f "data_unit"
info_position + (n * 0x89) + 0x1d "scan_title"
info_position + (n * 0x89) + 0x2a "scan_unit"
info_position + (n * 0x89) + 0x38 "comment"
info_position + (n * 0x89) + 0x7a "first_mass"
info_position + (n * 0x89) + 0x7e "scan_width"
info_position + (n * 0x89) + 0x80 "values_per_mass"
info_position + (n * 0x89) + 0x81 "zoom_start"
info_position + (n * 0x89) + 0x85 "zoom_end"
...
# UTS offset: read these 6 bytes for every cycle.
0xc2 + (n * cycle_length) "uts_offset_s"
0xc6 + (n * cycle_length) "uts_offset_ms"
# Read everything below for every cycle. Each cycle contains a number of scans.
# Datapoints info: read these 6 bytes (n_scans where type == 0x11) times.
data_position + (n * cycle_length) + 0x00 "n_datapoints"
data_position + (n * cycle_length) + 0x04 "data_range"
# Datapoints: read these 4 bytes (scan_width * values_per_mass) times
data_position + (n * cycle_length) + 0x06 "datapoints"
...
```

## Data Format

```python
{
    'header': {
        'data_index',
        'software_id',
        'software_version_major',
        'software_version_minor',
        'measure_second',
        'measure_minute',
        'measure_hour',
        'measure_day',
        'measure_month',
        'measure_year',
        'author',
        'n_cycles',
        'n_scans',
        'cycle_length',
    },
    'cycles': [
        [
            {
                'cycle'
                'header': {
                    'type',
                    'info_position',
                    'data_position',
                },
                'info': {
                    'data_format',
                    'data_title',
                    'data_unit',
                    'scan_title',
                    'scan_unit',
                    'comment',
                    'first_mass',
                    'scan_width',
                    'values_per_mass',
                    'zoom_start',
                    'zoom_end',
                    'uts',
                },
                'n_datapoints',
                'data_range',
                'datapoints': []
            },
            {
                ...
            },
        ],
        [{
            ...
        }],
    ],
    'scans': [
        {
            'cycle',
            'header': {
                'type',
                'info_position',
                'data_position',
            },
            'info': {
                'data_format',
                'data_title',
                'data_unit',
                'scan_title',
                'scan_unit',
                'comment',
                'first_mass',
                'scan_width',
                'values_per_mass',
                'zoom_start',
                'zoom_end',
                'uts',
            },
            'n_datapoints',
            'data_range',
            'datapoints': [],
        },
        {
            ...
        },
    ],
}

```