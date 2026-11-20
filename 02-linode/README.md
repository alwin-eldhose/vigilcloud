# Linode: your app running in Seattle

A Linode is a Linux virtual machine. Use one for a web app, API, bot, or worker. This lab runs the [workshop app](../demo/README.md), the same app you use on your laptop.

**You get:** an app that answers questions after you disconnect, with access limited by a firewall.
**Time:** allow 25 minutes, including about a minute while the Linode boots.
**Cost:** about $0.18 a day for a Nanode 1 GB. It bills until you delete it, even when powered off. The firewall is free.
**You need:** an active account, [setup](../00-setup/README.md) done, your inference key saved in `.env`, and an SSH key for logging in. Run every laptop command from the repo folder.

To try the app on your laptop first, run this and open http://localhost:8000. Ask a question, then press Ctrl+C in the terminal to stop it:
```bash
uv run demo/app.py
```

## 1. Create it

1. In [Cloud Manager](https://cloud.linode.com), Akamai's web console, click **Create**, then **Linode**.
2. Choose **Seattle, WA**, **Ubuntu 24.04 LTS**, and **Nanode 1 GB** on the **Shared CPU** tab.
3. Set **Linode Label** to `sea-<name>-web` with your first name in lowercase, such as `sea-ada-web`.
4. Set **Root Password** to a long password and save it. You need it if you use the browser console.
5. Print your public SSH key in your laptop terminal and copy the whole line:
```bash
cat ~/.ssh/id_ed25519.pub
```
6. Under **SSH Keys**, click **Add an SSH Key**. Set **Label** to `laptop`, paste the line into **SSH Public Key**, and click **Add Key**. Check the box next to your username in the table.
7. In **Assign Firewall**, choose **No firewall - traffic is unprotected (not recommended)** for now. You add one below before starting the app.
8. Open **Add User Data** and paste this block. It installs uv on first boot and turns off password login over SSH:
```yaml
#cloud-config
ssh_pwauth: false
disable_root: false
runcmd:
  - curl -LsSf https://astral.sh/uv/0.13.8/install.sh | env HOME=/root sh
```
9. Click **Create Linode**. It takes about a minute to show **Running**. While it starts, add the firewall below.

<details><summary>Same thing with the CLI</summary>

Set up the [Linode CLI](../00-setup/cli.md) first. This command sets a random root password that nobody sees, so the browser console login below will not work. It adds your SSH key and sends the same first-boot block from `cloud-init.yaml`. Type `NAME=`, then your first name in lowercase, and press Enter. Then run the second block:
```bash
NAME=PASTE_YOUR_NAME
```
```bash
linode-cli linodes create --label "sea-$NAME-web" --region us-sea --type g6-nanode-1 \
  --image linode/ubuntu24.04 --root_pass "$(openssl rand -base64 32)" \
  --authorized_keys "$(cat ~/.ssh/id_ed25519.pub)" \
  --metadata.user_data "$(base64 < 02-linode/cloud-init.yaml | tr -d '\n')" --text --format id,label,status,ipv4
```
</details>

### Add a firewall

A firewall controls which traffic reaches the Linode. This one allows SSH and the app from your current public IPv4 address. Everyone sharing that address can reach the app. It has no login and uses plain HTTP. Use practice data, and add a login and HTTPS before sharing it outside the workshop.

1. In your laptop terminal, print the address to allow. Copy the output, including `/32`, which means this one address:
```bash
echo "$(curl -s https://api.ipify.org)/32"
```
2. In Cloud Manager, select **Firewalls**, then **Create Firewall**. Choose **Custom Firewall** and set **Label** to `sea-<name>-fw`.
3. Keep **Default Inbound Policy** at **Drop** and **Default Outbound Policy** at **Accept**. Choose your Linode in **Linodes**, then click **Create Firewall**.
4. On its **Rules** page, click **Add an Inbound Rule**. Set **Label** to `ssh-and-web`, **Protocol** to **TCP**, and **Ports** to **Custom**. Enter `22, 80` in **Custom Port Range**.
5. In **Sources**, choose **IP / Netmask** or **IP / Netmask / Prefix List**, whichever appears. Paste the address from step 1 into **IP / Netmask**. Set **Action** to **Accept** and click **Add Rule**.
6. Click **Save Changes** before trying to connect. A firewall with no saved allow rule blocks SSH too.

When you change networks, repeat step 1 and edit the rule's source address. Use the Linode's IPv4 address for SSH and the browser. Ask a helper if the venue uses several public addresses and your connections still time out.

<details><summary>Same thing with the CLI</summary>

Type `NAME=`, then your first name in lowercase, and press Enter. Then run the second block from your laptop:
```bash
NAME=PASTE_YOUR_NAME
```
```bash
ID=$(linode-cli linodes list --label "sea-$NAME-web" --text --no-headers --format id)
MY_IP=$(curl -s https://api.ipify.org)
RULE='[{"label":"ssh-and-web","action":"ACCEPT","protocol":"TCP","ports":"22,80","addresses":{"ipv4":["'"$MY_IP"'/32"]}}]'
linode-cli firewalls create --label "sea-$NAME-fw" --rules.inbound "$RULE" \
  --rules.inbound_policy DROP --rules.outbound_policy ACCEPT --devices.linodes "$ID"
```
</details>

## 2. Connect

1. In your laptop terminal, type `IP=`, paste the Linode's IPv4 address after the `=`, and press Enter:
```bash
IP=PASTE_YOUR_LINODE_IP
```
2. Copy your settings, app, page, and service file. `scp` copies files over SSH, the connection used to log in to the Linode. If asked whether to continue connecting, type `yes`:
```bash
scp .env demo/app.py demo/index.html 02-linode/app.service root@$IP:
```
3. Log in. Commands now run on the Linode until you type `exit`:
```bash
ssh root@$IP
```

<details><summary>If SSH times out, check the firewall, then use the browser console in place of steps 2 and 3</summary>

1. In Cloud Manager, open the **...** menu at the top of your Linode's page and choose **Launch LISH Console**. LISH is a terminal in your browser. Log in as `root` with your root password. Nothing shows as you type it.
2. Download the app, page, service file, setup check, and settings template:
```bash
URL=https://github.com/akamai-developers/akamai-workshop-seattle-hackathon/raw/main
curl -fsSL --remote-name-all "$URL/check.py" "$URL/.env.example" "$URL/demo/app.py" "$URL/demo/index.html" "$URL/02-linode/app.service"
```
3. Run the check. At `key:`, paste your inference key and press Enter. It makes `.env` and ends with a model reply. Then continue at step 4 below:
```bash
python3 check.py
```
</details>

4. Wait for the first-boot setup to finish. You should see `status: done`, then the uv version:
```bash
cloud-init status --wait
uv --version
```

### Keep it running

On the Linode, install `app.service`. Linux uses it to start the app at boot and restart it if it stops. If `uv run app.py` is already running in a terminal, press Ctrl+C to stop that copy first:
```bash
cp app.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable app && systemctl restart app
journalctl -u app -n 20
```
The log should include `Uvicorn running on http://0.0.0.0:80`. The first start installs packages. If the line is missing, wait a few seconds and run `journalctl -u app -n 20` again. Read any error before continuing. If the log opens in a scrolling page, press `q` to return to the prompt.

## 3. Check it works

Disconnect from the Linode:
```bash
exit
```
In your browser, open `http://` followed by the Linode's IPv4 address. Continue past the browser's plain HTTP warning if it appears. You should see **Ask**, **Files**, and **History**. Leave **About the file** at **no file** and ask a question. An answer after you disconnect proves the service keeps the app running.

For the service settings, run this in your laptop terminal:
```bash
curl "http://$IP/health"
```
Without a database or bucket, you should see:
```text
{"inference":"configured","database":"not set","object_storage":"not set"}
```
`configured` means the model settings exist. The answer in the browser is the check that inference works.

## 4. Use it in your app

Edit `demo/app.py` or `demo/index.html` on your laptop. With `IP` still set, copy the files again and restart the app:
```bash
scp .env demo/app.py demo/index.html 02-linode/app.service root@$IP:
ssh root@$IP "systemctl restart app"
```
Reload the page. For errors, use `ssh root@$IP` and `journalctl -u app -n 20`. To add files or saved answers, follow [Connect the services](../demo/README.md#connect-the-services), then copy `.env` and restart again.

### Put your own code on it

1. Give your Python file a `# /// script` header like `demo/app.py`, with its packages in `dependencies`. Make it listen on `0.0.0.0` and port 80.
2. From your laptop, in the folder that holds your project folder, copy it with `scp -r my-app root@$IP:`, using your folder's name.
3. Edit `02-linode/app.service` on your laptop. Change `/root/app.py` at the end of `ExecStart` to your file's path, such as `/root/my-app/main.py`.
4. From the repo folder, copy it with `scp 02-linode/app.service root@$IP:`. Log in with `ssh root@$IP` and run both [Keep it running](#keep-it-running) commands again.

## Problems

| What you see | What to do |
|---|---|
| `Connection refused` just after creating the Linode | Wait a minute for it to boot. |
| SSH or the page times out | Check that the firewall allows your current public IPv4 address on ports 22 and 80 and that you clicked **Save Changes**. A new network needs a new source address. |
| SSH still times out but the firewall is correct | The venue may block port 22. Use the browser console in [Connect](#2-connect). |
| `Permission denied (publickey)` | The key's box was not checked, or the key belongs to another laptop. Recreate the Linode with the correct key, then attach the firewall to the new Linode. |
| `uv: command not found` on the Linode | Check `cloud-init status --wait`. If **User Data** was missing or changed, recreate the Linode with the supplied block and attach its firewall. |
| `Could not resolve host` or `Could not resolve hostname` | Set `IP` again to the Linode's IPv4 address. |
| The page fails, or an answer reports an error | Log in and read `journalctl -u app -n 20`. A `401` means the inference key in the server's `.env` is wrong. Copy the corrected settings and restart. |
| `[Errno 98] ... address already in use` | A copy started with `uv run app.py` may still use port 80. Stop it with Ctrl+C, then run `systemctl restart app`. |

## Delete it

1. In Cloud Manager, open **Linodes**. In your Linode's row, open **...**, then **Delete**. Type its label in **Linode Label** and click **Delete**. This stops its billing.
2. Open **Firewalls**. In your firewall's row, open **...**, then **Delete**. Confirm with **Delete Firewall**. Firewalls are free.

## More reading

- [Create a Linode](https://techdocs.akamai.com/cloud-computing/docs/create-a-compute-instance)
- [Create a Cloud Firewall](https://techdocs.akamai.com/cloud-computing/docs/create-a-cloud-firewall)
- [Access your system console using Lish](https://techdocs.akamai.com/cloud-computing/docs/access-your-system-console-using-lish)
- [How billing works](https://techdocs.akamai.com/cloud-computing/docs/understanding-how-billing-works)
