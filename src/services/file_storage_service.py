import os
import logging

logger = logging.getLogger(__name__)

class FileStorageService:
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def list_files(self):
        if not os.path.exists(self.data_dir):
            return []
        files = [f for f in os.listdir(self.data_dir) if os.path.isfile(os.path.join(self.data_dir, f))]
        files.sort()
        return files

    def get_file_path(self, filename):
        # Security check to prevent directory traversal
        if '..' in filename or filename.startswith('/'):
            raise ValueError("Invalid filename")
        return os.path.join(self.data_dir, filename)

    def read_file(self, filename):
        path = self.get_file_path(filename)
        with open(path, 'rb') as f:
            return f.read()

    def save_file(self, filename, data):
        path = self.get_file_path(filename)
        with open(path, 'wb') as f:
            f.write(data)
        return path
