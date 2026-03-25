from datetime import datetime, timedelta, timezone
import numpy as np
import random
from cache import cached_for_five_minutes
from osuProtocol.server_packets import osuAction

ALL_STATES = [
    osuAction.Idle,
    osuAction.Afk,
    osuAction.Playing,
    osuAction.Editing,
    osuAction.Modding,
    osuAction.Multiplayer,
    osuAction.Watching,
    osuAction.Testing,
    osuAction.Submitting,
    osuAction.Paused,
    osuAction.Lobby,
    osuAction.Multiplaying,
    osuAction.OsuDirect,
]

# ----------------------------------------------------------------------
# Helper: convert any datetime to UTC
# ----------------------------------------------------------------------
def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware and converted to UTC."""
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

# ----------------------------------------------------------------------
# Helper: extract timestamps when playcount increased
# ----------------------------------------------------------------------
def extract_play_times(data: list[tuple[datetime, int]]) -> list[datetime]:
    """
    Input: data - list of (datetime, playcount) pairs, sorted by datetime.
    Output: list of datetimes where the play count increased.
    """
    play_times = []
    for i in range(1, len(data)):
        if data[i][1] > data[i-1][1]:
            play_times.append(ensure_utc(data[i][0]))
    return play_times

# ----------------------------------------------------------------------
# Helper: compute gaps between consecutive play times (in seconds)
# ----------------------------------------------------------------------
def compute_gaps(play_times: list[datetime]) -> np.ndarray:
    if len(play_times) < 2:
        return np.array([])
    gaps = []
    for i in range(1, len(play_times)):
        delta = (play_times[i] - play_times[i-1]).total_seconds()
        gaps.append(delta)
    return np.array(gaps)

# ----------------------------------------------------------------------
# K-means for 1D data (3 clusters, sorted)
# ----------------------------------------------------------------------
def kmeans_1d(data: np.ndarray, k: int = 3, max_iter: int = 20) -> np.ndarray:
    if len(data) < k:
        pct = np.percentile(data, [25, 50, 75]) if len(data) > 0 else [60, 300, 3600]
        return np.sort(pct)

    centers = np.random.choice(data, k, replace=False)

    for _ in range(max_iter):
        clusters = [[] for _ in range(k)]
        for x in data:
            idx = np.argmin([abs(x - c) for c in centers])
            clusters[idx].append(x)

        new_centers = []
        for i, cluster in enumerate(clusters):
            if cluster:
                new_centers.append(np.mean(cluster))
            else:
                new_centers.append(centers[i] if len(data) else 0)
        centers = np.array(new_centers)

    return np.sort(centers)

# ----------------------------------------------------------------------
# Convert a gap to probabilities using distance to cluster centers
# ----------------------------------------------------------------------
def gap_to_probabilities(gap: float, centers: np.ndarray) -> dict[osuAction, float]:
    distances = np.abs(centers - gap)
    inv = 1.0 / (distances + 1e-6)
    probs = inv / np.sum(inv)

    return {
        osuAction.Playing: probs[0],
        osuAction.Idle: probs[1],
        osuAction.Afk: probs[2]
    }

# ----------------------------------------------------------------------
# Apply recency bias based on average gap (extreme gaps)
# ----------------------------------------------------------------------
def apply_recency_bias(probs: dict[osuAction, float], current_gap: float, avg_gap: float) -> dict[osuAction, float]:
    if avg_gap > 0:
        if current_gap > 2 * avg_gap:
            probs[osuAction.Afk] *= 1.5
        elif current_gap < 0.5 * avg_gap:
            probs[osuAction.Playing] *= 1.5

    total = sum(probs.values())
    for k in probs:
        probs[k] /= total
    return probs

# ----------------------------------------------------------------------
# Apply score recency boost (explicit boost based on last score time)
# ----------------------------------------------------------------------
def apply_score_recency_boost(probs: dict[osuAction, float], last_score_gap: float | None, boost_threshold: float = 300) -> dict[osuAction, float]:
    """
    Boost PLAYING probability if a score was submitted recently.
    boost_threshold: time in seconds (default 5 minutes) – if last_score_gap <= this, boost is applied.
    The boost decays linearly from 2× at gap=0 to 1× at gap=threshold.
    """
    if last_score_gap is not None and last_score_gap <= boost_threshold:
        # Boost factor: 2.0 at gap=0, 1.0 at gap=threshold
        boost_factor = 2.0 - (last_score_gap / boost_threshold)
        probs[osuAction.Playing] *= boost_factor
        # Renormalize
        total = sum(probs.values())
        for k in probs:
            probs[k] /= total
    return probs

# ----------------------------------------------------------------------
# Main function: estimate player state at a given time
# ----------------------------------------------------------------------
def estimate_player_state(
        data: list[tuple[datetime, int]],
        score_times: list[datetime] | None = None,
        now: datetime | None = None,
        random_state_on_low_confidence: bool = True,
        _score_recency_threshold: timedelta = timedelta(minutes=5)  # 5 minutes
) -> tuple[dict[osuAction, float], osuAction]:
    """
    Input:
        data - list of (datetime, playcount) pairs, sorted by datetime.
        score_times - optional list of datetimes when the player set a score.
        now - optional datetime; if None, uses current UTC time.
        random_state_on_low_confidence - if True and max probability < 0.5, pick random from ALL_STATES.
        score_recency_threshold - timedelta; if last score is within this, boost PLAYING probability.
    Output:
        (probabilities_dict, most_likely_state)
    """
    score_recency_threshold = _score_recency_threshold.total_seconds()

    # Ensure now is UTC-aware
    if now is None:
        now = datetime.now(timezone.utc)
    else:
        now = ensure_utc(now)

    # Step 1: Get activity timestamps (playcount increases + optional score events)
    play_times = extract_play_times(data)

    # Convert score_times to UTC if provided
    last_score_gap = None
    if score_times:
        score_times_utc = [ensure_utc(dt) for dt in score_times]
        # Determine the most recent score time
        if score_times_utc:
            last_score_time = max(score_times_utc)
            last_score_gap = (now - last_score_time).total_seconds()
        # Merge all activities
        all_activities = sorted(set(play_times + score_times_utc))
    else:
        all_activities = play_times

    # Not enough data to make a confident estimate: fallback to AFK
    if len(all_activities) < 3:
        return {osuAction.Afk: 1.0, osuAction.Idle: 0.0, osuAction.Playing: 0.0}, osuAction.Afk

    # Step 2: Compute gaps between consecutive activities
    gaps = compute_gaps(all_activities)

    # Step 3: Learn personal thresholds via K-means
    centers = kmeans_1d(gaps, k=3)

    # Step 4: Current gap since last activity
    current_gap = (now - all_activities[-1]).total_seconds()

    # Step 5: Convert to probabilities
    probs = gap_to_probabilities(current_gap, centers)

    # Step 6: Apply general recency bias (based on average gap)
    avg_gap = float(np.mean(gaps)) if len(gaps) > 0 else 0.0
    probs = apply_recency_bias(probs, current_gap, avg_gap)

    # Step 7: Apply score recency boost (explicit boost for recent scores)
    probs = apply_score_recency_boost(probs, last_score_gap, score_recency_threshold)

    # Step 8: Pick the most likely state (deterministic)
    state = max(probs, key=lambda k: probs[k])

    # Step 9: Optional low‑confidence randomness
    print(f"Estimated probabilities: {probs}, most likely state: {state}, current_gap: {current_gap:.1f}s, avg_gap: {avg_gap:.1f}s, last_score_gap: {last_score_gap:.1f}s" if last_score_gap is not None else f"Estimated probabilities: {probs}, most likely state: {state}, current_gap: {current_gap:.1f}s, avg_gap: {avg_gap:.1f}s")
    if random_state_on_low_confidence and max(probs.values()) < 0.3:
        state = random.choice(ALL_STATES)

    return probs, state