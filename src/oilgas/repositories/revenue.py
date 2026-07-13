from __future__ import annotations

from pathlib import Path
from uuid import UUID

from oilgas.models.revenue import RevenueLine, RevenueProduct, RevenueProperty, RevenueStatement
from oilgas.util.hashing import sha256
from oilgas.util.ids import new_uuid

from .base import Repository


class RevenueRepository(Repository):
    def __init__(
        self,
        connection,
        debug: bool = False,
    ):
        super().__init__(connection)
        self.debug = debug

    def is_imported(
        self,
        pdf: Path,
    ) -> bool:
        digest = sha256(pdf)

        row = self.execute(
            """
            SELECT 1
            FROM source_file sf
            JOIN revenue_statement rs
                ON rs.source_file_id = sf.source_file_id
            WHERE sf.sha256 = ?
            LIMIT 1
            """,
            (digest,),
        ).fetchone()

        return row is not None

    def insert(
        self,
        pdf: Path,
        statement: RevenueStatement,
    ) -> bool:

        self.connection.begin()

        try:
            source_file_id = self._insert_source_file(pdf)

            if self._has_revenue_statement(source_file_id):
                self._debug(f"Skipping already imported revenue statement: {pdf}")
                self.connection.commit()
                return False

            operator_id = self._upsert_operator(statement.operator)
            statement_id = self._insert_statement(
                source_file_id,
                operator_id,
                statement,
            )

            for property_ in statement.properties:
                self._debug(f"attempting to upsert {property_.property_name}, {property_.county}")
                property_id = self._upsert_property(operator_id, property_)

                for display_order, product in enumerate(property_.products, start=1):
                    product_id = self._insert_product(
                        statement_id,
                        property_id,
                        product,
                        display_order,
                    )

                    for line in product.lines:
                        self._debug(line.model_dump())
                        self._insert_line(
                            statement_id,
                            property_id,
                            product_id,
                            line,
                        )
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
                "revenue",
                "RevenueParser",
                "1.0",
            ),
        )

        return source_file_id

    def _has_revenue_statement(
        self,
        source_file_id: UUID,
    ) -> bool:
        row = self.execute(
            """
            SELECT 1
            FROM revenue_statement
            WHERE source_file_id = ?
            LIMIT 1
            """,
            (source_file_id,),
        ).fetchone()

        return row is not None

    def _upsert_operator(
        self,
        operator_name: str,
    ) -> UUID:

        row = self.execute(
            """
            SELECT operator_id
            FROM operator
            WHERE operator_name = ?
            """,
            (operator_name,),
        ).fetchone()

        if row is not None:
            return row[0]

        operator_id = new_uuid()

        self.execute(
            """
            INSERT INTO operator (

                operator_id,
                operator_name

            )

            VALUES (?, ?)
            """,
            (
                operator_id,
                operator_name,
            ),
        )

        return operator_id

    def _upsert_property(
        self,
        operator_id: UUID,
        property_: RevenueProperty,
    ) -> UUID:
        """
        Return the property's UUID.

        Properties are uniquely identified by property_code.
        Existing metadata is refreshed on every import.
        """

        row = self.execute(
            """
            SELECT property_id
            FROM property
            WHERE property_code = ?
            """,
            (property_.property_code,),
        ).fetchone()

        if row is not None:
            return row[0]

        property_id = new_uuid()

        self.execute(
            """
            INSERT INTO property (

                property_id,

                operator_id,

                property_code,
                property_name,

                county,
                state,

                api_number

            )

            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                property_id,
                operator_id,
                property_.property_code,
                property_.property_name,
                property_.county,
                property_.state,
                property_.api_number,
            ),
        )

        return property_id

    def _insert_statement(
        self,
        source_file_id: UUID,
        operator_id: UUID,
        statement: RevenueStatement,
    ) -> UUID:

        statement_id = new_uuid()

        self.execute(
            """
            INSERT INTO revenue_statement (

                statement_id,
                source_file_id,
                operator_id,

                check_number,
                owner_number,
                check_date,
                accounting_period,

                check_amount,
                gross_revenue,
                total_deductions,
                severance_tax,
                net_revenue

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                statement_id,
                source_file_id,
                operator_id,
                statement.check_number,
                statement.owner_number,
                statement.check_date,
                statement.accounting_period,
                statement.check_amount,
                None,
                None,
                None,
                None,
            ),
        )

        return statement_id

    def _insert_product(
        self,
        statement_id: UUID,
        property_id: UUID,
        product: RevenueProduct,
        display_order: int,
    ) -> UUID:

        product_id = new_uuid()

        self.execute(
            """
            INSERT INTO revenue_product (

                product_id,
                statement_id,
                property_id,
                product,
                display_order

            )

            VALUES (?, ?, ?, ?, ?)
            """,
            (
                product_id,
                statement_id,
                property_id,
                product.product,
                display_order,
            ),
        )

        return product_id

    def _insert_line(
        self,
        statement_id: UUID,
        property_id: UUID,
        product_id: UUID,
        line: RevenueLine,
    ) -> UUID:

        line_id = new_uuid()

        self.execute(
            """
            INSERT INTO revenue_line (

                line_id,
                statement_id,
                property_id,
                product_id,

                line_type,
                revenue_type,

                tax_deduct_code,

                production_period,

                property_volume,
                unit_price,
                property_gross_value,
                property_deductions,
                property_net_value,

                owner_interest,
                distribution_interest,

                owner_volume,
                owner_gross_value,
                owner_deductions,
                owner_net_value

            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                line_id,
                statement_id,
                property_id,
                product_id,
                line.line_type,
                line.revenue_type,
                line.tax_deduct_code,
                line.production_period,
                line.property_volume,
                line.unit_price,
                line.property_gross_value,
                line.property_deductions,
                line.property_net_value,
                line.owner_interest,
                line.distribution_interest,
                line.owner_volume,
                line.owner_gross_value,
                line.owner_deductions,
                line.owner_net_value,
            ),
        )

        return line_id

    def _debug(
        self,
        message: object,
    ) -> None:
        if self.debug:
            print(message)
