# Troubleshooting

These problems can show up in any lab. A problem inside one lab is in that lab's Problems table: [inference](../01-inference/README.md#problems), [Linode](../02-linode/README.md#problems), [database](../03-database/README.md#problems), [Object Storage](../04-object-storage/README.md#problems), [LKE](../05-lke/README.md#problems), and [CLI](../00-setup/cli.md#problems).

| What you see | What to do |
|---|---|
| Cloud Manager says **Your account is currently being reviewed.**, or the CLI says `Your account must be activated before you can use this endpoint` | A few new accounts wait for a manual review. Check your email for instructions. Meanwhile, do the [inference lab](../01-inference/README.md), which needs only the key, and pair with a teammate whose account works. |
| The signup form declines your card | Try another card, or PayPal. If every method fails, tell event staff. |
| `command not found` for `uv` right after installing uv | Open a new terminal window. On Windows, close Git Bash and open it again. |
| `Failed to spawn: check.py` or `No such file or directory` | The terminal is not in the repo folder. A new terminal starts in your home folder. Run `cd akamai-workshop-seattle-hackathon`, then the command again. |
| `... is not set. Add it to .env` while the line is in `.env` | Run the command from the `akamai-workshop-seattle-hackathon` folder. Check that the file is named `.env` and not `.env.txt`, which Notepad can add. Remove any quotes and any comment after the value. |
| You cannot find or open `.env` | It is in the repo folder. A file browser may hide a name that starts with a dot. From the repo folder, run `open -e .env` on macOS, `notepad .env` in Git Bash, `xdg-open .env` on Ubuntu, or `notepad.exe .env` in WSL. |
| A command is not found on Windows, or `python3` opens the Microsoft Store | Run every command in Git Bash, as [setup](../00-setup/README.md) says. Run Python files with `uv run`, such as `uv run check.py`. uv downloads Python 3.11 or newer if the laptop has none. |
| A connection times out on the venue Wi-Fi, but works on a phone hotspot | The venue network blocks that port. For SSH on port 22, see the Linode lab's Problems table. For a database, use the hotspot. |

## Still stuck

Ask a helper. Show the command you ran and the last lines of its output. Remove keys and passwords before sharing them.
