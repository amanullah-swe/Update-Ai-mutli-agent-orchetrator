from pathlib import Path
import fitz


class PDFLoader:
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def load(self) -> fitz.Document:
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"PDF not found: {self.file_path}"
            )

        if self.file_path.suffix.lower() != ".pdf":
            raise ValueError("Expected a PDF file.")

        return fitz.open(self.file_path)