#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Functions for converting Quadstar 32-bit analog data to DataFrame,
.csv and .xlsx.

Author:         Nicolas Vetsch (veni@empa.ch / vetschnicolas@gmail.com)
Organisation:   EMPA Dübendorf, Materials for Energy Conversion (501)
Date:           2021-11-02

"""
import os

import numpy as np
import pandas as pd

from .sac import parse_sac


def _construct_path(other_path: str, ext: str) -> str:
    """Constructs a new file path from the given path and extension.

    Parameters
    ----------
    other_path
        The path to some file.
    ext
        The new extension to add to the other_path.

    Returns
    -------
    str
        A new filepath with the given extension.

    """
    head, tail = os.path.split(other_path)
    tail, __ = os.path.splitext(tail)
    this_path = os.path.join(head, tail + ext)
    return this_path


def parse(path: str) -> dict:
    """Parses a Quadstar 32-bit analog data file.

    The function finds the file extension and tries to choose the
    correct parser.

    Note
    ----
    Currently only the .sac file extension is implemented.

    Parameters
    ----------
    path
        The path to a Quadstar 32-bit analog data file (.sac).

    Returns
    -------
    list or dict
        The parsed file.

    """
    __, ext = os.path.splitext(path)
    if ext == ".sac" or ".SAC":
        parsed = parse_sac(path)
    else:
        raise ValueError(f"Unrecognized file extension: {ext}")
    return parsed


def to_df(path: str) -> pd.DataFrame:
    """Extracts the data from a Quadstar 32-bit analog data file and
    returns it as Pandas DataFrame.

    The function finds the file extension and tries to choose the
    correct parser.

    Note
    ----
    Currently only the .sac file extension is implemented.

    Parameters
    ----------
    path
        The path to a Quadstar 32-bit analog data file (.sac).

    Returns
    -------
    pd.DataFrame
        Data parsed from an .sac file.

    """
    __, ext = os.path.splitext(path)
    if ext != ".sac" and ext != ".SAC":
        raise ValueError(f"Unrecognized file extension: {ext}")
    sac = parse_sac(path)
    cycles = sac["cycles"]
    first_cycle = cycles[0]
    # Determine the masses.
    masses = []
    for scan in first_cycle:
        first_mass = scan["info"]["first_mass"]
        scan_width = scan["info"]["scan_width"]
        values_per_mass = scan["info"]["values_per_mass"]
        scan_masses = np.linspace(
            first_mass,
            first_mass + scan_width,
            scan_width * values_per_mass,
            endpoint=False,
        )
        masses += list(scan_masses)
    # Read the data from each scan.
    cycles_data = [None] * len(cycles)
    for n, cycle in enumerate(cycles):
        for scan in cycle:
            if cycles_data[n] is None:
                cycles_data[n] = scan["datapoints"]
            else:
                cycles_data[n] += scan["datapoints"]
    # Build the DataFrame.
    cycles_data = np.array(cycles_data).T
    data = np.c_[masses, cycles_data]
    columns = ["mass"] + [f"cycle {n}" for n in range(1, len(cycles) + 1)]
    return pd.DataFrame(data=data, columns=columns)


def to_csv(path: str, csv_path: str = None) -> None:
    """Extracts the data from an .mpt/.mpr file or from the techniques
    in an .mps file and writes it to a number of .csv files.

    Parameters
    ----------
    path
        The path to a Quadstar 32-bit analog data file (.sac).
    csv_path
        Base path to use for the .csv files. Defaults to construct the
        .csv filename from the mpt_path.

    """
    df = to_df(path)
    if csv_path is None:
        csv_path = _construct_path(path, ".csv")
    df.to_csv(csv_path, float_format="%.10e", index=False)


def to_xlsx(path: str, xlsx_path: str = None) -> None:
    """Extracts the data from an .sac file and writes it to an Excel
    file.

    Parameters
    ----------
    path
        The path to a Quadstar 32-bit analog data file (.sac).
    xlsx_path (optional)
        Path to the Excel file to write. Defaults to construct the
        filename from the mpt_path.

    """
    df = to_df(path)
    if xlsx_path is None:
        xlsx_path = _construct_path(path, ".xlsx")
    df.to_excel(xlsx_path, index=False, sheet_name="SCA Cycles")
