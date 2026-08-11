#!/usr/bin/env bash
# Update the deployed application checkout and restart Gunicorn.
# Run as the deployment user (for example, travis), not as root.

set -euo pipefail

app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$app_dir"

git pull --ff-only
uv sync --frozen

sudo chown -R travis:oilgas "$app_dir"
sudo chmod -R g+rX "$app_dir"

sudo systemctl restart oilgas
sudo systemctl status oilgas --no-pager
sudo journalctl -u oilgas -n 100 --no-pager
