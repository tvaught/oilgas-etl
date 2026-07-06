-- ============================================================
-- Joint Interest Billing
-- ============================================================

CREATE TABLE jib_invoice (

    invoice_id UUID PRIMARY KEY,

    source_file_id UUID NOT NULL
        REFERENCES source_file(source_file_id),

    operator_id UUID
        REFERENCES operator(operator_id),

    invoice_number TEXT NOT NULL,

    invoice_date DATE,

    accounting_period DATE,

    invoice_total DECIMAL(18,2),

    payment_status TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE jib_line (

    line_id UUID PRIMARY KEY,

    invoice_id UUID NOT NULL
        REFERENCES jib_invoice(invoice_id),

    vendor_id UUID
        REFERENCES vendor(vendor_id),

    cost_center_id UUID
        REFERENCES cost_center(cost_center_id),

    category_id UUID
        REFERENCES expense_category(category_id),

    property_id UUID
        REFERENCES property(property_id),

    activity_period DATE,

    afe TEXT,

    op_account TEXT,

    minor_account TEXT,

    description TEXT,

    gross_amount DECIMAL(18,2),

    working_interest DECIMAL(18,10),

    net_amount DECIMAL(18,2)
);
