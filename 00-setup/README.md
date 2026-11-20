# Setup: account, tools, and your key

In the workshop, skip this page. [WORKSHOP.md](../WORKSHOP.md) has these steps at its top. Use this page when you start from a lab. The account is the slow part, so start it first.

**You get:** an Akamai Cloud account, git and uv on your laptop, the repo, ready for your key, and an SSH key.
**Time:** 15 minutes. A Mac that needs its developer tools can take 30 more. A manual review of your account, if you get one, has no set length.
**You need:** a laptop with macOS, Linux, or Windows, a phone for a text message, and a credit card, debit card, or PayPal.

## 1. Create your Akamai Cloud account

1. Open the signup link in the [README](../README.md). Accounts made through it get the event credit.
2. Enter your email, a username, and a password.
3. In **Verification**, enter your phone number.
4. Enter the code that arrives by text message.
5. Choose **Personal** for the account type.
6. In **Billing**, add a payment method. The form takes a credit card, a debit card, or PayPal. You are charged only when you create a paid service.
7. Click the link in the confirmation email. You land in Cloud Manager, the Akamai Cloud web console, at [cloud.linode.com](https://cloud.linode.com).

Most accounts work at once. A few wait for a manual review, and Cloud Manager shows **Your account is currently being reviewed.** until an email says the review is complete. While yours waits, finish the sections below, then do the [inference lab](../01-inference/README.md), which needs only your key. If it still waits when the workshop reaches the Linode part, follow along with a teammate whose account works.

## 2. Install git and uv

git copies this repo to your laptop. uv runs the Python files and installs what they need. Open the block for your laptop.

<details><summary>macOS</summary>

Open **Terminal**, in **Applications**, then **Utilities**. Run the first block. In the window that opens, click **Install**, and wait for it to finish, which can take up to 30 minutes. If it says the tools are already installed, that is fine. Then run the second block.
```bash
xcode-select --install
```
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Then press Cmd+N to open a new terminal window.

</details>

<details><summary>Ubuntu, Debian, or WSL</summary>

Open Terminal. WSL runs Linux inside Windows. If you already use WSL, open your WSL terminal. If you do not, use the Windows block below. On another Linux, install git and curl with its package manager instead of `apt`. Run the first block. It asks for your laptop password, and nothing shows as you type it. Then run the second block:
```bash
sudo apt update && sudo apt install -y git curl
```
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Then close the terminal and open it again.

</details>

<details><summary>Windows</summary>

1. Install [Git for Windows](https://git-scm.com/downloads/win) with the default options. It includes Git Bash.
2. Open **Git Bash**. Run every command in this repo in Git Bash.
3. Install uv:
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
4. Close Git Bash and open it again.

</details>

## 3. Clone the repo

Clone the repo, then move into the folder it makes. Run every command in this repo from that folder:
```bash
git clone https://github.com/akamai-developers/akamai-workshop-seattle-hackathon
cd akamai-workshop-seattle-hackathon
```

## 4. Check it works

1. Run the setup check. The first time, it makes your settings file, `.env`, and asks for your inference key:
```bash
uv run check.py
```
2. At `key:`, paste your key and press Enter. To paste, press Cmd+V on macOS, Ctrl+Shift+V on Linux, or Shift+Insert in Git Bash. On macOS and Linux, nothing shows as you paste. Event staff hand out the keys, and each starts with `sk_aka_`. If you have no key yet, press Enter alone.

Without a key, you should see:
```text
Checking your inference setup

  ok    .env made from .env.example
  Paste the key from event staff, then press Enter. Nothing shows as you paste.
  key:
  FAIL  no key was given, but git, uv, and the clone work
        fix: get your team's key from event staff, then run  uv run check.py  again
```
That result still proves git, uv, and the clone work. Get a key from staff and run the check again. With a key, the line after `key:` is `ok    AKAMAI_API_KEY saved in .env, 50 characters (value hidden)`. Four more `ok` lines follow. The last line is the model's reply. Any other `FAIL` line names the problem, and the `fix:` line under it says what to do. Other setup problems are in [troubleshooting](../docs/troubleshooting.md).

## 5. Make an SSH key

An SSH key logs you in to a Linode with no password. It is two files on your laptop. You paste the public one, `id_ed25519.pub`, into Cloud Manager when you create a Linode. The other file is private. Never share it.

1. Check for a key. The commands in this section are the same on macOS, Linux, and Windows. On Windows, run them in Git Bash:
```bash
ls ~/.ssh/id_ed25519.pub
```
If it prints the file's name, you have a key, so skip step 2.
2. Make a key:
```bash
ssh-keygen -t ed25519
```
It asks three questions. Press Enter at each one, so the key gets the usual name and no password of its own. If it asks `Overwrite (y/n)?`, type `n`. You already have a key.
3. Copy the public key when a lab asks for it. `cat ~/.ssh/id_ed25519.pub` prints it as one long line that starts with `ssh-ed25519`. Select the whole line and copy it, or let one of these commands copy it for you:

| Laptop | Command that copies the public key |
|---|---|
| macOS | `pbcopy < ~/.ssh/id_ed25519.pub` |
| Windows, in Git Bash | `clip < ~/.ssh/id_ed25519.pub` |
| Windows, in WSL | `clip.exe < ~/.ssh/id_ed25519.pub` |
| Linux | `cat ~/.ssh/id_ed25519.pub`, then select the line and press Ctrl+Shift+C |

## Your credentials

| Credential | What it is for | Where you get it |
|---|---|---|
| Inference key, `sk_aka_...` | Calling the models | Event staff, one per team |
| Cloud Manager login | Creating and deleting resources in the browser | Section 1 |
| SSH key | Logging in to your Linode | Section 5 |
| API token | The Linode CLI, which is optional | [cli.md](cli.md) |
| Object Storage access key | Your code reading and writing one bucket | [Lab 04](../04-object-storage/README.md) |
| Database password | Your code connecting to PostgreSQL | [Lab 03](../03-database/README.md) |

With your key saved, start `uv run demo/app.py` to download its packages, open http://localhost:8000, and ask a question. Press Ctrl+C in the terminal to stop it. Tell a helper if your account is still under review.

## Optional tools

- Only [Lab 05](../05-lke/README.md), the Kubernetes lab, needs [kubectl](https://kubernetes.io/docs/tasks/tools/), the command-line tool for Kubernetes.
- [Node.js](https://nodejs.org/en/download) 22 or newer runs `01-inference/chat.mjs`.

## More reading

- [Get started with Akamai Cloud](https://techdocs.akamai.com/cloud-computing/docs/getting-started)
- [Manage SSH keys](https://techdocs.akamai.com/cloud-computing/docs/manage-ssh-keys)
