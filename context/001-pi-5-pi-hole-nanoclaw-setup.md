<overview>
The user's goal was to set up a Raspberry Pi 5 as a home server running Pi-hole (DNS ad blocker), Unbound (recursive DNS resolver), Tailscale (VPN for remote access), and NanoClaw (AI agent via Telegram using Azure OpenAI GPT-4o via LiteLLM proxy). The approach was fully remote — identifying hardware, flashing SD cards, configuring the Pi over SSH, and installing/configuring all services. A major challenge throughout was unreliable SD card readers/adapters causing repeated flash failures before a working setup was achieved.
</overview>

<history>

1. **User wanted to access micro SD card in laptop SD slot**
   - Detected Realtek PCIE CardReader (OK status) but card not showing up
   - Multiple rescan attempts failed — card not detected
   - Eventually detected via USB card reader as 125GB exFAT drive

2. **User wanted to flash Raspberry Pi OS for Pi-hole + Unbound + Tailscale**
   - Original card was 125GB, USB-C adapter — write verification consistently failed
   - Identified correct image: `2025-12-04-raspios-trixie-arm64-lite.img.xz` (in Downloads, 487MB, arm64 for Pi 5)
   - Multiple flash attempts (Pi Imager, balenaEtcher, Rufus) all failed due to unreliable USB card reader
   - One balenaEtcher flash succeeded (2 partitions visible: 512MB FAT32 + 2.3GB ext4), but Windows couldn't mount boot partition to add SSH/WiFi config
   - Manually wrote `user-data`, `network-config`, and `ssh` cloud-init files to boot partition (E:)
   - Pi booted (fan whirred) but couldn't connect to WiFi — cloud-init config not applied correctly

3. **User switched to Pi 5 with new 64GB SD card and new card reader**
   - Pi Imager flash succeeded (2 correct partitions visible)
   - Pi Imager pre-configured: hostname=`rohan-pi-hole`, user=`rohan`, password=`Kabir@1Arrin@2`, WiFi=`checkWifi` (password: `Front-Back-Ahead`), SSH enabled
   - Pi found on network at `192.168.1.50` (hostname: `rohan-pi-hole`)
   - SSH working successfully

4. **Installed Pi-hole**
   - `apt update && apt upgrade` completed
   - Pi-hole installer failed interactively (non-TTY), fixed by pre-creating `/etc/pihole/setupVars.conf` via `nano` directly on Pi
   - Pi-hole v6.4 installed successfully

5. **Installed and configured Unbound**
   - `sudo apt install unbound -y` succeeded
   - Config written to `/etc/unbound/unbound.conf.d/pi-hole.conf`
   - Tested with `dig pi-hole.net @127.0.0.1 -p 5335` — resolved correctly
   - Pi-hole configured to use Unbound: `sudo pihole-FTL --config dns.upstreams '["127.0.0.1#5335"]'`
   - `sudo systemctl restart pihole-FTL` applied the change

6. **Installed Tailscale**
   - `curl -fsSL https://tailscale.com/install.sh | sh` then `sudo tailscale up`
   - Tailscale IP: `100.112.209.68`
   - Pi is `rohan-pi-hole` on Tailscale network

7. **Installed NanoClaw (AI agent)**
   - User requested NanoClaw instead of OpenClaw
   - Installed Node.js v22, Docker, build-essential
   - Cloned `https://github.com/qwibitai/nanoclaw.git` to `~/nanoclaw`
   - `bash setup.sh` succeeded (bootstrap)

8. **Configured Azure OpenAI via LiteLLM proxy**
   - User has Azure AI Foundry with GPT-4o deployed
   - Azure endpoint: `https://ai-rohanreddy6652ai346568304857.cognitiveservices.azure.com/`
   - API Key: `<REDACTED_AZURE_API_KEY>`
   - Deployments: `gpt-4o` (2024-11-20) and `gpt-4o-2` (2024-08-06)
   - Installed LiteLLM in `/opt/litellm` venv, created config at `/opt/litellm/config.yaml`
   - LiteLLM running as systemd service on port 4000, health check passes
   - NanoClaw `.env` set with `ANTHROPIC_BASE_URL=http://localhost:4000` to route through LiteLLM

9. **Set up Telegram channel for NanoClaw**
   - Bot: `@mera_chot_bot`, token: `8772822984:AAGWCjezNGfXMpv0x7qU4xyl-_dJM7JN9xc`
   - Merged Telegram skill via `git remote add telegram https://github.com/qwibitai/nanoclaw-telegram.git`
   - Resolved merge conflicts (package-lock.json, package.json, badge.svg)
   - `npm install && npm run build` succeeded
   - Chat registered: user Rohan, chat ID `1419669711`, folder `telegram_main`, no trigger required
   - NanoClaw started manually (`npm start`), connected to Telegram, sent first response (229 chars)
   - Error encountered: `invalid model name in model=claude-sonnet-4-6` — LiteLLM didn't have that model mapped
   - Fixed: updated LiteLLM config to map `claude-sonnet-4-6`, `claude-3-5-sonnet-20241022`, and `claude-3-7-sonnet-20250219` all to Azure GPT-4o
   - Was in process of installing NanoClaw as systemd service when compaction occurred

10. **Removed Linux partition from laptop**
    - Deleted 46.29GB Linux partition (Drive L:, Partition 4 on Disk 0)
    - Extended C: from 341.95GB → 464GB

11. **Formatted SD cards for Tapo camera**
    - 125GB card formatted as exFAT (FAT32 not supported >32GB in Windows natively)
    - 32GB card was corrupted from repeated Pi flashing attempts
    - Tiny (~32MB) card was faulty/dead

</history>

<work_done>

Files created/modified on Pi:
- `/etc/pihole/setupVars.conf` — Pi-hole pre-config (interface, DNS, web UI settings)
- `/etc/unbound/unbound.conf.d/pi-hole.conf` — Unbound config listening on 127.0.0.1:5335
- `/opt/litellm/config.yaml` — LiteLLM proxy config mapping Claude model names → Azure GPT-4o
- `/etc/systemd/system/litellm.service` — LiteLLM systemd service (enabled, running)
- `/home/rohan/nanoclaw/.env` — NanoClaw env: Anthropic base URL → LiteLLM, Telegram token
- `/home/rohan/nanoclaw/data/env/env` — Copy of .env for container runtime
- `~/.nanoclaw/config.json` — Azure provider config (may be unused now that LiteLLM handles it)

Work completed:
- [x] Pi OS flashed and booted
- [x] SSH access working (passwordless with key at `C:\Users\rohan\.ssh\id_ed25519`)
- [x] Pi-hole v6.4 installed and running
- [x] Unbound installed and resolving on port 5335
- [x] Pi-hole configured to use Unbound upstream
- [x] Tailscale connected (IP: 100.112.209.68)
- [x] Docker + Node.js v22 installed
- [x] NanoClaw cloned and built
- [x] Telegram skill merged and built
- [x] LiteLLM proxy running as service (port 4000, Azure GPT-4o backend)
- [x] NanoClaw Telegram chat registered (chat ID: 1419669711)
- [x] NanoClaw started and sent first Telegram response
- [x] LiteLLM updated with all Claude model name variants
- [ ] NanoClaw systemd service installation (in progress when compacted)

</work_done>

<technical_details>

- **Pi hardware**: Raspberry Pi 5, 64GB SD card, connected via WiFi (`checkWifi`, GB region)
- **SD card flashing issues**: USB-C adapter and old USB reader both failed — "The volume does not contain a recognized file system". New USB card reader fixed it. Pi Imager verification always failed but writes were actually correct (check for 2 partitions: 512MB FAT32 + ~2GB ext4)
- **Cloud-init vs Raspberry Pi Imager**: The `2025-12-04-raspios-trixie-arm64-lite.img.xz` uses cloud-init (`user-data`, `network-config` files) not the traditional `wpa_supplicant.conf`/`ssh` approach. Pi Imager handles this automatically.
- **Pi-hole v6 differences**: `pihole restartdns` and `pihole -g` commands changed. Use `sudo systemctl restart pihole-FTL` and `sudo pihole-FTL --config dns.upstreams` instead.
- **NanoClaw architecture**: Node.js AI agent that spawns Docker containers per conversation. Uses Anthropic Claude SDK internally. LiteLLM proxy intercepts Anthropic API calls and routes to Azure OpenAI.
- **LiteLLM model name mapping**: NanoClaw requests specific Claude model names (`claude-sonnet-4-6`, `claude-3-5-sonnet-20241022`, `claude-3-7-sonnet-20250219`). All must be mapped in LiteLLM config to Azure GPT-4o deployment.
- **SSH key auth**: Key at `C:\Users\rohan\.ssh\id_ed25519` (no passphrase), public key in Pi's `~/.ssh/authorized_keys`. SSH config at `C:\Users\rohan\.ssh\config` maps `192.168.1.50` to use this key.
- **Heredoc issue**: SSH heredoc commands get mangled in PowerShell. Workaround: write files locally and SCP them to Pi.
- **NanoClaw Telegram skill**: Applied via `git merge telegram/main` from remote `https://github.com/qwibitai/nanoclaw-telegram.git`. Conflicts resolved by taking `--theirs` for package files.
- **Pi-hole web admin**: accessible at `http://192.168.1.50/admin`
- **LiteLLM health endpoint**: `http://192.168.1.50:4000/health`
- **Azure subscription**: Visual Studio Professional (cb15c9de-a57f-4a7a-8b1c-4a070c319ad6), tenant 7a082108-90dd-41ac-be41-9b8feabee2da, resource group `DefaultResourceGroup-NEU`

</technical_details>

<important_files>

- `/opt/litellm/config.yaml` (Pi)
  - Maps Claude model names to Azure GPT-4o
  - Must include: `claude-sonnet-4-6`, `claude-3-5-sonnet-20241022`, `claude-3-7-sonnet-20250219`
  - Restart with: `sudo systemctl restart litellm`

- `/home/rohan/nanoclaw/.env` (Pi)
  - Contains: `ANTHROPIC_API_KEY=dummy-key`, `ANTHROPIC_BASE_URL=http://localhost:4000`, `ASSISTANT_NAME=nanoclaw`, `TELEGRAM_BOT_TOKEN=8772822984:AAGWCjezNGfXMpv0x7qU4xyl-_dJM7JN9xc`
  - Must be synced to `data/env/env` after any change

- `/etc/systemd/system/litellm.service` (Pi)
  - LiteLLM service definition, enabled and running
  - ExecStart: `/opt/litellm/bin/litellm --config /opt/litellm/config.yaml --port 4000`

- `/etc/unbound/unbound.conf.d/pi-hole.conf` (Pi)
  - Unbound listens on 127.0.0.1:5335
  - Pi-hole upstream DNS set to 127.0.0.1#5335

- `C:\Users\rohan\.ssh\id_ed25519` (Laptop)
  - SSH key for passwordless Pi access
  - No passphrase

</important_files>

<next_steps>

Immediate next step (was in progress):
- Install NanoClaw as systemd service so it auto-starts on reboot:
  ```
  scp nanoclaw.service rohan@192.168.1.50:/tmp/nanoclaw.service
  ssh rohan@192.168.1.50 "sudo cp /tmp/nanoclaw.service /etc/systemd/system/nanoclaw.service && sudo systemctl daemon-reload && sudo systemctl enable nanoclaw && sudo systemctl start nanoclaw"
  ```
  Service file content:
  ```ini
  [Unit]
  Description=NanoClaw AI Agent
  After=network.target litellm.service
  
  [Service]
  WorkingDirectory=/home/rohan/nanoclaw
  ExecStart=/usr/bin/node dist/index.js
  Restart=always
  User=rohan
  Environment=HOME=/home/rohan
  
  [Install]
  WantedBy=multi-user.target
  ```

- Verify NanoClaw responds correctly in Telegram with Azure GPT-4o (test by sending a message to @mera_chot_bot)
- Consider setting Pi's IP as static on router to avoid IP change
- Optionally configure Pi-hole as DNS server on router so all home devices use it

</next_steps>