# core/normalization.py
"""
Normalization utilities used by TOPSIS.
Currently TOPSIS uses vector normalization internally; this module
provides standalone helpers for alternative use-cases.
"""
from __future__ import annotations

import numpy as np


def vector_normalize(matrix: np.ndarray) -> np.ndarray:
    """
    Divide each column by its Euclidean norm.
    Zero-norm columns are left as-is (no division).
    """
    denom = np.sqrt((matrix ** 2).sum(axis=0))
    denom = np.where(denom == 0, 1.0, denom)
    return matrix / denom


def minmax_normalize(matrix: np.ndarray) -> np.ndarray:
    """
    Scale each column to [0, 1] using min-max normalization.
    Constant columns are mapped to 0.
    """
    col_min = matrix.min(axis=0)
    col_max = matrix.max(axis=0)
    rng = np.where((col_max - col_min) == 0, 1.0, col_max - col_min)
    return (matrix - col_min) / rng


def sum_normalize(matrix: np.ndarray) -> np.ndarray:
    """
    Divide each column by its sum.
    Zero-sum columns are left as-is.
    """
    col_sum = matrix.sum(axis=0)
    col_sum = np.where(col_sum == 0, 1.0, col_sum)
    return matrix / col_sum
