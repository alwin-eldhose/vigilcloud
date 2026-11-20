# Database: PostgreSQL that keeps your data

Managed PostgreSQL is a PostgreSQL server that Akamai runs for you. Use it when your app needs data that outlives a restart: users, saved answers, scores, or embeddings, the lists of numbers in [Store embeddings](#store-embeddings).

**You get:** a PostgreSQL database in Seattle and a `notes` table that your code writes and reads.
**Time:** 10 minutes, plus about 8 minutes while the database starts. Create it first, then do something else.
**Cost:** $0.58 a day for the smallest plan with one node. It bills by the hour until you delete it.
**You need:** an active account, the [setup](../00-setup/README.md) done, and a terminal in the repo folder.

## 1. Create it

The database only accepts connections from addresses on its allow list. Your laptop's public address goes on it now.

1. In your laptop terminal, print your public addresses:
```bash
echo "$(curl -s https://api.ipify.org)/32"
curl -s -m 5 https://api6.ipify.org && echo /128
```
You should see your IPv4 address, then your IPv6 address, the long one with colons, if your network has one. With no IPv6, the second command takes 5 seconds and prints nothing. `/32` and `/128` mean this one address only:
```text
203.0.113.10/32
2001:db8::10/128
```
2. In [Cloud Manager](https://cloud.linode.com), the Akamai Cloud web console, select **Databases**, then **Create Database Cluster**.
3. Set **Cluster Label** to `sea-<name>-db` with your first name in lowercase letters a to z, for example `sea-ada-db`.
4. Choose **PostgreSQL** with the highest version number in **Database Engine**.
5. Choose **Seattle, WA** in **Region**.
6. Choose **Nanode 1 GB**, the smallest plan, on the **Shared CPU** tab of **Choose a Plan**.
7. Choose **1 Node**.
8. Choose **Specific Access (recommended)** in **Manage Access**. Paste the first line from step 1 into **Allowed IP Addresses or Ranges**. For a second line, click **Add an IP** and paste it into the new field.
9. Click **Create Database Cluster**. Its **Status** reads **Active** after about 6 minutes, and its host name works about 2 minutes after that.

<details><summary>Same thing with the CLI</summary>

Set up the [Linode CLI](../00-setup/cli.md) first. Type `NAME=`, then your first name in lowercase, the one in your labels, and press Enter. Then run the second block. The IPv6 address goes on the allow list only if your network has one:
```bash
NAME=PASTE_YOUR_NAME
```
```bash
MY_IP=$(curl -s https://api.ipify.org)
MY_IP6=$(curl -s -m 5 https://api6.ipify.org)
linode-cli databases postgresql-create --label "sea-$NAME-db" --region us-sea --type g6-nanode-1 \
  --engine postgresql/18 --cluster_size 1 --allow_list "$MY_IP/32" ${MY_IP6:+--allow_list} ${MY_IP6:+"$MY_IP6/128"} \
  --text --format id,label,status
```

</details>

## 2. Connect

1. When the **Status** reads **Active**, open your database in Cloud Manager. The **Summary** tab shows **Connection Details**.
2. Open `.env`, in the repo folder, in your code editor. If you cannot find it, see [troubleshooting](../docs/troubleshooting.md).
3. In **Connection Details**, click **Show** to see the password. Copy **Host**, **Port**, and **Password** into these lines in `.env`, then save the file. `PGUSER`, `PGDATABASE`, and `PGSSLMODE` are already set.
```text
PGHOST=the Host value
PGPORT=the Port value
PGPASSWORD=the Password value
```

<details><summary>For a framework that reads one DATABASE_URL</summary>

Build it from the same values. If the password has characters such as `@` or `/`, URL-encode them.
```text
DATABASE_URL=postgresql://akmadmin:PASSWORD@HOST:PORT/defaultdb?sslmode=require
```

</details>

## 3. Check it works

When the **Status** has read **Active** for about 2 minutes, run:
```bash
uv run 03-database/db.py
```

You should see the row it wrote, with your date and time, in UTC:
```text
  1  2026-11-12 23:51  Hello from Seattle
```

Run it again with a note in quotes, such as `uv run 03-database/db.py "Our team is Rain City"`. Every run adds a row, and the rows survive restarts.

## 4. Use it in your app

`load_dotenv` copies the `PG` lines from `.env` into the environment, and `psycopg` reads them from there. These lines connect and query:

```python
# /// script
# dependencies = ["psycopg[binary]>=3.3", "python-dotenv>=1.2.4"]
# ///
import psycopg
from dotenv import load_dotenv

load_dotenv(override=True)
with psycopg.connect(connect_timeout=10) as conn:
    rows = conn.execute("select id, body from notes").fetchall()
```

### Let your Linode in

This part needs the Linode from [Lab 02](../02-linode/README.md), with uv installed. A Linode has its own addresses, so they need their own lines on the allow list. Akamai adds LKE nodes for you, usually within 10 minutes. If a pod still cannot connect after 15 minutes, add the node's address the same way.

1. In Cloud Manager, open the **Networking** tab of your database and click **Manage Access**.
2. Click **Add Another IP** or **Add an IP**, whichever shows, and paste the Linode's IPv4 address from its page. The allow list takes a plain address or one that ends in `/32` or `/128`. Add the Linode's IPv6 address the same way. Click **Update Access Controls**.
3. In your laptop terminal, in the repo folder, run `db.py` on the Linode. Type `IP=`, paste the Linode's IPv4 address right after the `=`, and press Enter. Then run the second block:
```bash
IP=PASTE_YOUR_LINODE_IP
```
```bash
scp .env 03-database/db.py root@$IP:
ssh root@$IP "/root/.local/bin/uv run db.py"
```
You should see your rows, read from the Linode.

### Store embeddings

An embedding is a list of numbers, also called a vector, that stands for the meaning of a text. Texts with similar meanings get similar lists. `vectors.py` embeds three sentences with `EMBEDDING_MODEL`, stores them in a `vector` column from pgvector, the PostgreSQL extension for vectors, and ranks them against a question. It needs your key in `.env` too, which `uv run check.py` saves.
```bash
uv run 03-database/vectors.py
```

You should see the question, then the three sentences with a distance each, smallest first, close to these. A smaller distance means a closer meaning:
```text
Closest to: How big can my team be?

0.154  Teams can have up to three people.
0.584  The build day ends with demos at the front of the room.
0.600  Delete your Linodes and databases when you finish, or they keep billing.
```

There is no index on the vectors. pgvector stores vectors of up to 16,000 numbers but indexes at most 2,000, and this model returns 4,096. Without an index, PostgreSQL compares the question with every row, which is fine for a few thousand rows.

## Problems

| What you see | What to do |
|---|---|
| `connection timeout expired` | Your address is not on the allow list. It changes when you change networks. Print your addresses again with the commands in [Create it](#1-create-it), and add them under **Networking**. |
| It works at the venue but times out at home | Everyone on the venue Wi-Fi shares one public address, so the allow list holds the venue's address. Add your home address too. The password still protects the database. |
| Every connection waits about 10 seconds, then works | The machine tries IPv6 first, and only its IPv4 address is on the allow list. Add its IPv6 address too. Run the second command in [Create it](#1-create-it) on a laptop, or copy it from the Linode's page. |
| `failed to resolve host` | A new database's host name starts resolving about 2 minutes after the status turns **Active**. Wait, then run it again. |
| `password authentication failed` | Copy the password again with **Show**. Check for a stray space at the end of the line in `.env`. |
| `expected 4096 dimensions, not 1024` | `EMBEDDING_MODEL` changed after `docs` was created. Change the table name `docs` in all three SQL strings in `vectors.py`, so each model gets its own table. |

## Delete it

Deleting the database deletes its data and stops its billing.

1. Open **Databases** in Cloud Manager and select your database.
2. Open the **Settings** tab. Under **Delete the Cluster**, click **Delete Cluster**.
3. Type the cluster's name in **Cluster Name**, then click **Delete Cluster**.

## More reading

- [Create and manage database clusters](https://techdocs.akamai.com/cloud-computing/docs/aiven-manage-database)
- [PostgreSQL on Akamai Cloud](https://techdocs.akamai.com/cloud-computing/docs/aiven-postgresql)
- [pgvector](https://github.com/pgvector/pgvector)
