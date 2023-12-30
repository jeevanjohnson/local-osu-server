# Local osu! server

Just imagine normal bancho, but you can have multiple profiles and funorange speed up maps ranked!

# Purpose
Main purpose of this server is that it can replicate the bancho like experiences with lbs and ranking, but also have its own cool little features, like osu!trainer rankings. The idea for the server is so that anyone can run it on any machine (aiming user friendly) without having the hassle of nginx, certificates, linux, etc.

Why do I even care for this server? Well when I got restricted on osu! back in 2018, I wanted to feel the bancho experience like gaining ranks and such without breaking rules while being restricted, that same idea came back to me this year (2021) and now that I have the knowledge I can finally bring that to reality.

# Windows Setup
1. Install python, specifically [python3.9.5](https://www.python.org/downloads/release/python-395/)! [64-bit download](https://www.python.org/ftp/python/3.9.5/python-3.9.5-amd64.exe), [32-bit download](https://www.python.org/ftp/python/3.9.5/python-3.9.5.exe) 

~~2. You will most likely need to uninstall python3.10 from your system, due to instability~~

3. Download [the code](https://github.com/coverosu/local-osu-server/archive/refs/heads/main.zip) and extract to a folder

4. Open the folder and double click the `main.py` file, from there the rest of the instructions are there for you to read and you should be good to go! (Note: most important information you will want to fill in is the paths, osu api key, and osu daily api key!)

5. Just a note, when doing the `-devserver` method be sure to put the domain `catboy.click` in as the domain, all this does is allow all osu! connections be redirected to your localhost.

# Linux Setup
coming soon

# Reminders
Any unknown errors you see when setting up or just playing, please report them to me on discord `cover#0675` :)

To make/play with different profiles, when logging in be sure to put the username of the profile you want to play/make and it will automaticly make/go onto the profile.

# Huge TODOS(?)

- Support other modes?
- switch to sqlite rather then use json as db
