PATH_TO_FILE = r''
PATH_TO_DOT_DATA_FOLDER = r''

from typing import Any
JsonFile: Any = 0

from pathlib import Path

p = [*Path.cwd().parts, 'objects', 'jsonfile.py']
try: p.remove('scripts')
except: pass
jsonfile = Path('\\'.join(p))
exec(jsonfile.read_text())

file = JsonFile(PATH_TO_FILE)

data_folder = Path(PATH_TO_DOT_DATA_FOLDER)
if not data_folder.exists():
    data_folder.mkdir(exist_ok=True)

pfps = JsonFile(data_folder / 'pfps.json')
beatmaps = JsonFile(data_folder / 'beatmaps.json')
profiles = JsonFile(data_folder / 'profiles.json')

beatmaps.update(file['beatmaps'])
profiles.update(file['profiles'])
pfps.update({k: None for k in file['profiles'].keys()})

beatmaps.update_file()
profiles.update_file()
pfps.update_file()

print('done!')