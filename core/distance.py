# core/distance.py
"""
Distance metrics for TOPSIS ideal-solution separation.
TOPSIS currently uses Euclidean distance exclusively.
"""
from __future__ import annotations

import numpy as np


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Euclidean distance between two 1-D vectors."""
    return float(np.sqrt(np.sum((a - b) ** 2)))


def separation_measures(
    weighted_matrix: np.ndarray,
    pis: np.ndarray,
    nis: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute S* (distance to PIS) and S- (distance to NIS) for every alternative.

    Parameters
    ----------
    weighted_matrix : (m, n) ndarray
    pis : (n,) ndarray — positive ideal solution
    nis : (n,) ndarray — negative ideal solution

    Returns
    -------
    s_pos, s_neg : (m,) ndarrays
    """
    s_pos = np.sqrt(((weighted_matrix - pis) ** 2).sum(axis=1))
    s_neg = np.sqrt(((weighted_matrix - nis) ** 2).sum(axis=1))
    return s_pos, s_neg
