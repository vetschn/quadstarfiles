#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Functions for converting Quadstar 32-bit analog data to DataFrame,
.csv and .xlsx.

See the actual parser to get an idea of the data format used.

.. codeauthor:: Nicolas Vetsch <vetschnicolas@gmail.com>
"""
import os

import pandas as pd

from quadstarfiles import sac


def _construct_fn(other_fn: str, ext: str) -> str:
    """Constructs a new file name from the given name and extension.

    Parameters
    ----------
    other_fn
        The path to some file.
    ext
        The new extension to add to the other_fn.

    Returns
    -------
    str
        A new file name with the given extension.

    """
    head, tail = os.path.split(other_fn)
    tail, __ = os.path.splitext(tail)
    this_fn = os.path.join(head, tail + ext)
    return this_fn


def process(fn: str) -> tuple[list, dict]:
    """Processes a Quadstar 32-bit analog file.

    Parameters
    ----------
    fn
        The path to a Quadstar 32-bit analog file.

    Returns
    -------
    tuple[list, dict]
        The processed file. A nested list containing cycles and scans in
        each cycle and a dictionary containing metadata.
    """
    __, ext = os.path.splitext(fn)
    if ext in {".sac", ".SAC"}:
        return sac.process(fn)
    raise ValueError(f"Unrecognized file extension: {ext}")


def to_df(fn: str) -> pd.DataFrame:
    """Extracts data from a Quadstar file and returns it as DataFrame.
    
    The DataFrame will have a hierarchical MultiIndex, top-level being
    the cycle and second level being the scans in each cycle.
    
    The DataFrame.attrs will contain any metadata.

    Parameters
    ----------
    fn
        The path to a Quadstar 32-bit analog data file.

    Returns
    -------
    pd.DataFrame
        Data parsed from a .sac file.

    """
    cycles, meta = process(fn)
    dfs_cycles = []
    for scans in cycles:
        dfs_scans = []
        for scan in scans:
            dfs_scans.append(pd.DataFrame.from_dict(scan))
        dfs_cycles.append(
            pd.concat(dfs_scans, keys=range(len(dfs_scans)), names=["Scan"])
        )
    df = pd.concat(dfs_cycles, keys=range(len(dfs_cycles)), names=["Cycle"], axis=1)
    df.attrs = meta
    return df


def to_csv(fn: str, csv_fn: str = None) -> None:
    """Extracts the data from an Quadstar file and writes it to csv.

    Parameters
    ----------
    fn
        The path to the EC-Lab file to read in.
    csv_fn
        Base path to use for the csv file. Defaults to generate the csv
        file name from the input file name.

    """
    df = to_df(fn)
    if csv_fn is None:
        csv_fn = _construct_fn(fn, ".csv")
    df.to_csv(csv_fn, float_format="%.10e")


def to_excel(fn: str, excel_fn: str = None) -> None:
    """Extracts the data from an Quadstar file and writes it to Excel.

    Parameters
    ----------
    fn
        The path to the EC-Lab file to read in.
    excel_fn
        Path to the Excel file to write. Defaults to generate the xlsx
        file name from the input file name.

    """
    df = to_df(fn)
    if excel_fn is None:
        excel_fn = _construct_fn(fn, ".xlsx")
    df.to_excel(excel_fn)
