# Workshop app: questions, files, and saved answers

This is the app used throughout the workshop and in Lab 02. Run it on your laptop, put it on a Linode, then add files and saved answers when your project needs them. You can change it for your own project.

**Time:** 5 minutes on your laptop, plus Labs 03 and 04 to connect the database and the bucket.
**You need:** the [setup](../00-setup/README.md) done with your key saved, and a terminal in the repo folder.

Your browser sends requests to `demo/app.py`, which runs on your laptop, a Linode, or LKE. The app uses these services:

| Service | What it does | When it is on |
|---|---|---|
| Akamai Cloud Inference | Answers the question | Always |
| Managed PostgreSQL | Saves each question and answer | When `PGHOST` is set |
| Object Storage | Holds the uploaded text files | When `OBJ_BUCKET` is set |

Only inference is required. The page shows which services are connected, and links to the lab for each one that is not.

The app has no login. Anyone who can reach it can spend your key's quota, read saved answers, and read or upload files when those services are connected. Lab 02 limits access with a firewall, but people sharing an allowed address can still use the app. Use practice data. Add a login and HTTPS before sharing it outside the workshop, and delete resources when you finish.

## Run it on your laptop

```bash
uv run demo/app.py
```

The first start downloads its packages, which can take a minute. Wait for the `Uvicorn running` line, then open http://localhost:8000. With no `PORT` set, only your laptop can open the app. You should see three badges at the top: `inference: configured`, `database: not set`, and `object storage: not set`. Ask a question to see an answer.

## Connect the services

You can add either service first. Do both to follow the full demonstration.

1. For saved answers, do [Lab 03](../03-database/README.md) through "Connect", so the `PG` lines in `.env` are filled in. For an app on a Linode, also add that Linode's IPv4 and IPv6 addresses under "Let your Linode in".
2. For uploads, do [Lab 04](../04-object-storage/README.md) through "Connect", so the `OBJ` lines in `.env` are filled in.
3. On your laptop, press Ctrl+C, then run `uv run demo/app.py` again. On a Linode, copy the updated `.env` and restart as shown below. Each service you added should read `connected`. Inference still reads `configured`. Ask a question to check that it works.
4. Upload [volunteer-handbook.txt](volunteer-handbook.txt) from the `demo` folder in the **Files** panel. Its event details are made up for practice.
5. Choose that file under **About the file**.
6. Ask "Where should I send someone who needs a quiet room?" Compare the answer with the file. With PostgreSQL connected, the question and answer appear under **History**.

Then ask "Who has parking passes?" The file does not say. Check whether the model admits that or invents an answer. Restart the app and reload the page to check that the file and saved answers remain.

A badge that starts with `error:` names the problem. A database timeout means your address is not on the database allow list, the addresses it accepts. Lab 03 shows how to add it.

## Run it on a Linode

Part 2 of the [workshop](../WORKSHOP.md) puts the app on a Linode as a service. [Lab 02](../02-linode/README.md) has the same steps. To copy changes to its files or settings, use the commands below. In your laptop terminal, in the repo folder, type `IP=`, paste the Linode's IPv4 address after the `=`, and press Enter:

```bash
IP=PASTE_YOUR_LINODE_IP
```
```bash
scp .env demo/app.py demo/index.html 02-linode/app.service root@$IP:
ssh root@$IP "systemctl restart app"
```

Then reload the page at `http://` and your IP. For errors, log in with `ssh root@$IP` and run `journalctl -u app -n 20`.

## Run it on LKE

This is optional for teams that already use Kubernetes. The workshop hour uses one Linode.

`demo/Dockerfile` builds the image. Do [Lab 05](../05-lke/README.md) through "Check it works", then every step of "Run your own image" there. Its step 1 builds this image, and the Deployment sets `PORT=80`.

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/` | The page |
| GET | `/health` | Each service as `not set`, `configured`, `connected`, or `error: <reason>`. Inference says `configured`, because a check would spend tokens |
| POST | `/ask` | Body `{"question": "...", "file": "notes.txt"}`, with `file` optional. Returns `{"answer": "...", "saved": true}` |
| GET | `/history` | The last 20 questions, newest first. Empty without a database |
| GET | `/files` | The files in the bucket. Empty without a bucket |
| POST | `/files` | Upload one text file as multipart form data, up to 1 MB |

The model sees at most the first 20,000 characters of one selected text file. The app creates the `questions` table on first use. For searching many documents by meaning, see [Store embeddings](../03-database/README.md#store-embeddings).
