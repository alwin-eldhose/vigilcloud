# Workshop: getting started with Akamai Cloud

Follow this page in order. You will run an app on your laptop, then on Akamai Cloud.

| When | What to do |
|---|---|
| 0 to 5 | Watch the demo |
| 5 to 12 | Run the app locally |
| 12 to 35 | Put it on Akamai Cloud |
| 35 to 45 | Watch files and saved answers work |
| 45 to 50 | Choose your project |
| 50 to 55 | Review judging, help, and cleanup |
| 55 to 60 | Questions and catch-up |

## Set up: before the hour

Allow 15 minutes, or up to 45 on a Mac. If you are already set up, go to [See the app](#see-the-app-minutes-0-to-5).

### 1. Create your Akamai Cloud account

[Sign up for $300 in credit](https://login.linode.com/signup?promo=akm-eve-git-bell-300-103126-W204). You need a phone and a payment method. Choose **Personal**, verify your phone, and confirm your email.

Check: you can sign in to [Cloud Manager](https://cloud.linode.com). If your account is under review, continue setup and use a teammate's active account for Part 2.

### 2. Install git and uv

Open the instructions for your laptop.

<details><summary>macOS</summary>

Open **Terminal**. Install the developer tools and wait for them to finish. Skip this if already installed:
```bash
xcode-select --install
```
Then install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Press Cmd+N to open a new terminal.
</details>

<details><summary>Ubuntu, Debian, or WSL</summary>

In Terminal, install git and curl. It asks for your laptop password:
```bash
sudo apt update && sudo apt install -y git curl
```
Then install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Close Terminal and open it again.
</details>

<details><summary>Windows</summary>

Install [Git for Windows](https://git-scm.com/downloads/win) with the default options. Open **Git Bash** and install uv:
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Close Git Bash and open it again. Use it for every laptop command below.
</details>

### 3. Get this repo

On your laptop:
```bash
git clone https://github.com/akamai-developers/akamai-workshop-seattle-hackathon
cd akamai-workshop-seattle-hackathon
```
Run the remaining laptop commands from this folder.

### 4. Make an SSH key

An SSH key lets your laptop log in to the Linode without a password. On your laptop, check for an existing key:
```bash
ls ~/.ssh/id_ed25519.pub
```
If the file is missing, run this and press Enter at each prompt. If asked to overwrite a key, answer `n`:
```bash
ssh-keygen -t ed25519
```
Get your team's inference key from staff. This key lets the app call the models.

## See the app: minutes 0 to 5

Watch the instructor upload a practice handbook, ask a question, and show the saved answer.

| Service | What it does |
|---|---|
| Linode | Runs the app on a Linux server |
| Inference | Answers the question |
| Object Storage | Keeps the handbook |
| PostgreSQL | Saves past questions and answers |

## Part 1. Run it locally: minutes 5 to 12

1. On your laptop, check setup. Paste your inference key when asked. On macOS and Linux, nothing shows as you paste:
```bash
uv run check.py
```
2. On your laptop, start the app:
```bash
uv run demo/app.py
```
3. Wait for `Uvicorn running` in the terminal, then open http://localhost:8000. Leave **About the file** at **no file**. Ask a question, then change it and ask again.
4. Return to your laptop terminal and press Ctrl+C to stop the app.

Check: you received an answer and can type in the terminal again.

<details><summary>Help with the key or app</summary>

- Paste with Cmd+V on macOS, Ctrl+Shift+V on Linux, or Shift+Insert in Git Bash. On macOS and Linux, the key stays hidden.
- If the check prints `FAIL`, follow its `fix:` line. A saved key is not requested again.
- The first app start installs packages. Wait for `Uvicorn running` before opening the page.
- `database: not set` and `object storage: not set` are expected. You add those later. `inference: configured` alone does not prove a model call works.
- The model call is `client.chat.completions.create` in [demo/app.py](demo/app.py). [Lab 01](01-inference/README.md) has more examples.
</details>

## Part 2. Put it on Akamai Cloud: minutes 12 to 35

Run the same app on a Linode. The plan costs about $0.18 a day until deleted.

### Create the Linode

1. In [Cloud Manager](https://cloud.linode.com), choose **Create**, then **Linode**. Use these settings:

| Field | Value |
|---|---|
| Region | Seattle, WA |
| Linux Distribution | Ubuntu 24.04 LTS |
| Plan | Shared CPU, Nanode 1 GB |
| Linode Label | `sea-<name>-web`, using your first name in lowercase |
| Root Password | A long password. Save it for the browser console |
| Assign Firewall | No firewall - traffic is unprotected (not recommended). Add one below |

2. On your laptop, copy the public key printed by this command:
```bash
cat ~/.ssh/id_ed25519.pub
```
3. In **SSH Keys**, click **Add an SSH Key**. Set **Label** to `laptop` and paste into **SSH Public Key**. Click **Add Key**, then check the box next to your username.
4. In **Add User Data**, paste this block:
```yaml
#cloud-config
ssh_pwauth: false
disable_root: false
runcmd:
  - curl -LsSf https://astral.sh/uv/0.13.8/install.sh | env HOME=/root sh
```
5. Click **Create Linode**. Add the firewall while it starts.

Check: the Linode shows **Running** after about a minute.

### Add a firewall

Allow SSH and the app from your current network address.

1. On your laptop, copy the output, including `/32`:
```bash
echo "$(curl -s https://api.ipify.org)/32"
```
2. In Cloud Manager, open **Firewalls**, then **Create Firewall**. Choose **Custom Firewall**:

| Field | Value |
|---|---|
| Label | `sea-<name>-fw` |
| Default Inbound Policy | Drop |
| Default Outbound Policy | Accept |
| Linodes | Your `sea-<name>-web` Linode |

3. Click **Create Firewall**. On **Rules**, click **Add an Inbound Rule**:

| Field | Value |
|---|---|
| Label | `ssh-and-web` |
| Protocol | TCP |
| Ports | Custom |
| Custom Port Range | `22, 80` |
| Sources | IP / Netmask, or IP / Netmask / Prefix List |
| IP / Netmask | The address you copied, including `/32` |
| Action | Accept |

4. Click **Add Rule**, then **Save Changes**.

Check: the rule is saved. People sharing this address can use the app. It has no login, so use practice data.

### Copy the app and keep it running

1. On your laptop, set `IP` to the IPv4 address shown on your Linode's page. Put that address in place of `PASTE_YOUR_LINODE_IP`:
```bash
IP=PASTE_YOUR_LINODE_IP
```
2. On your laptop, copy the files. Type `yes` if asked to continue connecting:
```bash
scp .env demo/app.py demo/index.html 02-linode/app.service root@$IP:
```
3. From your laptop, log in to the Linode:
```bash
ssh root@$IP
```
4. On the Linode, wait for setup to finish:
```bash
cloud-init status --wait
uv --version
```
5. On the Linode, start the app as a service so it keeps running:
```bash
cp app.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable app && systemctl restart app
journalctl -u app -n 20
```
Wait for `Uvicorn running` in the log. Run `journalctl -u app -n 20` again if packages are still installing.
6. On the Linode, disconnect:
```bash
exit
```
7. Open `http://` followed by your Linode's IPv4 address. Continue past the plain HTTP warning if shown. Ask a question.

Check: the app answers after you disconnect.

<details><summary>Help connecting or starting the app</summary>

- SSH timeout: check the firewall address, ports `22, 80`, and **Save Changes**. If the venue blocks SSH, use [the browser console](02-linode/README.md#2-connect), then return to step 4 above.
- App error: log in with `ssh root@$IP` and read `journalctl -u app -n 20`. Press `q` if the log opens in a scrolling page.
- More fixes are in [Lab 02](02-linode/README.md#problems).
</details>

<details><summary>Update the app during build time</summary>

Edit `demo/app.py` or `demo/index.html` on your laptop. With `IP` still set, run:
```bash
scp .env demo/app.py demo/index.html 02-linode/app.service root@$IP:
ssh root@$IP "systemctl restart app"
```
Reload the page. Copy the updated `.env` whenever you add a service. Keep keys private. Add a login and HTTPS before sharing the app outside the workshop.
</details>

## Part 3. Add files and saved answers: minutes 35 to 45

Watch the instructor upload a file, check answers against it, and restart the app to show that its history remains. Your next steps are [Object Storage](04-object-storage/README.md), [PostgreSQL](03-database/README.md), and [connecting them to the app](demo/README.md#connect-the-services).

## Part 4. Choose your project: minutes 45 to 50

Write these with your team, then choose your first change and [next lab](docs/services.md):

- We help [person] do [task].
- The model helps by [what it does].
- We use [service] because [what the app needs].
- Our demo will show [a useful result].

## Part 5. Continue building: minutes 50 to 55

- [Judging](docs/judging.md): 40% other services, 20% inference, 20% usefulness, 20% creativity. Explain your choices. More services do not automatically mean a higher score.
- Help: ask a helper or open [troubleshooting](docs/troubleshooting.md). Get the submission link from event staff.
- [Cleanup](docs/cleanup.md): keep resources for build time, then delete them. A stopped Linode still bills. Deleting buckets does not cancel Object Storage.

## Questions and catch-up: minutes 55 to 60

Ask a helper about any missed step. Confirm that your app answers and your team knows what to build next.
