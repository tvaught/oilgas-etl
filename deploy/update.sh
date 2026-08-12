#!/usr/bin/env bash
# Update the deployed application checkout and restart Gunicorn.
# Run as the deployment user (for example, travis), not as root.

set -euo pipefail

verbose=false

usage() {
    cat <<'EOF'
Usage: ./deploy/update.sh [--verbose|-v]

Update the application checkout, sync locked dependencies, repair service
permissions, and restart the oilgas service.

Options:
  -v, --verbose  Print systemd status and the latest 100 service-log lines.
  -h, --help     Show this help text.
EOF
}

run() {
    printf '+ '
    printf '%q ' "$@"
    printf '\n'
    "$@"
}

while (( $# > 0 )); do
    case "$1" in
        -v|--verbose)
            verbose=true
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown option: %s\n\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

printf 'Updating Oil & Gas ETL in %s\n' "$app_dir"
cd "$app_dir"

run git pull origin main --ff-only
run uv sync --frozen
run sudo chown -R travis:oilgas "$app_dir"
run sudo chmod -R g+rX "$app_dir"
run sudo systemctl restart oilgas
run sudo systemctl is-active --quiet oilgas
printf 'oilgas service is active.\n'

if "$verbose"; then
    run sudo systemctl status oilgas --no-pager
    run sudo journalctl -u oilgas -n 100 --no-pager
fi
