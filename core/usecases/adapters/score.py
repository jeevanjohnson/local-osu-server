"""
Empirical score estimation using multidimensional RBF interpolation.

Instead of trying to reverse-engineer osu!'s exact scoring formula,
this uses actual Bancho API scores to learn the relationship between
player performance (accuracy, combo, mod_multiplier) and final score.

Supports both Score V1 (legacy) and Score V2 (ScoreV2).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import numpy as np
from scipy.interpolate import RBFInterpolator


class ScoringVersion(Enum):
    """Scoring system version."""
    V1 = "v1"      # Legacy osu! scoring
    V2 = "v2"      # ScoreV2 system


@dataclass
class ScoreDataPoint:
    """Typed training data point for score estimation."""
    count_300: int
    count_100: int
    count_50: int
    count_miss: int
    combo: int       # max combo achieved
    score: int       # actual bancho score (with mods applied)
    mod_multiplier: float  # multiplier used for this score


class ScoreEstimator:
    """
    Estimates scores using empirical Bancho data via multidimensional RBF interpolation.
    
    Learns the relationship: (accuracy, combo, mod_multiplier) → score
    
    Supports both Score V1 and Score V2 estimations.
    """
    
    def __init__(self, version: ScoringVersion = ScoringVersion.V1):
        """
        Initialize score estimator.
        
        Args:
            version: Scoring version (V1 or V2)
        """
        self.version = version
        self.rbf_interpolator: Optional[RBFInterpolator] = None
        self.known_points: list[tuple[int, int, int, int, int, float, int]] = []  # (count_300, count_100, count_50, count_miss, combo, mod_mult, score)
    
    def train(self, training_data: list[ScoreDataPoint]) -> None:
        """
        Train the estimator using actual Bancho scores with multidimensional RBF.
        
        Creates a 6D interpolation surface: (count_300, count_100, count_50, count_miss, combo, mod_multiplier) → score
        
        Args:
            training_data: List of ScoreDataPoint objects from Bancho leaderboard
        """
        if not training_data or len(training_data) < 4:  # Need at least 4 points
            return
        
        # Build 6D feature space: [count_300, count_100, count_50, count_miss, combo, mod_multiplier]
        points = np.array([
            [float(p.count_300), float(p.count_100), float(p.count_50), float(p.count_miss), float(p.combo), p.mod_multiplier]
            for p in training_data
        ])
        
        # Target values: scores transformed to log space
        values = np.array([float(p.score) for p in training_data])
        log_values = np.log(np.maximum(values, 1.0))  # Avoid log(0), minimum 1
        
        # Log training bounds
        print(f"[V1 TRAIN] Training with {len(training_data)} V1 scores")
        print(f"[V1 TRAIN] Mod multiplier bounds: {points[:, 5].min():.4f} - {points[:, 5].max():.4f}")
        print(f"[V1 TRAIN] Score range: {values.min():.0f} - {values.max():.0f}")
        
        self.rbf_interpolator = RBFInterpolator(
            points, 
            log_values,  # Train on log-transformed scores
            kernel='multiquadric',
            epsilon=1.0,  # Shape parameter for multiquadric kernel
            smoothing=1e-3  # Regularize to prevent singular matrix
        )
        
        # Store raw data for reference
        self.known_points = [
            (p.count_300, p.count_100, p.count_50, p.count_miss, p.combo, p.mod_multiplier, p.score) 
            for p in training_data
        ]
    
    def estimate_v1(self, count_300: int, count_100: int, count_50: int, count_miss: int, combo: int, mod_multiplier: float) -> int:
        """
        Estimate Score V1 (legacy) using multidimensional RBF interpolation.
        
        Queries the learned 6D surface: (count_300, count_100, count_50, count_miss, combo, mod_multiplier) → score
        
        If query falls outside training bounds, clamps to nearest boundary (prevents bad extrapolation).
        
        Args:
            count_300: Number of 300 hits
            count_100: Number of 100 hits
            count_50: Number of 50 hits
            count_miss: Number of misses
            combo: Max combo achieved
            mod_multiplier: Mod difficulty multiplier used for this score
            
        Returns:
            Estimated Score V1 based on Bancho data and mod context
        """
        if not self.rbf_interpolator:
            return 0
        
        query = np.array([float(count_300), float(count_100), float(count_50), float(count_miss), float(combo), mod_multiplier])
        
        # Query 6D RBF surface (outputs log-space score)
        log_score = self.rbf_interpolator([query])[0]
        # Transform back to linear space (guarantees positive)
        estimated_score = np.exp(log_score)
        result = max(1, int(estimated_score))
        
        return result

    def estimate_v2(
        self,
        count_300: int,
        count_100: int,
        count_50: int,
        count_miss: int,
        combo: int,
        beatmap_max_combo: int,
        mod_multiplier: float
    ) -> int:
        """
        Calculate Score V2 (ScoreV2/Lazer) using the official formula.
        
        Args:
            count_300: Number of 300 hits
            count_100: Number of 100 hits
            count_50: Number of 50 hits
            count_miss: Number of misses
            combo: Combo achieved in play
            beatmap_max_combo: Maximum possible combo on beatmap
            mod_multiplier: Mod difficulty multiplier
            
        Returns:
            Score V2 based on official Lazer calculation
        """
        total_hits = count_300 + count_100 + count_50 + count_miss
        
        if total_hits == 0:
            return 0
        
        # Accuracy calculation (standard osu! weighting)
        accuracy = (count_300 + count_100 / 3 + count_50 / 5) / total_hits
        
        # Combo progress: achieved combo / max possible combo
        combo_progress = combo / beatmap_max_combo if beatmap_max_combo > 0 else 0
        
        # Accuracy progress: always 1.0 for osu!standard
        accuracy_progress = 1.0
        
        # Official lazer scoring formula (two 500k terms)
        hit_score = (
            500_000 * accuracy * combo_progress
            + 500_000 * (accuracy ** 5) * accuracy_progress
        )
        
        # No bonus points (spinner overspins not implemented)
        bonus_points = 0.0
        base_score = hit_score + bonus_points
        
        # Apply 0.96× "Classic" multiplier (always present for imported scores)
        # Then apply mod multiplier
        final_score = base_score * 0.96 * mod_multiplier
        
        return round(final_score)
    
    def estimate(
        self,
        combo: int,
        mod_multiplier: float,
        count_300: int,
        count_100: int,
        count_50: int,
        count_miss: int,
        beatmap_max_combo: int | None = None
    ) -> int:
        """
        Estimate score using the configured scoring version.
        
        For Score V1 (legacy):
            Args: count_300, count_100, count_50, count_miss, combo, mod_multiplier
            
        For Score V2 (ScoreV2):
            Args: count_300, count_100, count_50, count_miss, combo, beatmap_max_combo, mod_multiplier
        
        Returns:
            Estimated score based on configured scoring version
        """
        if self.version == ScoringVersion.V1:
            return self.estimate_v1(
                count_300=count_300,
                count_100=count_100,
                count_50=count_50,
                count_miss=count_miss,
                combo=combo,
                mod_multiplier=mod_multiplier
            )
        elif self.version == ScoringVersion.V2:
            assert beatmap_max_combo is not None, "beatmap_max_combo is required for Score V2 estimation"
            return self.estimate_v2(
                count_300=count_300,
                count_100=count_100,
                count_50=count_50,
                count_miss=count_miss,
                combo=combo,
                beatmap_max_combo=beatmap_max_combo,
                mod_multiplier=mod_multiplier
            )
        else:
            return 0
    
    def has_training_data(self) -> bool:
        """Check if estimator has been trained with data."""
        return self.rbf_interpolator is not None and len(self.known_points) > 0
