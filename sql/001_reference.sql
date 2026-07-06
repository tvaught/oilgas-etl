-- ============================================================
-- Reference Data
-- ============================================================

CREATE TABLE operator (

    operator_id UUID PRIMARY KEY,

    operator_name TEXT NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE vendor (

    vendor_id UUID PRIMARY KEY,

    vendor_name TEXT NOT NULL UNIQUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE expense_category (

    category_id UUID PRIMARY KEY,

    category_name TEXT NOT NULL UNIQUE,

    parent_category UUID
        REFERENCES expense_category(category_id),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cost_center (

    cost_center_id UUID PRIMARY KEY,

    cost_center_code TEXT UNIQUE,

    description TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE property (

    property_id UUID PRIMARY KEY,

    operator_id UUID
        REFERENCES operator(operator_id),

    property_code TEXT NOT NULL UNIQUE,

    property_name TEXT NOT NULL,

    county TEXT,

    state TEXT,

    api_number TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ownership_interest (

    interest_id UUID PRIMARY KEY,

    property_id UUID NOT NULL
        REFERENCES property(property_id),

    owner_name TEXT NOT NULL,

    working_interest DECIMAL(18,10),

    revenue_interest DECIMAL(18,10),

    effective_date DATE,

    expiration_date DATE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
