-- ============================================================
-- Imported Documents
-- ============================================================

CREATE TABLE source_file (

    source_file_id UUID PRIMARY KEY,

    filename TEXT NOT NULL,

    filepath TEXT,

    sha256 TEXT NOT NULL UNIQUE,

    filesize BIGINT,

    page_count INTEGER,

    imported_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    document_type TEXT,

    parser TEXT,

    parser_version TEXT
);

CREATE TABLE document_page (

    source_file_id UUID NOT NULL
        REFERENCES source_file(source_file_id),

    page_number INTEGER NOT NULL,

    page_text TEXT,

    PRIMARY KEY (
        source_file_id,
        page_number
    )
);

CREATE TABLE import_log (

    import_log_id UUID PRIMARY KEY,

    source_file_id UUID
        REFERENCES source_file(source_file_id),

    imported_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    status TEXT,

    rows_inserted INTEGER,

    warnings INTEGER,

    errors INTEGER,

    elapsed_ms INTEGER
);
