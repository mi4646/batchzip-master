from datetime import datetime


class FileUploadResponse:
    def __init__(self, filename: str, saved_path: str, size: int, md5: str):
        self.filename = filename
        self.saved_path = saved_path
        self.size = size
        self.md5 = md5
        self.upload_time = datetime.now().isoformat()
