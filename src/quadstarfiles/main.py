#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Functions for converting Quadstar 32-bit analog data to DataFrame,
.csv and .xlsx.

Author:         Nicolas Vetsch (veni@empa.ch / vetschnicolas@gmail.com)
Organisation:   EMPA Dübendorf, Materials for Energy Conversion (501)
Date:           2021-11-02

"""
import os
from typing import Union

import numpy as np
import pandas as pd

from quadstarfiles.sac import parse_sac


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
    if ext in {".sac", ".SAC"}:
        parsed = parse_sac(path)
    else:
        raise ValueError(f"Unrecognized file extension: {ext}")
    return parsed


def to_df(path: str) -> pd.DataFrame:
    """Extracts the data from a Quadstar 32-bit analog data file and
    returns it as a list (cycles) of lists (scans) of Pandas DataFrames.

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
    sac = parse(path)
    # Read the data from each scan in each cycle.
    cycles = []
    for cycle in sac["cycles"]:
        scans = []
        for scan in cycle["scans"]:
            mass = np.linspace(
                scan["info"]["first_mass"],
                scan["info"]["first_mass"] + scan["info"]["scan_width"],
                scan["info"]["scan_width"] * scan["info"]["values_per_mass"],
                endpoint=False,
            ).tolist()
            df = pd.DataFrame(
                {
                    scan["info"]["scan_title"]: mass,
                    scan["info"]["data_title"]: scan["datapoints"],
                }
            )
            scans.append(df)
        cycles.append(pd.concat(scans, keys=range(len(scans)), names=["Scan"]))
    df = pd.concat(cycles, keys=range(len(cycles)), names=["Cycle"], axis=1)
    return df


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
    df.to_csv(csv_path, float_format="%.10e")


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
    df.to_excel(xlsx_path)
