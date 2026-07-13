-- ============================================================
-- Joint Interest Billing
-- ============================================================

CREATE TABLE jib_invoice (

    invoice_id UUID PRIMARY KEY,

    source_file_id UUID NOT NULL
        REFERENCES source_file(source_file_id),

    operator_id UUID NOT NULL
        REFERENCES operator(operator_id),

    owner_number TEXT,

    invoice_number TEXT NOT NULL,

    invoice_date DATE,

    accounting_period DATE,

    invoice_total DECIMAL(18,2),

    payment_status TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (
        operator_id,
        invoice_number
    )
);

CREATE TABLE jib_cost_center (

    cost_center_id UUID PRIMARY KEY,

    operator_id UUID NOT NULL
        REFERENCES operator(operator_id),

    cost_center_code TEXT NOT NULL,

    cost_center_name TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (
        operator_id,
        cost_center_code
    )
);

CREATE TABLE jib_cost_center_summary (

    summary_id UUID PRIMARY KEY,

    invoice_id UUID NOT NULL
        REFERENCES jib_invoice(invoice_id),

    cost_center_id UUID NOT NULL
        REFERENCES jib_cost_center(cost_center_id),

    afe TEXT,

    description TEXT,

    gross_amount DECIMAL(18,2),

    cash_call_amount DECIMAL(18,2),

    invoiced_amount DECIMAL(18,2),

    display_order INTEGER NOT NULL
);

CREATE TABLE jib_line (

    line_id UUID PRIMARY KEY,

    invoice_id UUID NOT NULL
        REFERENCES jib_invoice(invoice_id),

    cost_center_id UUID NOT NULL
        REFERENCES jib_cost_center(cost_center_id),

    vendor_id UUID
        REFERENCES vendor(vendor_id),

    afe TEXT,

    cost_class TEXT,

    account_group TEXT,

    op_account TEXT,

    minor_account TEXT,

    description TEXT,

    vendor_invoice TEXT,

    activity_period DATE,

    partner_percent DECIMAL(18,10),

    gross_amount DECIMAL(18,2),

    invoiced_amount DECIMAL(18,2),

    display_order INTEGER NOT NULL
);
