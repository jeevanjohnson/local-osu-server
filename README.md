# Local osu! server

Just imagine normal bancho, but you can have multiple profiles and funorange speed up maps ranked!

---
# Windows Setup
1. Install python, specifically [python3.9.5](https://www.python.org/downloads/release/python-395/)!
2. You may need to uninstall python3.10 from your system, due to unstableness
3. Download [the code](https://github.com/coverosu/local-osu-server/archive/refs/heads/main.zip) and extract to a folder
4. Open up command prompt
5. Type and enter the following
```
cd "replace_this_text_with_the_folder_directory_of_the_server_you_just_installed"
pip install -r requirements.txt
```
6. You'll have to edit the config file provided, read through it to fully setup the server
7. just run `main.py` with the following command `py main.py` and you should be good to go!
---

# Linux Setup
coming soon

---
# Reminders
This project gets frequently updated, so just to update (will make an updater soon), just download the new code and replace it with the files you current have in your server. You may have to edit the config file a bit if `sample.config.py` gets some changes. 

Any unknown errors you see when setting up or just playing, please report them to me on discord `cover#0675` :)

To make/play with different profiles, when logging in be sure to put the username of the profile you want to play/make and it will automaticly make/go onto the profile.

# TODOs

(Not listed in any specifc order)

- Updated PP system
- Alternative to `glob`
- Better logging

# Maybes

- Support other modes?