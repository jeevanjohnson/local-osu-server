"""
Just a note, you will have to rename this file to
config.py in order for it to work!
"""

from typing import Iterable
from typing import Optional

# Just a note
# When doing the -devserver method
# be sure to put the domain 'coverbancho.tk' in as the domain
# it will redirect back to your local host and you can be
# good. Only change if testing and I probably won't provide
# little support on setting that up

# To make/play with different profiles,
# when logging in be sure to put the username
# of the profile you want to play/make and
# it will automaticly make/go onto the profile.
paths: dict[str, Optional[str]] = {
    'osu! path': r'', # if provided no need to fill in below
                      # unless songs, replay, and ss folder are somewhere else

    'songs': None, # osu! songs folder
    'replay': None, # osu! replay folder
    'screenshots': None # osu! screenshot folder
}

"""Ingame Config"""
# please keep this as false as it is unusable atm
# TODO: use api v2 to get lb scores rather then v1
# as if i remember it returns a pp value for each
# score making it so the server can be faster
pp_leaderboard: bool = False

# change to `False` if you don't want to be highlighted
ping_user_when_recent_score: bool = True

# ingame menu icon you see under the osu! logo
menu_icon: dict[str, Optional[str]] = {
    'image_link': '',
    'click_link': '',
}

# you can run commands through the direct search bar
# this prefix can change to whatever you want it to be
# just know that when you change it that is the character
# you need to use before typing out commands and such
command_prefix: str = '!'

# shows pp amount instead of actual score for
# personal best on leaderboards
show_pp_for_personal_best: bool = True

# amount of scores to show on leaderboard max is 100
amount_of_scores_on_lb: int = 100

"""Server Config"""
# will automatically update the sever
# whenever there are new updates added
# updater is not 100% tested, but should work safely
auto_update: bool = False

# will not include funorange maps in rankings or plays 
# and won't submit funorange map scores
disable_funorange_maps: bool = False

# needed for loading leaderboards
# you can find your's here https://old.ppy.sh/p/api/
# if `None` then leaderboards won't load nor score submission
osu_api_key: Optional[str] = ''

# if u want ur screenshots to be uploaded
# get your client id here https://api.imgur.com/
# if `None` it won't upload screenshots
imgur_client_id: Optional[str] = ''

# that is if you want ur bancho rank to show up
# you can find your's here https://github.com/Adrriii/osudaily-api/wiki
# if `None` it will show you as rank 1
osu_daily_api_key: Optional[str] = ''

# sign up for one right here https://beatconnect.io/accounts/privatesignup/
# if `None` then direct won't work/will be disabled
beatconnect_api_key: Optional[str] = ''

# list of urls, example: ['https://dsada.png', https://dsad11a.png]
# if `None` then it will just show no background
# unless you have the skin background inabled
seasonal_bgs: Optional[Iterable[str]] = []
