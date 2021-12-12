# Local osu! server

Just imagine normal bancho, but you can have multiple profiles and funorange speed up maps ranked (coming soon)!

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
When changing your player_name in the config, it'll make a new profile in the json folder

When changing pfps through the `.data/pfp.json` you'll need to restart the server in order to see updates (will make it auto update soon)