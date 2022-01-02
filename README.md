# Local osu! server

Just imagine normal bancho, but you can have multiple profiles and funorange speed up maps ranked!

# Purpose
Main purpose of this server is that it can replicate the bancho like experiences with lbs and ranking, but also have its own cool little features, like osu!trainer rankings. The idea for the server is so that anyone can run it on any machine (aiming user friendly) without having the hassle of nginx, certificates, linux, etc.

Why do I even care for this server? Well when I got restricted on osu! back in 2018, I wanted to feel the bancho experience like gaining ranks and such without breaking rules while being restricted, that same idea came back to me this year (2021) and now that I have the knowledge I can finally bring that to reality.

# Windows Setup
1. Install python, specifically [python3.9.5](https://www.python.org/downloads/release/python-395/)!
2. You may need to uninstall python3.10 from your system, due to unstableness
3. Download [the code](https://github.com/coverosu/local-osu-server/archive/refs/heads/main.zip) and extract to a folder
4. Open up command prompt
5. Type and enter the following
```
cd "replace_this_text_with_the_folder_directory_of_the_server_you_just_installed"
python -m pip install -r requirements.txt
```
6. You'll have to edit the config file provided, read through it to fully setup the server (most important information you will want to fill in is `osu_api_key`, `osu_daily_api_key`, and your paths!)
7. just run `main.py` with the following command `./main.py` and you should be good to go!


# Linux Setup
coming soon

# Reminders
You may have to edit your `config.py` file a bit if `sample.config.py` gets some changes with incoming updates. 

Any unknown errors you see when setting up or just playing, please report them to me on discord `cover#0675` :)

To make/play with different profiles, when logging in be sure to put the username of the profile you want to play/make and it will automaticly make/go onto the profile.

# Huge TODOS(?)

- Support other modes?
- switch to sqlite rather then use json as db