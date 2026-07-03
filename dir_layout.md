oilgas-etl/
│
├── pyproject.toml
├── README.md
├── .gitignore
├── .python-version
│
├── config/
│   ├── settings.toml
│   └── categories.toml
│
├── data/
│   ├── raw/
│   │   ├── highmark/
│   │   │   ├── revenue/
│   │   │   └── jib/
│   │   └── xto/
│   │       ├── revenue/
│   │       └── jib/
│   │
│   ├── archive/
│   └── oilgas.duckdb
│
├── sql/
│   ├── schema.sql
│   ├── views.sql
│   └── indexes.sql
│
├── src/
│   └── oilgas/
│
│       ├── cli.py
│       ├── config.py
│       ├── database.py
│       ├── hashing.py
│       │
│       ├── models/
│       │
│       ├── parsers/
│       │
│       ├── extractors/
│       │
│       ├── loaders/
│       │
│       ├── classify/
│       │
│       ├── reports/
│       │
│       └── util/
│
├── tests/
│
└── notebooks/
