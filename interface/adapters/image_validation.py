
from jays_tools.architecture import Adapter
from nicegui.elements.upload_files import FileUpload
import requests


class ImageValidationAdapter(Adapter):

    def valid_image_from_nice_gui_upload(self, file: FileUpload) -> bool:
        if not file.content_type.startswith("image/"):
            return False

        suffix = file.content_type.removeprefix("image/")

        if suffix not in ["png", "jpeg", "jpg", "gif"]:
            return False

        return True

    def valid_image_from_url(self, url: str) -> bool:
        try:
            response = requests.head(
                url,
                timeout=5,
                allow_redirects=True,
                verify=False
            )
            content_type = response.headers.get("content-type", "")
            return content_type.startswith("image/")
        except Exception:
            return False
