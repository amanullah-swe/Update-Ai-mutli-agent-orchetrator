from pathlib import Path
import fitz


class PDFParser:
    """
    Parser for mixed-layout PDFs.

    Extracts:
        - Text
        - Text blocks
        - Tables
        - Embedded images
        - Vector graphics/drawings
        - Page metadata/layout
    """

    def __init__(self, image_output_dir: str = "data/extracted_images"):
        self.image_output_dir = Path(image_output_dir)

    def parse(self, pdf: fitz.Document) -> dict:

        document_id = self._create_document_id(pdf)

        document = {
            "document_id": document_id,
            "metadata": pdf.metadata,
            "page_count": len(pdf),
            "pages": []
        }

        # Create directory for extracted images
        self.image_output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # ------------------------------------------------
        # Process every page
        # ------------------------------------------------

        for page_number, page in enumerate(pdf, start=1):

            page_data = self._parse_page(
                pdf=pdf,
                page=page,
                page_number=page_number,
                document_id=document_id
            )

            document["pages"].append(page_data)

        return document

    # ====================================================
    # PAGE
    # ====================================================

    def _parse_page(
        self,
        pdf: fitz.Document,
        page: fitz.Page,
        page_number: int,
        document_id: str
    ) -> dict:

        page_data = {
            "page_number": page_number,

            "dimensions": {
                "width": page.rect.width,
                "height": page.rect.height
            },

            "text": "",
            "blocks": [],
            "tables": [],
            "images": [],
            "graphics": []
        }

        # ------------------------------------------------
        # 1. TEXT + LAYOUT BLOCKS
        # ------------------------------------------------

        text_blocks = page.get_text(
            "blocks",
            sort=True
        )

        for block_index, block in enumerate(text_blocks):

            x0, y0, x1, y1, text, *rest = block

            text = text.strip()

            if not text:
                continue

            block_data = {
                "id": f"{document_id}_p{page_number}_b{block_index}",
                "type": "text",
                "text": text,
                "bbox": [
                    x0,
                    y0,
                    x1,
                    y1
                ]
            }

            page_data["blocks"].append(block_data)

            page_data["text"] += text + "\n"

        # ------------------------------------------------
        # 2. TABLES
        # ------------------------------------------------

        page_data["tables"] = self._extract_tables(
            page=page,
            page_number=page_number,
            document_id=document_id
        )

        # ------------------------------------------------
        # 3. EMBEDDED IMAGES
        # ------------------------------------------------

        page_data["images"] = self._extract_images(
            pdf=pdf,
            page=page,
            page_number=page_number,
            document_id=document_id
        )

        # ------------------------------------------------
        # 4. VECTOR GRAPHICS
        # ------------------------------------------------

        page_data["graphics"] = self._extract_graphics(
            page=page,
            page_number=page_number,
            document_id=document_id
        )

        return page_data

    # ====================================================
    # TABLE EXTRACTION
    # ====================================================

    def _extract_tables(
        self,
        page: fitz.Page,
        page_number: int,
        document_id: str
    ) -> list:

        tables = []

        try:
            table_finder = page.find_tables()

            for table_index, table in enumerate(
                table_finder.tables
            ):

                rows = table.extract()

                if not rows:
                    continue

                # Clean None values
                cleaned_rows = []

                for row in rows:

                    cleaned_row = [
                        cell.strip() if isinstance(cell, str)
                        else cell
                        for cell in row
                    ]

                    cleaned_rows.append(cleaned_row)

                tables.append({
                    "id": (
                        f"{document_id}"
                        f"_p{page_number}"
                        f"_table{table_index}"
                    ),

                    "type": "table",

                    "bbox": [
                        table.bbox[0],
                        table.bbox[1],
                        table.bbox[2],
                        table.bbox[3]
                    ],

                    "rows": cleaned_rows,

                    "row_count": len(cleaned_rows),

                    "column_count": (
                        len(cleaned_rows[0])
                        if cleaned_rows
                        else 0
                    )
                })

        except Exception as exc:

            # Don't fail the complete document because
            # table extraction failed on one page.
            tables.append({
                "type": "table_error",
                "error": str(exc)
            })

        return tables

    # ====================================================
    # IMAGE EXTRACTION
    # ====================================================

    def _extract_images(
        self,
        pdf: fitz.Document,
        page: fitz.Page,
        page_number: int,
        document_id: str
    ) -> list:

        images = []

        image_list = page.get_images(
            full=True
        )

        for image_index, image in enumerate(image_list):

            xref = image[0]

            try:
                image_data = pdf.extract_image(xref)

                extension = image_data["ext"]

                filename = (
                    f"{document_id}"
                    f"_page_{page_number}"
                    f"_image_{image_index}"
                    f".{extension}"
                )

                output_path = (
                    self.image_output_dir / filename
                )

                with open(output_path, "wb") as file:
                    file.write(image_data["image"])

                images.append({
                    "id": (
                        f"{document_id}"
                        f"_p{page_number}"
                        f"_img{image_index}"
                    ),

                    "type": "image",

                    "xref": xref,

                    "format": extension,

                    "width": image_data["width"],

                    "height": image_data["height"],

                    "path": str(output_path)
                })

            except Exception as exc:

                images.append({
                    "type": "image_error",
                    "xref": xref,
                    "error": str(exc)
                })

        return images

    # ====================================================
    # VECTOR GRAPHICS
    # ====================================================

    def _extract_graphics(
        self,
        page: fitz.Page,
        page_number: int,
        document_id: str
    ) -> list:

        graphics = []

        drawings = page.get_drawings()

        for graphic_index, drawing in enumerate(drawings):

            rect = drawing.get("rect")

            graphics.append({
                "id": (
                    f"{document_id}"
                    f"_p{page_number}"
                    f"_graphic{graphic_index}"
                ),

                "type": "graphic",

                "bbox": [
                    rect.x0,
                    rect.y0,
                    rect.x1,
                    rect.y1
                ] if rect else None,

                "items": drawing.get("items", []),

                "fill": drawing.get("fill"),

                "color": drawing.get("color"),

                "width": drawing.get("width")
            })

        return graphics

    # ====================================================
    # DOCUMENT ID
    # ====================================================

    def _create_document_id(
        self,
        pdf: fitz.Document
    ) -> str:

        metadata = pdf.metadata or {}

        title = metadata.get(
            "title",
            "document"
        )

        # Simple safe ID
        safe_title = "".join(
            char.lower()
            if char.isalnum()
            else "_"
            for char in title
        )

        return safe_title.strip("_") or "document"