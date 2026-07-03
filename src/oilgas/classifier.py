from enum import Enum

from oilgas.extractors.models import PDFDocument


class DocumentType(str, Enum):
    UNKNOWN = "UNKNOWN"

    HIGHMARK_REVENUE = "HIGHMARK_REVENUE"
    HIGHMARK_JIB = "HIGHMARK_JIB"
    HIGHMARK_STATEMENT = "HIGHMARK_STATEMENT"

    XTO_REVENUE = "XTO_REVENUE"


RULES = {
    DocumentType.HIGHMARK_REVENUE: [
        "HIGHMARK ENERGY OPERATING LLC",
        "REVENUE STATEMENT",
        "CHECK NUMBER",
        "CHECK DATE",
    ],

    DocumentType.HIGHMARK_JIB: [
        "HIGHMARK ENERGY OPERATING LLC",
        "JOINT INTEREST",
    ],

    DocumentType.HIGHMARK_STATEMENT: [
        "STATEMENT OF ACCOUNT",
    ],

    DocumentType.XTO_REVENUE: [
        "XTO ENERGY",
        "REVENUE",
    ],
}


class DocumentClassifier:

    @staticmethod
    def classify(document: PDFDocument) -> DocumentType:

        text = document.pages[0].text.upper()

        for doc_type, required in RULES.items():
            if all(token in text for token in required):
                return doc_type

        return DocumentType.UNKNOWN
