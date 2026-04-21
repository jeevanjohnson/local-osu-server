"""Calculate accuracy from hit counts."""


def calculate_accuracy(count_300: int, count_100: int, count_50: int, count_miss: int) -> float:
    """
    Calculate accuracy percentage from hit counts.
    
    Args:
        count_300: Number of 300 hits
        count_100: Number of 100 hits
        count_50: Number of 50 hits
        count_miss: Number of misses
        
    Returns:
        Accuracy as float (0.0-1.0)
    """
    total_hits = count_300 + count_100 + count_50 + count_miss
    if total_hits == 0:
        return 0.0
    return (count_300 * 300 + count_100 * 100 + count_50 * 50) / (total_hits * 300)
