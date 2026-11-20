# Optional: the Linode CLI

Every lab works in Cloud Manager, the Akamai Cloud web console. The Linode CLI does the same work from your terminal, in each lab's "Same thing with the CLI" block. Set it up here before you use one.

**Time:** 5 minutes.

## 1. Install it

```bash
uv tool install linode-cli --with boto3
```

`boto3` is for `linode-cli obj`, which creates buckets.

## 2. Create a token

1. Click your username at the top of [Cloud Manager](https://cloud.linode.com) and select **API Tokens**. A token is a password the CLI uses to act as your account.
2. Click **Create a Personal Access Token**.
3. Set **Label** to `sea-<name>-cli`, with your first name in lowercase letters a to z for `<name>`. Set **Expiry** to **In 1 month**, the shortest choice.
4. Set **Read/Write** for Databases, Firewalls, Kubernetes, Linodes, and Object Storage. Set **Read Only** for Account and NodeBalancers. Leave the rest at **No Access**.
5. Click **Create Token** and copy the token. Cloud Manager shows it once.

## 3. Configure the CLI

```bash
linode-cli configure --token
```

Paste the token when asked. Press Enter at each optional question after it. Every lab command sets its own region, plan, and image.

## 4. Check it works

```bash
linode-cli profile view --text --format username
```

You should see:

```text
username
<your-username>
```

## Problems

| What you see | What to do |
|---|---|
| `command not found` for `linode-cli` | Run `uv tool update-shell`, then open a new terminal. |
| `This plugin requires the 'boto3' module` | Run `uv tool install linode-cli --with boto3 --force`. |
| `linode-cli obj` says you are running without a configuration file | `LINODE_CLI_TOKEN` is set in your shell, maybe for another project. Run `unset LINODE_CLI_TOKEN`, then [Configure the CLI](#3-configure-the-cli). |
| `Your OAuth token isn't authorized to create Object Storage keys` | The token lacks Account Read Only. Make a new one as in [Create a token](#2-create-a-token), then [Configure the CLI](#3-configure-the-cli) again. |
| `Request failed: 401` | The token is wrong or expired. Make a new one as in [Create a token](#2-create-a-token). |

`linode-cli obj` makes its own access key the first time it runs, labeled `linode-cli-` plus your user and machine. Revoke it when you clean up.

## More reading

- [Get started with the Linode CLI](https://techdocs.akamai.com/cloud-computing/docs/getting-started-with-the-linode-cli)
- [Manage personal access tokens](https://techdocs.akamai.com/cloud-computing/docs/manage-personal-access-tokens)
