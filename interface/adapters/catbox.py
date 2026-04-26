from pathlib import Path
import requests
from jays_tools.architecture import Adapter
from typing import TypeAlias
from nicegui.elements.upload_files import FileUpload

# https://catbox.moe/
CATBOX_API = 'https://catbox.moe/user/api.php'
URL: TypeAlias = str


class CatboxAdapter(Adapter):

    async def from_nice_gui_file_upload(self, file: FileUpload) -> URL:
        return self.upload_raw_file(await file.read())

    def upload(self, file_or_url: str | Path) -> str:
        if isinstance(file_or_url, Path):
            return self.file_path_upload(str(file_or_url))

        return self.url_upload(file_or_url)

    def file_path_upload(self, file_path: str):
        with open(file_path, 'rb') as file:
            return self.upload_raw_file(file.read())

    def upload_raw_file(self, file: bytes) -> str:
        return self.catbox_request(file=file)

    def url_upload(self, file_url: str) -> str:
        return self.catbox_request(url=file_url)

    def catbox_request(self, file: bytes | None = None, url: URL | None = None) -> URL:
        if not any((file, url)):
            raise ValueError("Either file or url must be provided")

        if file is not None:
            data = {'reqtype': 'fileupload'}
            files = {'fileToUpload': file}
        elif url is not None:
            data = {'reqtype': 'urlupload', 'url': url}
            files = {}
        else:
            raise ValueError("Either file or url must be provided")

        response = requests.post(
            CATBOX_API, data=data, files=files, verify=False
        )

        if response.status_code == 200:
            return response.text.strip()
        else:
            raise Exception(
                f"Failed to Upload File: {response.status_code} {response.text}"
            )
