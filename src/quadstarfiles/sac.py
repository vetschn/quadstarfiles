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
The `process` function returns a tuple of data and metadata. The data is
structured as list of cycles, each cycle containing a list of scans.

.. code-block:: python

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
        ],
        [
            {
                "{{ scan_title }}": list[float],
                "{{ data_title }}": list[float],
            },
            {
                "{{ scan_title }}": list[float],
                "{{ data_title }}": list[float],
            },
        ],
    ]

The metadata dictionary is structured into a general header and
information on the cycles/scans. The "cycles" entry maps directly onto
the data.

.. code-block:: python

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

.. codeauthor:: Nicolas Vetsch <vetschnicolas@gmail.com>
"""
from datetime import datetime
from typing import Any, Union

import numpy as np

# The general header at the top of .sac files.
general_header_dtype = np.dtype(
    [
        ("data_index", "<i2"),
        ("software_id", "<i4"),
        ("version_major", "|u1"),
        ("version_minor", "|u1"),
        ("S", "|u1"),
        ("M", "|u1"),
        ("H", "|u1"),
        ("d", "|u1"),
        ("m", "|u1"),
        ("y", "|u1"),
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


def _read_value(data: bytes, offset: int, dtype: np.dtype) -> Any:
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
        item = [i.decode() if isinstance(i, bytes) else i for i in item]
        return dict(zip(value.dtype.names, item))
    return item.decode() if isinstance(item, bytes) else item


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


def process(fn: str) -> tuple[list, dict]:
    """Processes a Quadstar 32-bit analog data .sac file.

    Parameters
    ----------
    fn
        The file containing the trace(s) to parse.

    Returns
    -------
    tuple[list, dict]
        Tuple containing the data and metadata.

    """
    with open(fn, "rb") as sac_file:
        sac = sac_file.read()
    general = _read_value(sac, 0x0000, general_header_dtype)
    uts_base_s = _read_value(sac, 0x00C2, "<u4")
    # The ms part of the timestamps is actually saved as tenths of ms so
    # dividing by 10 here.
    uts_base_ms = _read_value(sac, 0x00C6, "<u2") / 10
    uts_base = uts_base_s + uts_base_ms / 1000
    scan_headers = _read_values(sac, 0x00C8, scan_header_dtype, general["n_scans"])
    # Find the data position of the first data-containing timestep.
    data_pos_0 = _find_first_data_position(scan_headers)
    cycle_length = general.pop("cycle_length")
    cycles = []
    cycles_meta = []
    for n in range(general["n_cycles"]):
        ts_offset = n * cycle_length
        uts_offset_s = _read_value(sac, data_pos_0 - 0x0006 + ts_offset, "<u4")
        uts_offset_ms = _read_value(sac, data_pos_0 - 0x0002 + ts_offset, "<u2") / 10
        uts_timestamp = uts_base + (uts_offset_s + uts_offset_ms / 1000)
        scans = []
        scans_meta = []
        for header in scan_headers:
            if header["type"] != 0x11:
                continue
            info = _read_value(sac, header["info_position"], scan_info_dtype)
            # Construct the masses.
            scan_values = np.linspace(
                info["first_mass"],
                info["first_mass"] + info["scan_width"],
                info["scan_width"] * info["values_per_mass"],
                endpoint=False,
            ).tolist()
            # Read and construct the data.
            cycle_data_pos = header["data_position"] + ts_offset
            # Determine the detector's full scale range.
            fsr = 10 ** _read_value(sac, cycle_data_pos + 0x0004, "<i2")
            # The n_datapoints value at cycle_data_position is sometimes
            # wrong. Calculating this here works, however.
            n_datapoints = info["scan_width"] * info["values_per_mass"]
            data_values = _read_values(
                sac, cycle_data_pos + 0x0006, "<f4", n_datapoints
            )
            # Once a scan_value leaves the FSR it jumps to the maximum
            # of a float32. These values should be NaNs instead.
            data_values = [d if d <= fsr else float("NaN") for d in data_values]
            scans.append(
                {info["scan_title"]: scan_values, info["data_title"]: data_values,}
            )
            scans_meta.append(
                {
                    "uts": uts_timestamp,
                    "comment": info["comment"],
                    "data_format": info["data_format"],
                    "fsr": fsr,
                    "scan_unit": info["scan_unit"],
                    "data_unit": info["data_unit"],
                }
            )
        cycles.append(scans)
        cycles_meta.append(scans_meta)

    version = str(general["version_major"]) + "." + str(general["version_minor"])
    measure_uts = datetime(
        general["y"] + 1900,
        general["m"],
        general["d"],
        general["H"],
        general["M"],
        general["S"],
    ).timestamp()
    meta = {
        "general": {
            "software_id": general["software_id"],
            "software_version": version,
            "measure_uts": measure_uts,
            "author": general["author"],
            "n_cycles": general["n_cycles"],
            "n_scans": general["n_scans"],
        },
        "cycles": cycles_meta,
    }
    return cycles, meta
