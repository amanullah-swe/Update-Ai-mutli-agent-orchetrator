from loaders.pdf_loader import PDFLoader
from parsers.pdf_parser import PDFParser
from cleaners.pdf_cleaner import DocumentCleaner


class IngestionPipeline:

    def __init__(self, pdf_path: str):

        self.loader = PDFLoader(pdf_path)
        self.parser = PDFParser()
        self.cleaner = DocumentCleaner()

    def run(self):

        # 1. Load
        pdf = self.loader.load()

        try:
            # 2. Parse
            document = self.parser.parse(pdf)

            # 3. Clean
            document = self.cleaner.clean(document)

            return document

        finally:
            pdf.close()



path = "/home/amanullah/claude code/Update Ai mutli agent orchetrator/document_store/PyTorch_Complete_Course_CampusX_OCR.pdf"
pipeline = IngestionPipeline(path)

document = pipeline.run()

images_number = sum( len(page['images']) for page in document["pages"])

print(f"Document ID: {document['document_id']}")
print(f"Number of pages: {len(document['pages'])}")
print(f"Number of images: {images_number}")