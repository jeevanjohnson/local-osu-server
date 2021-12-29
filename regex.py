try:
    import re2 as re # type: ignore
except ImportError:
    import re

filename_parser = re.compile(
    r"(?P<artist>.*) - (?P<song_name>.*) ((?P<mapper>.*) \[)(?P<diff_name>.*)\]\.osu"
)
modified_regexes = (
    re.compile(r"(?P<rate>[0-9]{1,2}\.[0-9]{1,2}x) \((?P<bpm>[0-9]*bpm)\)"),
    re.compile(r"(?P<rate>[0-9]{1,2}x) \((?P<bpm>[0-9]*bpm)\)")
)
attribute_edits = (
    re.compile(r'(.*) ((HP)|(CS)|(AR)|(OD))([0-9]{1,2})'),
    re.compile(r'(.*) ((HP)|(CS)|(AR)|(OD))([0-9]{1,2}\.[0-9]{1,2})')
)