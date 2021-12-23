import re

screenshot_web_path = re.compile(r'\/ss\/(?P<link>.*)')
bmap_web_path = re.compile(r'\/(beatmaps|beatmapsets)\/(?P<path>.*)')
download_web_path = re.compile(r'/d/(?P<setid>[0-9]*)')

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

avatar_handler = re.compile(r'\/a\/(?P<userid>[0-9]*)')
api_v1_handler = re.compile(r'\/api\/v1\/(?P<path>.*)')
website_handler = re.compile(r'\/(?P<path>.*)')
cho_handler = re.compile(r'\/((c[4-6e])|(c))\/(?P<handler>.*)')
osu_web_handler = re.compile(r'\/osu\/(?P<handler>.*)')