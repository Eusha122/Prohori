#!/bin/bash
# Runs ON the server (as ubuntu) after the code is unpacked in /opt/prohori. Safe to run again.
set -euo pipefail
cd /opt/prohori
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements-server.txt
cd collector
npm ci --no-audit --no-fund --loglevel=error
sudo npx --yes playwright install-deps chromium >/dev/null
npx --yes playwright install chromium >/dev/null
cd ..
sudo cp deploy/prohori.service deploy/prohori-update.service deploy/prohori-update.timer /etc/systemd/system/
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl daemon-reload
sudo systemctl enable --now prohori.service prohori-update.timer
sudo systemctl restart prohori.service
sudo systemctl reload caddy || sudo systemctl restart caddy
echo "SETUP DONE"
