# Local osu! server

([This is the most stable version up to date](https://github.com/coverosu/local-osu-server/tree/cfbb16b83b93b7818928b97343f7a18ecc8d5099), may not have all the features you want but when more errors and bugs get reported and fixed this will change :D)

Just imagine normal bancho, but you can have multiple profiles and funorange speed up maps ranked! (fun orange part is 85% done? just need testers O_O)

---
# Windows Setup
1. Install python, specifically [python3.9.5](https://www.python.org/downloads/release/python-395/)!
2. You may need to uninstall python3.10 from your system, due to unstableness
3. Download the code and extract to a folder
4. Open up command prompt
5. Type and enter the following
```
cd "replace_this_text_with_the_folder_directory_of_the_server_you_just_installed"
pip install -r requirements.txt
py main.py
```
6. If the result of running the `main.py` file is "server is running", you've successfully ran the server!
7. You'll have to edit the config file provided, read through it to fully setup the server
8. just re run `main.py` and when config is updated and you should be good to go!
---

# Linux Setup
coming soon

---
# Reminders
Any unknown errors you see when setting up or just playing, please report them to me on discord `cover#0675` :)

To make/play with different profiles, when logging in be sure to put the username of the profile you want to play/make and it will automaticly make/go onto the profile.

# TODOs

(Not listed in any specifc order)

- Funorange speed up map status (read above)
- Updated PP system
- Ingame menus (includes like change pfp button or smth)
- Alternative to `glob`
- Better logging

# Maybes

- Support other modes?
- Local API for other external program uses (programs that do this are gosumemory)
- Local website for viewing profile? (Would take a while because frontend knowledge is not high)