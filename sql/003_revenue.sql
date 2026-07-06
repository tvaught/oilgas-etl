-- ============================================================
-- Revenue Statements
-- ============================================================

CREATE TABLE revenue_statement (

    statement_id UUID PRIMARY KEY,

    source_file_id UUID NOT NULL
        REFERENCES source_file(source_file_id),

    operator_id UUID
        REFERENCES operator(operator_id),

    check_number TEXT NOT NULL,

    owner_number TEXT,

    check_date DATE NOT NULL,

    accounting_period DATE,

    check_amount DECIMAL(18,2) NOT NULL,

    gross_revenue DECIMAL(18,2),

    total_deductions DECIMAL(18,2),

    severance_tax DECIMAL(18,2),

    net_revenue DECIMAL(18,2),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE revenue_product (

    product_id UUID PRIMARY KEY,

    statement_id UUID NOT NULL
        REFERENCES revenue_statement(statement_id),

    property_id UUID NOT NULL
        REFERENCES property(property_id),

    product TEXT NOT NULL,

    display_order INTEGER NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (
        statement_id,
        property_id,
        product
    )
);

CREATE TABLE revenue_line (

    line_id UUID PRIMARY KEY,

    statement_id UUID NOT NULL
        REFERENCES revenue_statement(statement_id),

    property_id UUID NOT NULL
        REFERENCES property(property_id),

    product_id UUID NOT NULL
        REFERENCES revenue_product(product_id),

    line_type TEXT,
    revenue_type TEXT NOT NULL,
    tax_deduct_code TEXT,
    production_period DATE,
    property_volume DECIMAL(18,6),
    unit_price DECIMAL(18,6),
    property_gross_value DECIMAL(18,2),
    property_deductions DECIMAL(18,2),
    property_net_value DECIMAL(18,2),
    owner_interest DECIMAL(18,10),
    distribution_interest DECIMAL(18,10),
    owner_volume DECIMAL(18,6),
    owner_gross_value DECIMAL(18,2),
    owner_deductions DECIMAL(18,2),
    owner_net_value DECIMAL(18,2),

);
