# very light osu! file parser to get exactly what I need
import math
from pathlib import Path
from enum import IntEnum
from typing import TypedDict

class HitObjectType(IntEnum):
  CIRCLE = 1
  SLIDER = 1 << 1
  NEW_COMBO = 1 << 2
  SPINNER = 1 << 3
  COMBO_OFFSET = (1 << 4) | (1 << 5) | (1 << 6)
  HOLD = 1 << 7

def get_raw_file(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()

def get_section(lines: list[str], section_name: str) -> list[str]:
    start = lines.index(f"[{section_name}]") + 1
    
    try:
        end = lines.index("", start)
    except ValueError:
        end = len(lines)

    return lines[start:end]

class SliderDifficulty(TypedDict):
    slider_multiplier: float
    slider_tick_rate: float

def get_slider_difficulty(path: Path) -> SliderDifficulty:
    raw = get_raw_file(path)
    difficulty = get_section(raw, "Difficulty")
    slider_multiplier = 1.0
    slider_tick_rate = 1.0

    for line in difficulty:
        if line.startswith("SliderMultiplier:"):
            slider_multiplier = float(line.split("SliderMultiplier:")[1].strip())
        elif line.startswith("SliderTickRate:"):
            slider_tick_rate = float(line.split("SliderTickRate:")[1].strip())
    
    return SliderDifficulty(
        slider_multiplier=slider_multiplier, 
        slider_tick_rate=slider_tick_rate
    )

class TimingPoint(TypedDict):
    offset: float
    beat_length: float

def get_timing_points(path: Path) -> list[TimingPoint]:
    # Parse timing points
    raw = get_raw_file(path)

    timing_points = []
    timings_section = get_section(raw, "TimingPoints")
    for line in timings_section:
        parts = line.split(",")

        offset = float(parts[0])
        beat_length = float(parts[1])
        
        timing_points.append(
            TimingPoint(
                offset=offset, 
                beat_length=beat_length
            )
        )
    
    return timing_points

def get_max_combo(path: Path) -> int:
    raw = get_raw_file(path)
    
    # Parse slider multiplier from difficulty section
    slider_difficulty = get_slider_difficulty(path)
    slider_multiplier = slider_difficulty["slider_multiplier"]
    slider_tick_rate = slider_difficulty["slider_tick_rate"]

    # Parse timing points
    timing_points = get_timing_points(path)

    max_combo = 0

    section = get_section(raw, "HitObjects")
    for hit_object in section:
        parts = hit_object.split(",")
        
        object_type = int(parts[3])

        if not object_type & HitObjectType.SLIDER:
            max_combo += 1
            continue

        # Slider: get timing info
        start_time = int(parts[2])
        repeat_count = int(parts[6])
        pixel_length = float(parts[7])

        # Find applicable timing point
        beat_length = timing_points[0]["beat_length"]
        for tp in timing_points:
            if tp["offset"] <= start_time:
                beat_length = tp["beat_length"]

        # Simple slider tick calculation
        if beat_length > 0:
            slider_velocity_multiplier = 1.0
        else:
            slider_velocity_multiplier = (-100.0 / beat_length)
        
        px_per_beat = slider_multiplier * 100.0 * slider_velocity_multiplier
        num_beats = (pixel_length * repeat_count) / px_per_beat
        ticks_per_repeat = int((num_beats - 0.1) / repeat_count * slider_tick_rate)
        total_ticks = ticks_per_repeat * repeat_count + 1
        
        max_combo += max(0, total_ticks)

    return max_combo

def get_artist(path: Path) -> str:
    raw = get_raw_file(path)
    section = get_section(raw, "Metadata")

    for line in section:
        if line.startswith("Artist:"):
            return line.split(":", 1)[1].strip()
    
    raise ValueError("Artist not found")

def get_title(path: Path) -> str:
    raw = get_raw_file(path)
    section = get_section(raw, "Metadata")

    for line in section:
        if line.startswith("Title:"):
            return line.split(":", 1)[1].strip()
    
    raise ValueError("Title not found")

def get_version(path: Path) -> str:
    raw = get_raw_file(path)
    section = get_section(raw, "Metadata")

    for line in section:
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip()
    
    raise ValueError("Version not found")

def get_beatmap_id(path: Path) -> int:
    raw = get_raw_file(path)
    section = get_section(raw, "Metadata")

    for line in section:
        if line.startswith("BeatmapID:"):
            return int(line.split(":", 1)[1].strip())
    
    return 0

def get_beatmap_set_id(path: Path) -> int:
    raw = get_raw_file(path)
    section = get_section(raw, "Metadata")

    for line in section:
        if line.startswith("BeatmapSetID:"):
            return int(line.split(":", 1)[1].strip())
    
    return 0

class DifficultyAttributes(TypedDict):
    ar: float
    cs: float
    hp: float
    od: float

def get_difficulty_attributes(path: Path) -> DifficultyAttributes:
    raw = get_raw_file(path)
    section = get_section(raw, "Difficulty")

    ar = 0.0
    cs = 0.0
    hp = 0.0
    od = 0.0

    for line in section:
        if line.startswith("CircleSize:"):
            cs = float(line.split("CircleSize:")[1].strip())
        elif line.startswith("ApproachRate:"):
            ar = float(line.split("ApproachRate:")[1].strip())
        elif line.startswith("OverallDifficulty:"):
            od = float(line.split("OverallDifficulty:")[1].strip())
        elif line.startswith("HPDrainRate:"):
            hp = float(line.split("HPDrainRate:")[1].strip())
    
    return DifficultyAttributes(
        ar=ar,
        cs=cs,
        hp=hp,
        od=od
    )

def get_object_count(path: Path) -> int:
    raw = get_raw_file(path)
    section = get_section(raw, "HitObjects")

    return len(section)

class BreakTime(TypedDict):
    start_time: float
    end_time: float

def get_break_times(path: Path) -> list[BreakTime]:
    raw = get_raw_file(path)
    section = get_section(raw, "Events")

    break_times = []
    for line in section:
        parts = line.split(",")
        if parts[0].strip() != "2":
            continue

        start_time = float(parts[1])
        end_time = float(parts[2])

        break_times.append(
            BreakTime(
                start_time=start_time, 
                end_time=end_time
            )
        )
    
    return break_times

# self.drain_time = math.floor((last_obj.start_time - first_obj.start_time - self.break_time) / 1000)
def get_drain_time_seconds(path: Path) -> int:
    raw = get_raw_file(path)
    section = get_section(raw, "HitObjects")

    if not section:
        return 0

    break_times = get_break_times(path)
    total_break_time = 0

    for break_time in break_times:
        total_break_time += (break_time["end_time"] - break_time["start_time"])

    first_obj_time = int(section[0].split(",")[2])
    last_obj_time = int(section[-1].split(",")[2])

    return math.floor((last_obj_time - first_obj_time - total_break_time) / 1000)