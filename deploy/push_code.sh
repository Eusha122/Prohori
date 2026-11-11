#!/bin/bash
# Send code changes (app + pipeline + collector scripts) to the live server and restart the site.
# Data and the server's .env are not touched. Run from the project folder in Git Bash:  bash deploy/push_code.sh
set -euo pipefail
cd "$(dirname "$0")/.."
KEY="$HOME/.ssh/prohori-mumbai.pem"
HOST="ubuntu@$(python -c "import json;print(json.load(open('deploy/state.json'))['ip'])" 2>/dev/null || echo 13.201.237.123)"
tar --exclude='__pycache__' --exclude='*.pyc' -czf /tmp/prohori-code.tar.gz app pipeline collector/*.js requirements-server.txt deploy/*.service deploy/*.timer deploy/Caddyfile
scp -i "$KEY" /tmp/prohori-code.tar.gz "$HOST:/tmp/"
ssh -i "$KEY" "$HOST" 'cd /opt/prohori && tar -xzf /tmp/prohori-code.tar.gz && rm /tmp/prohori-code.tar.gz && sudo systemctl restart prohori && echo "live site restarted"'
