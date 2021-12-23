CHO_TOKEN = str
BODY = bytearray

WELCOME_MSG = '\n'.join([
    'Welcome {name}!',
    '',
    'Below you can find some useful buttons to enhance your gaming experience B)'
])

CHANNEL = tuple[str, str]
CHANNELS: list[CHANNEL] = [
    # name, desc
    ('#osu', 'x'),
    ('#recent', 'shows recently submitted scores!'),
    ('#tops', 'shows top plays, as well as updates them!')
]

BUTTON = tuple[str, str]
BUTTONS: list[BUTTON] = [
    # url, name
    ('http://127.0.0.1:5000/api/v1/client/tops?limit=100&m={mode}', 'view tops'),
    ('http://127.0.0.1:5000/api/v1/client/recent?limit=10&m={mode}', 'view recent'),
    ('http://127.0.0.1:5000/api/v1/client/recalc?m={mode}', 'recalc plays'),
    ('http://127.0.0.1:5000/api/v1/client/profile?m={mode}', 'view profile'),
    ('http://127.0.0.1:5000/api/v1/client/change_avatar', 'change avatar'),
    ('http://127.0.0.1:5000/api/v1/client/wipe?m={mode}', 'wipe profile')
]