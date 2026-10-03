#!/usr/bin/env bash
# Ingest PDFs into the production database and restart the reporting service.
# Run as the deployment user (for example, travis), not as root.

set -euo pipefail

app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
database_path="/srv/oilgas/data/oilgas.duckdb"
raw_data_dir="/srv/oilgas/data/raw"
debug=false
service_stopped=false

usage() {
    cat <<'EOF'
Usage: ./deploy/ingest.sh [--debug] <source-path>

Ingest revenue and Highmark JIB PDFs into the production DuckDB database.
The source path must be /srv/oilgas/data/raw/ or a path within it.
Directory inputs are scanned recursively for PDFs.

Options:
  --debug     Show parser and repository debug output.
  -h, --help  Show this help text.
EOF
}

run() {
    printf '+ '
    printf '%q ' "$@"
    printf '\n'
    "$@"
}

repair_archive_permissions() {
    printf 'Repairing raw archive permissions for the oilgas service account.\n'
    sudo chown -R travis:oilgas "$raw_data_dir"
    sudo chmod -R g+rX "$raw_data_dir"
}

restart_service() {
    if "$service_stopped"; then
        repair_archive_permissions
        printf 'Restarting oilgas service.\n'
        sudo systemctl start oilgas
    fi
}

while (( $# > 0 )); do
    case "$1" in
        --debug)
            debug=true
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --*)
            printf 'Unknown option: %s\n\n' "$1" >&2
            usage >&2
            exit 2
            ;;
        *)
            if [[ -n ${source_path+x} ]]; then
                printf 'Only one source path may be provided.\n\n' >&2
                usage >&2
                exit 2
            fi
            source_path="$1"
            ;;
    esac
    shift
done

if [[ -z ${source_path+x} ]]; then
    usage >&2
    exit 2
fi

source_path="$(realpath "$source_path")"
if [[ "$source_path" != "$raw_data_dir" && "$source_path" != "$raw_data_dir"/* ]]; then
    printf 'Source must be within %s: %s\n' "$raw_data_dir" "$source_path" >&2
    exit 2
fi
if [[ ! -e "$source_path" ]]; then
    printf 'Source does not exist: %s\n' "$source_path" >&2
    exit 2
fi
if [[ ! -f "$database_path" ]]; then
    printf 'Production database does not exist: %s\n' "$database_path" >&2
    exit 1
fi

trap restart_service EXIT

printf 'Ingesting %s into %s\n' "$source_path" "$database_path"
cd "$app_dir"

run sudo systemctl stop oilgas
service_stopped=true

if "$debug"; then
    run uv run oilgas ingest --database "$database_path" "$source_path" --debug
else
    run uv run oilgas ingest --database "$database_path" "$source_path"
fi
