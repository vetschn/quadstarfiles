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
from numpy.lib import recfunctions as rfn


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
        ("author", "|S20"),
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
    # There is a peculiar timestamp at the top of the file.
    general_header = _read_value(sac, 0, general_header_dtype)
    n_cycles = _read_value(sac, 100, "<i4")
    n_scans = _read_value(sac, 104, "<i2")
    cycle_length = _read_value(sac, 106, "<i4")
    scan_headers = _read_values(sac, 200, scan_header_dtype, n_scans)
    header = general_header.update(
        {"n_cycles": n_cycles, "n_scans": n_scans, "cycle_length": cycle_length,}
    )
    # Iterate through cycles and scan blocks to get all the scan data in
    # the present .sac file.
    scans = []
    cycles = [None] * n_cycles
    for n in range(n_cycles):
        for scan_header in scan_headers:
            if scan_header["type"] != 0x11:
                # Usually there is a 0x0F type scan at the start that
                # does not contain any data.
                continue
            info_position = scan_header["info_position"]
            scan_info = _read_value(sac, info_position, scan_info_dtype)
            data_position = scan_header["data_position"] + n * cycle_length
            n_datapoints = _read_value(sac, data_position, "<i4")
            data_range = _read_value(sac, data_position + 4, "<i2")
            # NOTE: Against all intuition, do not read (n_datapoints)
            # values but read (scan_width*values_per_mass) values.
            scan_width = scan_info["scan_width"]
            values_per_mass = scan_info["values_per_mass"]
            datapoints = _read_values(
                sac, data_position + 6, "<f4", scan_width * values_per_mass
            )
            scan = {
                "cycle": n,
                "header": scan_header,
                "info": scan_info,
                "n_datapoints": n_datapoints,
                "data_range": data_range,
                "datapoints": datapoints,
            }
            scans.append(scan)
            if cycles[n] is None:
                cycles[n] = [scan]
            else:
                cycles[n] += [scan]
    # Find the timestamp of each cycle.
    # TODO: Do this in a nicer and faster way.
    # Standard POSIX timestamp.
    uts_base_s = _read_value(sac, 194, "<u4")
    uts_base_ms = float(_read_value(sac, 198, "<u2")) * 1e-1
    base_uts_offset_position = scans[0]["header"]["data_position"] - 6
    for n in range(n_cycles):
        uts_offset_position = base_uts_offset_position + n * cycle_length
        uts_offset_s = _read_value(sac, uts_offset_position, "<u4")
        uts_offset_ms = _read_value(sac, uts_offset_position + 4, "<u2") * 1e-1
        for scan in cycles[n]:
            scan["info"]["uts"] = (
                uts_base_s + uts_offset_s + 1e-3 * (uts_base_ms + uts_offset_ms)
            )
    return {"header": header, "cycles": cycles, "scans": scans}
