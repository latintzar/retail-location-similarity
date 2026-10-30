"""Independently expressed Leo historical score; see README for provenance."""
import math
from typing import Optional, Tuple
import numpy as np

def compute_diem_parameters(n_dimensions: int, min_val: float = 0.0, max_val: float = 1.0) -> Tuple[float, float]:
    """Historic Leo distance calibration, independently expressed from its equations.

    The project cites Tessari et al. (2024), https://arxiv.org/abs/2407.08623.
    This approximation and its logistic display score are Leo-specific and are
    not the authors' reference implementation of the published DIEM metric.
    """
    width = max_val - min_val
    expected_square = n_dimensions * width ** 2 / 6
    if expected_square <= 0:
        return 0.0, 0.0
    square_variance = (n_dimensions / 180 + n_dimensions * (n_dimensions - 1) / 36) * width ** 4
    return math.sqrt(expected_square), math.sqrt(square_variance / (4 * expected_square))

def compute_diem(
    reference_vector: np.ndarray,
    comparison_vectors: np.ndarray,
    min_vals: Optional[np.ndarray] = None,
    max_vals: Optional[np.ndarray] = None
) -> np.ndarray:
    """Reproduce the historic Leo calibrated distance as a 0–100 score."""
    rows = np.asarray(comparison_vectors)
    if rows.ndim == 1:
        rows = rows.reshape(1, -1)
    low = np.nanmin(rows, axis=0) if min_vals is None else min_vals
    high = np.nanmax(rows, axis=0) if max_vals is None else max_vals
    width = high - low
    width[width == 0] = 1.0
    target = np.nan_to_num((reference_vector - low) / width, nan=0.5)
    scaled = np.nan_to_num((rows - low) / width, nan=0.5)
    distance = np.sqrt(np.sum((scaled - target) ** 2, axis=1))
    center, spread = compute_diem_parameters(len(reference_vector), 0.0, 1.0)
    standard = (distance - center) / spread if spread > 0 else distance - center
    return 100 * (1 - 1 / (1 + np.exp(-standard * 1.5)))
