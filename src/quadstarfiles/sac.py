#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read Quadstar 32-bit analog data into dictionaries.

The sac2dat.c code from Dr. Moritz Bubek (https://www.bubek.org/sac2dat.php)
was a really useful stepping stone for this Python adaptation.

Pretty much the entire file format has been reverse engineered. There
are still one or two unknown fields.


File Structure of `.sac` Files
------------------------------
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
...
0xc2 "uts_base_s"
0xc6 "uts_base_ms"
# Scan header. Read these 9 bytes for every scan (n_scans).
0xc8 + (n * 0x09) "type"
0xc9 + (n * 0x09) "info_position"
0xcd + (n * 0x09) "data_position"
...
# Scan info. Read these 137 bytes for every scan where type != 0x11.
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
# UTS offset. Read these 6 bytes for every cycle (n_cycles).
0xc2 + (n * cycle_length) "uts_offset_s"
0xc6 + (n * cycle_length) "uts_offset_ms"
# Read everything remaining below for every cycle and every scan where type != 0x11.
data_position + (n * cycle_length) + 0x00 "n_datapoints"
data_position + (n * cycle_length) + 0x04 "data_range"
# Datapoints. Read these 4 bytes (scan_width * values_per_mass) times.
data_position + (n * cycle_length) + 0x06 "datapoints"
...


Structure of Parsed Data
------------------------
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
        {
            'uts',
            'scans': [
                {
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
                    },
                    'n_datapoints',
                    'data_range',
                    'datapoints': []
                },
                {...},
            ],
        },
        {...},
    ],
}


Author:         Nicolas Vetsch (veni@empa.ch / vetschnicolas@gmail.com)
Organisation:   EMPA Dübendorf, Materials for Energy Conversion (501)
Date:           2021-11-02

"""
from typing import Any, Union

import numpy as np

# The general header at the top of .sac files.
general_header_dtype = np.dtype(
    [
        ("data_index", "<i2"),
        ("software_id", "<i4"),
        ("software_version_major", "|u1"),
        ("software_version_minor", "|u1"),
        ("measure_second", "|u1"),
        ("measure_minute", "|u1"),
        ("measure_hour", "|u1"),
        ("measure_day", "|u1"),
        ("measure_month", "|u1"),
        ("measure_year", "|u1"),
        ("author", "|S86"),
        ("n_cycles", "<i4"),
        ("n_scans", "<i2"),
        ("cycle_length", "<i4"),
    ]
)


scan_header_dtype = np.dtype(
    [("type", "|u1"), ("info_position", "<i4"), ("data_position", "<i4"),]
)


scan_info_dtype = np.dtype(
    [
        ("data_format", "<u2"),
        ("data_title", "|S13"),
        ("data_unit", "|S14"),
        ("scan_title", "|S13"),
        ("scan_unit", "|S14"),
        ("comment", "|S66"),
        ("first_mass", "<f4"),
        ("scan_width", "<u2"),
        ("values_per_mass", "|u1"),
        ("zoom_start", "<f4"),
        ("zoom_end", "<f4"),
    ]
)


def _read_value(
    data: bytes, offset: int, dtype: np.dtype, encoding: str = "windows-1252"
) -> Any:
    """Reads a single value from a buffer at a certain offset.

    Just a handy wrapper for np.frombuffer().

    The read value is converted to a built-in datatype using
    np.dtype.item().

    Parameters
    ----------
    data
        An object that exposes the buffer interface. Here always bytes.

    offset
        Start reading the buffer from this offset (in bytes).

    dtype
        Data-type to read in.

    encoding
        The encoding of the bytes to be converted.

    Returns
    -------
    Any
        The unpacked and converted value from the buffer.

    """
    value = np.frombuffer(data, offset=offset, dtype=dtype, count=1)
    item = value.item()
    if value.dtype.names:
        item = [i.decode(encoding) if isinstance(i, bytes) else i for i in item]
        return dict(zip(value.dtype.names, item))
    return item.decode(encoding) if isinstance(item, bytes) else item


def _read_values(
    data: bytes, offset: int, dtype: np.dtype, count: int
) -> Union[list, list[dict]]:
    """Reads in multiple values from a buffer starting at offset.

    Just a handy wrapper for np.frombuffer() with count >= 1.

    The read values are converted to a list of built-in datatypes using
    np.ndarray.tolist().

    Parameters
    ----------
    data
        An object that exposes the buffer interface. Here always bytes.

    offset
        Start reading the buffer from this offset (in bytes).

    dtype
        Data-type to read in.

    count
        Number of items to read. -1 means all data in the buffer.

    Returns
    -------
    Any
        The values read from the buffer as specified by the arguments.

    """
    values = np.frombuffer(data, offset=offset, dtype=dtype, count=count)
    if values.dtype.names:
        return [dict(zip(value.dtype.names, value.item())) for value in values]
    # The ndarray.tolist() method converts numpy scalars in ndarrays to
    # built-in python scalars. Thus not just list(values).
    return values.tolist()


def _find_first_data_position(scan_headers: list[dict]) -> int:
    """Finds the data position of the first scan containing any data."""
    for header in scan_headers:
        if header["type"] != 0x11:
            continue
        return header["data_position"]


def parse_sac(path: str) -> dict:
    """Parses a Quadstar 32-bit analog data .sac file.

    Parameters
    ----------
    path
        Filepath of the Quadstar 32-bit analog data file to read in.

    Returns
    -------
    dict
        The parsed file contents.

    """
    with open(path, "rb") as sac_file:
        sac = sac_file.read()
    general_header = _read_value(sac, 0x0000, general_header_dtype)
    uts_base_s = _read_value(sac, 0x00C2, "<u4")
    uts_base_ms = _read_value(sac, 0x00C6, "<u2") * 1e-1
    uts_base = uts_base_s + uts_base_ms * 1e-3
    scan_headers = _read_values(
        sac, 0x00C8, scan_header_dtype, general_header["n_scans"]
    )
    # Find the data position of the first data-containing cycle.
    first_data_position = _find_first_data_position(scan_headers)
    cycles = []
    for n in range(general_header["n_cycles"]):
        cycle_offset = n * general_header["cycle_length"]
        uts_offset_s = _read_value(
            sac, first_data_position - 0x0006 + cycle_offset, "<u4"
        )
        uts_offset_ms = (
            _read_value(sac, first_data_position - 0x0002 + cycle_offset, "<u2") * 1e-1
        )
        uts_timestamp = uts_base + (uts_offset_s + uts_offset_ms * 1e-3)
        scans = []
        for header in scan_headers:
            if header["type"] != 0x11:
                continue
            info = _read_value(sac, header["info_position"], scan_info_dtype)
            cycle_data_position = header["data_position"] + cycle_offset
            n_datapoints = _read_value(sac, cycle_data_position + 0x0000, "<i4")
            data_range = _read_value(sac, cycle_data_position + 0x0004, "<i2")
            actual_n_datapoints = info["scan_width"] * info["values_per_mass"]
            datapoints = _read_values(
                sac, cycle_data_position + 0x0006, "<f4", actual_n_datapoints
            )
            scans.append(
                {
                    "header": header,
                    "info": info,
                    "n_datapoints": n_datapoints,
                    "data_range": data_range,
                    "datapoints": datapoints,
                }
            )
        cycles.append({"uts": uts_timestamp, "scans": scans})
    return {"header": general_header, "cycles": cycles}
