from __future__ import annotations

from pathlib import Path
from uuid import UUID

from oilgas.models.jib import JIBCostCenterSummary, JIBInvoice, JIBLine
from oilgas.util.hashing import sha256
from oilgas.util.ids import new_uuid

from .base import Repository


class JIBRepository(Repository):
    def __init__(
        self,
        connection,
        debug: bool = False,
    ):
        super().__init__(connection)
        self.debug = debug

    def is_imported(
        self,
        invoice: JIBInvoice,
    ) -> bool:
        operator_id = self._operator_id(invoice.operator)

        if operator_id is None:
            return False

        return self._has_invoice(operator_id, invoice.invoice_number)

    def insert(
        self,
        pdf: Path,
        invoice: JIBInvoice,
    ) -> bool:
        self.connection.begin()

        try:
            source_file_id = self._insert_source_file(pdf)
            operator_id = self._upsert_operator(invoice.operator)

            if self._has_invoice(operator_id, invoice.invoice_number):
                self._debug(f"Skipping already imported JIB invoice: {invoice.invoice_number}")
                self.connection.commit()
                return False

            invoice_id = self._insert_invoice(
                source_file_id,
                operator_id,
                invoice,
            )

            cost_center_ids: dict[str, UUID] = {}

            for summary in invoice.cost_centers:
                cost_center_id = self._upsert_cost_center(operator_id, summary)
                cost_center_ids[summary.cost_center_code] = cost_center_id
                self._insert_summary(invoice_id, cost_center_id, summary)

            for line in invoice.lines:
                cost_center_id = cost_center_ids.get(line.cost_center_code)

                if cost_center_id is None:
                    cost_center_id = self._upsert_cost_center_from_line(operator_id, line)
                    cost_center_ids[line.cost_center_code] = cost_center_id

                vendor_id = self._upsert_vendor(line.vendor_name) if line.vendor_name else None
                self._insert_line(invoice_id, cost_center_id, vendor_id, line)

            self.connection.commit()
            return True

        except Exception:
            self.connection.rollback()
            raise

    def _insert_source_file(
        self,
        pdf: Path,
    ) -> UUID:
        digest = sha256(pdf)

        row = self.execute(
            """
            SELECT source_file_id
            FROM source_file
            WHERE sha256 = ?
            """,
            (digest,),
        ).fetchone()

        if row is not None:
            return row[0]

        source_file_id = new_uuid()

        self.execute(
            """
            INSERT INTO source_file (
                source_file_id,
                filename,
                filepath,
                sha256,
                filesize,
                page_count,
                document_type,
                parser,
                parser_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_file_id,
                pdf.name,
                str(pdf.resolve()),
                digest,
                pdf.stat().st_size,
                None,
                "jib",
                "JIBParser",
                "1.0",
            ),
        )

        return source_file_id

    def _operator_id(
        self,
        operator_name: str,
    ) -> UUID | None:
        row = self.execute(
            """
            SELECT operator_id
            FROM operator
            WHERE operator_name = ?
            """,
            (operator_name,),
        ).fetchone()

        return row[0] if row else None

    def _upsert_operator(
        self,
        operator_name: str,
    ) -> UUID:
        operator_id = self._operator_id(operator_name)

        if operator_id is not None:
            return operator_id

        operator_id = new_uuid()

        self.execute(
            """
            INSERT INTO operator (
                operator_id,
                operator_name
            )
            VALUES (?, ?)
            """,
            (operator_id, operator_name),
        )

        return operator_id

    def _has_invoice(
        self,
        operator_id: UUID,
        invoice_number: str,
    ) -> bool:
        row = self.execute(
            """
            SELECT 1
            FROM jib_invoice
            WHERE operator_id = ?
                AND invoice_number = ?
            LIMIT 1
            """,
            (operator_id, invoice_number),
        ).fetchone()

        return row is not None

    def _insert_invoice(
        self,
        source_file_id: UUID,
        operator_id: UUID,
        invoice: JIBInvoice,
    ) -> UUID:
        invoice_id = new_uuid()

        self.execute(
            """
            INSERT INTO jib_invoice (
                invoice_id,
                source_file_id,
                operator_id,
                owner_number,
                invoice_number,
                invoice_date,
                accounting_period,
                invoice_total,
                payment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                source_file_id,
                operator_id,
                invoice.owner_number,
                invoice.invoice_number,
                invoice.invoice_date,
                invoice.accounting_period,
                invoice.invoice_total,
                invoice.payment_status,
            ),
        )

        return invoice_id

    def _upsert_cost_center(
        self,
        operator_id: UUID,
        summary: JIBCostCenterSummary,
    ) -> UUID:
        return self._upsert_cost_center_values(
            operator_id,
            summary.cost_center_code,
            summary.cost_center_name,
        )

    def _upsert_cost_center_from_line(
        self,
        operator_id: UUID,
        line: JIBLine,
    ) -> UUID:
        return self._upsert_cost_center_values(
            operator_id,
            line.cost_center_code,
            line.cost_center_name,
        )

    def _upsert_cost_center_values(
        self,
        operator_id: UUID,
        cost_center_code: str,
        cost_center_name: str | None,
    ) -> UUID:
        row = self.execute(
            """
            SELECT cost_center_id
            FROM jib_cost_center
            WHERE operator_id = ?
                AND cost_center_code = ?
            """,
            (operator_id, cost_center_code),
        ).fetchone()

        if row is not None:
            return row[0]

        cost_center_id = new_uuid()

        self.execute(
            """
            INSERT INTO jib_cost_center (
                cost_center_id,
                operator_id,
                cost_center_code,
                cost_center_name
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                cost_center_id,
                operator_id,
                cost_center_code,
                cost_center_name,
            ),
        )

        return cost_center_id

    def _insert_summary(
        self,
        invoice_id: UUID,
        cost_center_id: UUID,
        summary: JIBCostCenterSummary,
    ) -> UUID:
        summary_id = new_uuid()

        self.execute(
            """
            INSERT INTO jib_cost_center_summary (
                summary_id,
                invoice_id,
                cost_center_id,
                afe,
                description,
                gross_amount,
                cash_call_amount,
                invoiced_amount,
                display_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary_id,
                invoice_id,
                cost_center_id,
                summary.afe,
                summary.description,
                summary.gross_amount,
                summary.cash_call_amount,
                summary.invoiced_amount,
                summary.display_order,
            ),
        )

        return summary_id

    def _upsert_vendor(
        self,
        vendor_name: str,
    ) -> UUID:
        row = self.execute(
            """
            SELECT vendor_id
            FROM vendor
            WHERE vendor_name = ?
            """,
            (vendor_name,),
        ).fetchone()

        if row is not None:
            return row[0]

        vendor_id = new_uuid()

        self.execute(
            """
            INSERT INTO vendor (
                vendor_id,
                vendor_name
            )
            VALUES (?, ?)
            """,
            (vendor_id, vendor_name),
        )

        return vendor_id

    def _insert_line(
        self,
        invoice_id: UUID,
        cost_center_id: UUID,
        vendor_id: UUID | None,
        line: JIBLine,
    ) -> UUID:
        line_id = new_uuid()

        self.execute(
            """
            INSERT INTO jib_line (
                line_id,
                invoice_id,
                cost_center_id,
                vendor_id,
                afe,
                cost_class,
                account_group,
                op_account,
                minor_account,
                description,
                vendor_invoice,
                activity_period,
                partner_percent,
                gross_amount,
                invoiced_amount,
                display_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                line_id,
                invoice_id,
                cost_center_id,
                vendor_id,
                line.afe,
                line.cost_class,
                line.account_group,
                line.op_account,
                line.minor_account,
                line.description,
                line.vendor_invoice,
                line.activity_period,
                line.partner_percent,
                line.gross_amount,
                line.invoiced_amount,
                line.display_order,
            ),
        )

        return line_id

    def _debug(
        self,
        message: object,
    ) -> None:
        if self.debug:
            print(message)
