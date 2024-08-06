# data_source.py
from abc import ABC, abstractmethod
from docx import Document

class DataSource(ABC):
    @abstractmethod
    def get_data(self) -> str:
        pass

class FileDataSource(DataSource):
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_data(self) -> str:
        if self.file_path.endswith('.docx'):
            return self.read_docx(self.file_path)
        else:
            with open(self.file_path, 'r') as file:
                return file.read()

    def read_docx(self, file_path: str) -> str:
        document = Document(file_path)
        full_text = []
        for para in document.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
