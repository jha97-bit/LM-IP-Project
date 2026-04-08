# core/validation.py
"""
Input validation helpers shared across TOPSIS and VFT pipelines.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np


def validate_matrix(
    matrix: np.ndarray,
    alternative_names: List[str],
    criterion_names: List[str],
) -> Tuple[bool, List[str]]:
    """
    Validate a raw measurement matrix.

    Returns (is_valid, list_of_issues).
    """
    issues: List[str] = []

    if matrix.ndim != 2:
        issues.append("Matrix must be 2-dimensional.")
        return False, issues

    m, n = matrix.shape

    if m == 0:
        issues.append("Matrix has no alternatives.")
    if n == 0:
        issues.append("Matrix has no criteria.")

    if np.isnan(matrix).any():
        nan_count = int(np.isnan(matrix).sum())
        issues.append(f"Matrix has {nan_count} missing value(s). Fill all cells before running.")

    if np.isinf(matrix).any():
        issues.append("Matrix contains infinite values. Replace them with finite numbers.")

    return len(issues) == 0, issues


def validate_weights(
    weights: np.ndarray,
    criterion_names: List[str],
) -> Tuple[bool, List[str]]:
    """
    Validate a weight vector.
    """
    issues: List[str] = []

    if (weights < 0).any():
        neg_crits = [criterion_names[i] for i, w in enumerate(weights) if w < 0]
        issues.append(f"Negative weights for: {', '.join(neg_crits)}.")

    if float(weights.sum()) <= 0:
        issues.append("Weights must sum to a positive number.")

    return len(issues) == 0, issues


def validate_directions(
    directions: List[str],
    criterion_names: List[str],
) -> Tuple[bool, List[str]]:
    """
    Validate that each direction is 'benefit' or 'cost'.
    """
    issues: List[str] = []
    valid = {"benefit", "cost"}
    for name, d in zip(criterion_names, directions):
        if d not in valid:
            issues.append(f"Criterion '{name}' has invalid direction '{d}' (must be 'benefit' or 'cost').")
    return len(issues) == 0, issues
