# Deploying the bot + website to run 24/7

Your PC can't run anything while it's off. True 24/7 operation means renting a
small cloud server (a "VPS") and running this project there with Docker. The
whole stack — bot plus dashboard website — is already packaged in
`docker-compose.yml`, so deployment is one command once you have a server.

## 1. Get a server (the only step that costs money)

Any of these is plenty (the bot is lightweight — 1 vCPU / 1–2 GB RAM is fine):

| Provider | Plan | Cost |
|---|---|---|
| Hetzner Cloud | CX22, Ubuntu 24.04 | ~€4/month |
| DigitalOcean | Basic Droplet, Ubuntu 24.04 | ~$6/month |
| Oracle Cloud | "Always Free" Ampere instance | $0 (free tier) |

Create an Ubuntu 24.04 server, add your SSH key during setup, and note its IP.

## 2. Prepare the project (one-time, before first upload)

**Change the API credentials in `config.json`** (`api_server` section: `password`,
`jwt_secret_key`, `ws_token`) — the current ones were fine for localhost-only
paper trading but must be fresh secrets before the config lives on a server.

## 3. Upload and start

From PowerShell on this PC (replace `SERVER_IP`):

```powershell
# Copy the project (excludes .venv — not needed on the server)
scp -r config.json config.docker.json docker-compose.yml dashboard user_data root@SERVER_IP:/opt/crypto-trader/

# Log in and start everything
ssh root@SERVER_IP
```

On the server:

```bash
curl -fsSL https://get.docker.com | sh      # install Docker
cd /opt/crypto-trader
docker compose up -d --build                # build + start bot and website
```

That's it. The website is now at `http://SERVER_IP` from any device, and
`restart: unless-stopped` means both containers come back automatically after
crashes or server reboots.

Copying `user_data` carries over your paper-trading history (the trade
database lives in `user_data/`), so the bot continues where the PC left off.
Stop the local bot afterwards so two bots aren't paper trading in parallel.

## 4. Security notes

- The **dashboard website is read-only** — visitors can see stats but cannot
  control the bot. It's the only thing exposed to the internet (port 80).
- The **freqtrade API/web UI is not public.** To use the full freqUI control
  panel, open an SSH tunnel and browse to http://127.0.0.1:8080 locally:
  `ssh -L 8080:127.0.0.1:8080 root@SERVER_IP`
- Optional firewall: `ufw allow 22 && ufw allow 80 && ufw enable`
- If you ever go live with real API keys: keys must be trade-only
  (withdrawals disabled), and never commit them to git.

## 5. Day-2 operations

```bash
docker compose logs -f freqtrade        # watch the bot's log
docker compose restart freqtrade        # restart after editing a strategy
docker compose pull && docker compose up -d   # update freqtrade version
```

Optional niceties later: a $10/year domain pointed at the server IP, and
Caddy or nginx in front for free HTTPS.
