#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read Quadstar 32-bit analog data into dictionaries.

The sac2dat.c code from Dr. Moritz Bubek (https://www.bubek.org/sac2dat.php)
was a really useful stepping stone for this Python adaptation.

Pretty much the entire file format has been reverse engineered. There
are still one or two unknown fields.

TODO: The parse_sac function could use some more thinking. This is a
first, working solution.

Author:         Nicolas Vetsch (veni@empa.ch / vetschnicolas@gmail.com)
Organisation:   EMPA Dübendorf, Materials for Energy Conversion (501)
Date:           2021-11-02

"""
from typing import Any

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


def _read_values(data: bytes, offset: int, dtype, count) -> list:
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
    # The ndarray.tolist() method converts python scalars to numpy
    # scalars, hence not just list(values).
    return values.tolist()


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
    cycles = []
    for n in range(general_header["n_cycles"]):
        cycle_offset = n * general_header["cycle_length"]
        uts_offset_s = _read_value(sac, 0x00C2 + cycle_offset, "<u4")
        uts_offset_ms = _read_value(sac, 0x00C6 + cycle_offset, "<u4") * 1e-1
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
            scan = {
                "header": header,
                "info": info,
                "n_datapoints": n_datapoints,
                "data_range": data_range,
                "datapoints": datapoints,
            }
            scans.append(scan)
        cycle = {"uts": uts_timestamp, "scans": scans}
        cycles.append(cycle)
    return {"header": general_header, "cycles": cycles}
