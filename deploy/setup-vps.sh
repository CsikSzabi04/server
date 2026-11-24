#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Auri AI backend — one-shot VPS setup (Ubuntu, x86_64 or ARM/aarch64).
# Installs Node 20, Ollama (+ perf tuning + models), Piper TTS (+ Hungarian
# voice), builds the server, runs it as a systemd service, and (optionally)
# fronts it with Caddy for automatic HTTPS.
#
# Run it AFTER the server/ code is on the box (git clone or scp) at $APP_DIR.
#
#   sudo DOMAIN=auri.example.com bash deploy/setup-vps.sh
#   # or without a domain (HTTP only, key-protected — see README):
#   sudo bash deploy/setup-vps.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── tunables (override via env) ──────────────────────────────────────────────
DOMAIN="${DOMAIN:-}"                                  # FQDN for HTTPS; empty = no Caddy
APP_DIR="${APP_DIR:-/opt/auri/server}"               # where the server/ code lives
PIPER_DIR="${PIPER_DIR:-/opt/auri/piper}"
MODELS="${MODELS:-gemma2:2b qwen2.5:3b-instruct}"     # space-separated
DEFAULT_MODEL="${DEFAULT_MODEL:-gemma2:2b}"
RUN_USER="${SUDO_USER:-$USER}"
PIPER_REL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2"
VOICE_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/hu/hu_HU/anna/medium"

echo "==> base packages"
sudo apt-get update -y
sudo apt-get install -y curl git ca-certificates ufw tar

echo "==> Node 20"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
node --version

echo "==> Ollama"
curl -fsSL https://ollama.com/install.sh | sh
# Perf + keep-alive as a systemd drop-in (so the model stays hot 24/7).
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null <<'EOF'
[Service]
Environment="OLLAMA_KEEP_ALIVE=30m"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
sleep 3
for m in $MODELS; do echo "   pulling $m"; ollama pull "$m"; done

echo "==> Piper TTS"
ARCH="$(uname -m)"
case "$ARCH" in
  aarch64|arm64) PIPER_TGZ="piper_linux_aarch64.tar.gz" ;;
  x86_64|amd64)  PIPER_TGZ="piper_linux_x86_64.tar.gz" ;;
  *) echo "   !! unknown arch $ARCH — skipping Piper"; PIPER_TGZ="" ;;
esac
if [ -n "$PIPER_TGZ" ]; then
  sudo mkdir -p "$PIPER_DIR/voices"
  curl -fsSL "$PIPER_REL/$PIPER_TGZ" -o /tmp/piper.tgz
  sudo tar -xzf /tmp/piper.tgz -C "$PIPER_DIR"          # -> $PIPER_DIR/piper/piper
  sudo curl -fsSL "$VOICE_BASE/hu_HU-anna-medium.onnx"      -o "$PIPER_DIR/voices/hu_HU-anna-medium.onnx"
  sudo curl -fsSL "$VOICE_BASE/hu_HU-anna-medium.onnx.json" -o "$PIPER_DIR/voices/hu_HU-anna-medium.onnx.json"
fi

echo "==> build the server ($APP_DIR)"
cd "$APP_DIR"
npm install
npm run build
[ -f .env ] || npm run generate-key   # creates .env (+ a fresh API key) on first run

# helper: set or replace a KEY=value line in .env
set_env() {
  local k="$1" v="$2"
  if grep -q "^$k=" .env; then sed -i "s|^$k=.*|$k=$v|" .env; else echo "$k=$v" >> .env; fi
}
set_env OLLAMA_MODEL    "$DEFAULT_MODEL"
set_env ALLOWED_ORIGINS ""                                   # server-to-server via Vercel proxy
if [ -n "${PIPER_TGZ:-}" ]; then
  set_env PIPER_BIN   "$PIPER_DIR/piper/piper"
  set_env PIPER_VOICE "$PIPER_DIR/voices/hu_HU-anna-medium.onnx"
fi

echo "==> systemd service for the server"
sudo tee /etc/systemd/system/auri-server.service >/dev/null <<EOF
[Unit]
Description=Auri AI server
After=network-online.target ollama.service
Wants=network-online.target

[Service]
WorkingDirectory=$APP_DIR
ExecStart=$(command -v node) $APP_DIR/dist/src/index.js
Restart=always
RestartSec=3
User=$RUN_USER
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now auri-server

echo "==> journald: keep server logs at most 30 days (privacy notice §2, SECURITY.md §15.6)"
sudo mkdir -p /etc/systemd/journald.conf.d
sudo tee /etc/systemd/journald.conf.d/auri-retention.conf >/dev/null <<'EOF'
[Journal]
MaxRetentionSec=30day
EOF
sudo systemctl restart systemd-journald

echo "==> firewall (ufw)"
sudo ufw allow 22/tcp
if [ -n "$DOMAIN" ]; then sudo ufw allow 80/tcp; sudo ufw allow 443/tcp; else sudo ufw allow 8787/tcp; fi
sudo ufw --force enable

if [ -n "$DOMAIN" ]; then
  echo "==> Caddy (automatic HTTPS for $DOMAIN -> 127.0.0.1:8787)"
  sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -y && sudo apt-get install -y caddy
  sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
$DOMAIN {
    reverse_proxy 127.0.0.1:8787
}
EOF
  sudo systemctl restart caddy
fi

echo
echo "──────────────────────────────────────────────────────────────"
echo " DONE. Health check:"
echo "   curl http://127.0.0.1:8787/health"
if [ -n "$DOMAIN" ]; then echo "   public: https://$DOMAIN/health"; fi
echo
echo " Your API key (put it in Vercel as AURI_SERVER_API_KEY):"
grep '^AURI_API_KEY=' "$APP_DIR/.env" | sed 's/^AURI_API_KEY=//; s/,.*//'
echo
echo " On Vercel set:"
if [ -n "$DOMAIN" ]; then echo "   AURI_SERVER_URL=https://$DOMAIN"; else echo "   AURI_SERVER_URL=http://<ORACLE_PUBLIC_IP>:8787"; fi
echo "   AURI_SERVER_API_KEY=<the key above>"
echo "   VITE_API_URL=/api/chat"
echo "──────────────────────────────────────────────────────────────"
