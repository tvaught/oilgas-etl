from __future__ import annotations

import re
from datetime import date

from oilgas.extractors.models import PDFDocument
from oilgas.layout import Layout
from oilgas.layout.rows import LayoutRow
from oilgas.models.jib import JIBCostCenterSummary, JIBInvoice, JIBLine
from oilgas.util.dates import parse_check_date, parse_production_period
from oilgas.util.numbers import parse_decimal, require_decimal

MONEY_RE = r"(?:\(?-?\d[\d,]*\.\d{2}\)?)"
MONTH_RE = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"

SUMMARY_RE = re.compile(
    rf"^(?P<cost_center>\S+)\s+(?P<body>.+?)\s+"
    rf"(?P<amount>{MONEY_RE})(?:\s+(?P<cash_call>{MONEY_RE}))?\s+"
    rf"(?P<invoiced>{MONEY_RE})$"
)

DETAIL_RE = re.compile(
    rf"^(?P<op_account>\S+)\s+(?P<body>.+?)\s+"
    rf"(?P<partner_percent>-?\d+\.\d{{8}})\s+"
    rf"(?P<activity_period>{MONTH_RE}\s+\d{{2}})\s+"
    rf"(?P<gross>{MONEY_RE})\s+"
    rf"(?P<invoiced>{MONEY_RE})$"
)

INVOICE_NUMBER_RE = re.compile(r"\bInvoice Number\s+(?P<invoice_number>\S+)")
ACCOUNTING_MONTH_RE = re.compile(r"\bOp Accounting Month\s+(?P<month>[A-Za-z]+\s+\d{4})")
INVOICE_DATE_RE = re.compile(r"\bInvoice Date\s+(?P<date>\d{1,2}-[A-Za-z]{3}-\d{4})")
INVOICED_RE = re.compile(rf"\bInvoiced\s+(?P<amount>{MONEY_RE})")

COST_CLASS_HEADINGS = {
    "CAPITAL",
    "EXPENSE",
    "LEASEHOLD",
}

PAGE_FURNITURE_PREFIXES = (
    "Statement",
    "EnergyLink Operator Invoice - JIB",
    "Partner Operator Invoice",
    "Property Owner",
    "Sales Date Interest",
    "Type Deduct Code",
    "Deductions",
    "Operator",
    "Amounts",
    "OP Account Minor Account Description",
    "Percent Month",
    "www.energylink.com",
    "© ",
    "Invoice Number ",
    "Invoice Comment",
    "WHITE HAT ",
    "118 JAMES ST",
    "BOERNE,",
    "DALLAS,",
    "PLANO,",
    "HOUSTON,",
)


class JIBParser:
    def __init__(
        self,
        debug: bool = False,
    ):
        self.debug = debug

    def parse(
        self,
        document: PDFDocument,
        source_file: str,
    ) -> JIBInvoice | None:
        document_text = "\n".join(page.text for page in document.pages).upper()

        if "HIGHMARK ENERGY OPERATING" not in document_text:
            return None

        rows_by_page = [Layout(page).rows for page in document.pages]
        summary_page_index = self._find_summary_page(rows_by_page)

        if summary_page_index is None:
            return None

        header = self._parse_header(rows_by_page[summary_page_index])
        summaries = self._parse_summaries(rows_by_page[summary_page_index])
        lines = self._parse_detail_pages(rows_by_page[summary_page_index + 1 :])

        return JIBInvoice(
            operator=header["operator"],
            owner_number=header["owner_number"],
            invoice_number=header["invoice_number"],
            invoice_date=header["invoice_date"],
            accounting_period=header["accounting_period"],
            invoice_total=header["invoice_total"],
            cost_centers=summaries,
            lines=lines,
        )

    def _find_summary_page(
        self,
        rows_by_page: list[list[LayoutRow]],
    ) -> int | None:
        for i, rows in enumerate(rows_by_page):
            text = "\n".join(row.text for row in rows)
            if (
                "Operator Invoice - JIB" in text
                and "Cost Center" in text
                and "Report Total" in text
            ):
                return i

        return None

    def _parse_header(
        self,
        rows: list[LayoutRow],
    ) -> dict:
        text = "\n".join(row.text for row in rows)

        invoice_number = self._require_match(INVOICE_NUMBER_RE, text, "invoice_number")
        invoice_date_text = self._require_match(INVOICE_DATE_RE, text, "invoice_date")
        accounting_month_text = self._require_match(
            ACCOUNTING_MONTH_RE,
            text,
            "accounting_period",
        )
        invoice_total_text = self._require_match(INVOICED_RE, text, "invoice_total")

        owner_operator_row = next(
            (row.text for row in rows if "Invoice Number" in row.text),
            None,
        )
        accounting_row = next(
            (row.text for row in rows if "Op Accounting Month" in row.text),
            None,
        )

        if owner_operator_row is None:
            raise ValueError("Could not locate JIB owner/operator row.")

        before_invoice = owner_operator_row.split("Invoice Number", 1)[0].strip()
        accounting_tokens = accounting_row.split() if accounting_row else []
        owner_number = accounting_tokens[0] if accounting_tokens else None
        operator = self._parse_operator(before_invoice)

        if not owner_number:
            tokens = before_invoice.split()
            owner_number = tokens[0] if tokens else None

        if not operator:
            raise ValueError("Could not parse JIB operator name.")

        return {
            "owner_number": owner_number,
            "operator": operator,
            "invoice_number": invoice_number,
            "invoice_date": parse_check_date(invoice_date_text),
            "accounting_period": self._parse_accounting_month(accounting_month_text),
            "invoice_total": require_decimal(invoice_total_text, "invoice_total"),
        }

    def _parse_summaries(
        self,
        rows: list[LayoutRow],
    ) -> list[JIBCostCenterSummary]:
        summaries: list[JIBCostCenterSummary] = []
        in_table = False

        for row in rows:
            text = row.text.strip()

            if text.startswith("Cost Center "):
                in_table = True
                continue

            if not in_table:
                continue

            if text.startswith("Report Total"):
                break

            if self._is_summary_skip_row(text):
                continue

            match = SUMMARY_RE.match(text)

            if match is None:
                raise ValueError(f"Could not parse JIB summary row:\n{text}")

            body = match.group("body")
            afe, description = self._split_summary_body(body)

            summaries.append(
                JIBCostCenterSummary(
                    cost_center_code=match.group("cost_center"),
                    cost_center_name=description,
                    afe=afe,
                    description=description,
                    gross_amount=require_decimal(match.group("amount"), "summary.amount"),
                    cash_call_amount=parse_decimal(match.group("cash_call")),
                    invoiced_amount=require_decimal(match.group("invoiced"), "summary.invoiced"),
                    display_order=len(summaries) + 1,
                )
            )

        if not summaries:
            raise ValueError("No JIB cost center summary rows found.")

        return summaries

    def _parse_detail_pages(
        self,
        pages: list[list[LayoutRow]],
    ) -> list[JIBLine]:
        lines: list[JIBLine] = []
        current_cost_center_code: str | None = None
        current_cost_center_name: str | None = None
        current_afe: str | None = None
        current_cost_class: str | None = None
        current_account_group: str | None = None
        previous_line: JIBLine | None = None

        for rows in pages:
            page_text = "\n".join(row.text for row in rows)
            if "Cost Center" not in page_text and "OP Account" not in page_text:
                continue

            for row in rows:
                text = row.text.strip()

                if not text:
                    continue

                if text.startswith("AFE"):
                    current_afe = self._parse_afe(text)
                    continue

                if text.startswith("Cost Center"):
                    cost_center_code, cost_center_name = self._parse_cost_center(text)

                    if cost_center_code != current_cost_center_code:
                        current_cost_class = None
                        current_account_group = None
                        previous_line = None

                    current_cost_center_code = cost_center_code
                    current_cost_center_name = cost_center_name
                    continue

                if self._is_detail_skip_row(text):
                    continue

                if self._is_total_row(text):
                    continue

                if text.upper() in COST_CLASS_HEADINGS:
                    current_cost_class = text
                    current_account_group = None
                    continue

                match = DETAIL_RE.match(text)

                if match is not None:
                    if current_cost_center_code is None:
                        raise ValueError(f"JIB detail row before cost center:\n{text}")

                    line = self._line_from_match(
                        match,
                        cost_center_code=current_cost_center_code,
                        cost_center_name=current_cost_center_name,
                        afe=current_afe,
                        cost_class=current_cost_class,
                        account_group=current_account_group,
                        display_order=len(lines) + 1,
                    )
                    lines.append(line)
                    previous_line = line
                    continue

                if "~" in text:
                    if previous_line is None:
                        raise ValueError(f"JIB vendor continuation without detail row:\n{text}")

                    vendor_name, vendor_invoice = self._parse_vendor_line(text)
                    updated = previous_line.model_copy(
                        update={
                            "vendor_name": vendor_name,
                            "vendor_invoice": vendor_invoice,
                        }
                    )
                    lines[-1] = updated
                    previous_line = updated
                    continue

                if self._looks_like_account_group(text):
                    current_account_group = text
                    continue

                if previous_line is not None:
                    updated = previous_line.model_copy(
                        update={
                            "description": f"{previous_line.description} {text}",
                        }
                    )
                    lines[-1] = updated
                    previous_line = updated
                    continue

                raise ValueError(f"Unrecognized JIB detail row:\n{text}")

        if not lines:
            raise ValueError("No JIB detail lines found.")

        return lines

    def _line_from_match(
        self,
        match: re.Match,
        cost_center_code: str,
        cost_center_name: str | None,
        afe: str | None,
        cost_class: str | None,
        account_group: str | None,
        display_order: int,
    ) -> JIBLine:
        body = match.group("body")
        minor_account, description = self._split_detail_body(body)

        return JIBLine(
            cost_center_code=cost_center_code,
            cost_center_name=cost_center_name,
            afe=afe,
            cost_class=cost_class,
            account_group=account_group,
            op_account=match.group("op_account"),
            minor_account=minor_account,
            description=description,
            activity_period=parse_production_period(match.group("activity_period")),
            partner_percent=require_decimal(match.group("partner_percent"), "partner_percent"),
            gross_amount=require_decimal(match.group("gross"), "gross_amount"),
            invoiced_amount=require_decimal(match.group("invoiced"), "invoiced_amount"),
            display_order=display_order,
        )

    def _parse_operator(
        self,
        before_invoice: str,
    ) -> str | None:
        match = re.search(r"HIGHMARK ENERGY OPERATING,?\s+LLC", before_invoice)

        if match is not None:
            return match.group(0).replace(",", "")

        tokens = before_invoice.split()

        if len(tokens) > 1:
            return " ".join(tokens[1:])

        return None

    def _parse_afe(
        self,
        text: str,
    ) -> str | None:
        value = text.removeprefix("AFE").strip().rstrip(",")
        return value or None

    def _parse_cost_center(
        self,
        text: str,
    ) -> tuple[str, str | None]:
        value = text.removeprefix("Cost Center").strip()
        parts = value.split(maxsplit=1)

        if not parts:
            raise ValueError(f"Could not parse JIB cost center row:\n{text}")

        return parts[0], parts[1] if len(parts) > 1 else None

    def _parse_vendor_line(
        self,
        text: str,
    ) -> tuple[str | None, str | None]:
        parts = [part.strip() for part in text.split("~")]
        vendor_name = parts[0] or None
        vendor_invoice = parts[1] if len(parts) > 1 and parts[1] else None
        return vendor_name, vendor_invoice

    def _split_summary_body(
        self,
        body: str,
    ) -> tuple[str | None, str]:
        parts = body.split(maxsplit=1)

        if len(parts) == 2 and self._looks_like_afe(parts[0]):
            return parts[0], parts[1]

        return None, body

    def _split_detail_body(
        self,
        body: str,
    ) -> tuple[str | None, str]:
        parts = body.split(maxsplit=1)

        if len(parts) == 2 and self._looks_like_minor_account(parts[0]):
            return parts[0], parts[1]

        return None, body

    def _looks_like_afe(
        self,
        text: str,
    ) -> bool:
        return bool(re.match(r"^(?:\d+\*\S+|[A-Z]+\d+|\d{5,})$", text))

    def _looks_like_minor_account(
        self,
        text: str,
    ) -> bool:
        return bool(re.search(r"[A-Za-z]", text)) and len(text) <= 32

    def _looks_like_account_group(
        self,
        text: str,
    ) -> bool:
        if any(char.isdigit() for char in text):
            return False

        if text.startswith(PAGE_FURNITURE_PREFIXES):
            return False

        return bool(re.search(r"[A-Za-z]", text))

    def _is_summary_skip_row(
        self,
        text: str,
    ) -> bool:
        return text.startswith(("Invoice Comment", "HighMark ", "future payments", "75222 "))

    def _is_detail_skip_row(
        self,
        text: str,
    ) -> bool:
        return (
            text.startswith(PAGE_FURNITURE_PREFIXES)
            or " Invoice Number " in text
            or " Op Accounting Month " in text
            or text.startswith("Invoiced ")
            or "TIN:" in text
            or re.match(r"^\(?\d{3}\)?[-\s]\d{3}-\d{4}$", text) is not None
        )

    def _is_total_row(
        self,
        text: str,
    ) -> bool:
        return text.startswith("Total ")

    def _parse_accounting_month(
        self,
        value: str,
    ) -> date:
        return parse_check_date(f"1 {value}").replace(day=1)

    def _require_match(
        self,
        regex: re.Pattern,
        text: str,
        field_name: str,
    ) -> str:
        match = regex.search(text)

        if match is None:
            raise ValueError(f"Could not locate JIB field: {field_name}")

        return match.group(1)
