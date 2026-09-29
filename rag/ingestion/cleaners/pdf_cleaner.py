import re


class DocumentCleaner:

    def clean(self, document: dict) -> dict:

        for page in document["pages"]:

            # Clean page-level text
            page["text"] = self._clean_text(page["text"])

            # Clean individual blocks
            for block in page["blocks"]:

                if block["type"] == "text":
                    block["text"] = self._clean_text(
                        block["text"]
                    )

        return document

    def _clean_text(self, text: str) -> str:

        # Normalize whitespace
        text = re.sub(r"[ \t]+", " ", text)

        # Remove excessive blank lines
        text = re.sub(r"\n\s*\n+", "\n\n", text)

        # Remove spaces around newlines
        text = re.sub(r" *\n *", "\n", text)

        return text.strip()