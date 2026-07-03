from __future__ import annotations

from pathlib import Path

import fitz

from .models import PDFDocument
from .models import PDFPage
from .models import PDFWord


class PDFExtractor:

    @staticmethod
    def load(path: Path) -> PDFDocument:

        pdf = fitz.open(path)

        pages = []

        for page_number, page in enumerate(pdf, start=1):

            rect = page.rect

            words = []

            for w in page.get_text("words"):

                x0, y0, x1, y1, text, block, line, word = w

                words.append(
                    PDFWord(
                        text=text,
                        x0=x0,
                        y0=y0,
                        x1=x1,
                        y1=y1,
                        block=block,
                        line=line,
                        word=word,
                    )
                )

            pages.append(
                PDFPage(
                    number=page_number,
                    width=rect.width,
                    height=rect.height,
                    rotation=page.rotation,
                    text=page.get_text("text"),
                    words=words,
                )
            )

        pdf.close()

        return PDFDocument(
            path=path,
            page_count=len(pages),
            pages=pages,
        )
