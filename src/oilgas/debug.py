from __future__ import annotations

from pathlib import Path

import fitz

from oilgas.extractors.pdf import PDFExtractor


def draw_layout(pdf_path: Path, output: Path):

    document = PDFExtractor.load(pdf_path)

    pdf = fitz.open(pdf_path)

    for page_number, page in enumerate(pdf):
        p = document.pages[page_number]

        for word in p.words:
            rect = fitz.Rect(
                word.x0,
                word.y0,
                word.x1,
                word.y1,
            )

            page.draw_rect(
                rect,
                color=(1, 0, 0),
                width=0.5,
            )

        page.insert_text(
            (20, 20),
            f"Page {page_number + 1}",
            fontsize=8,
            color=(0, 0, 1),
        )

    pdf.save(output)
