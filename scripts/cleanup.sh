#!/usr/bin/env bash
# Delete everything whose label starts with your prefix: Linodes, firewalls, databases,
# LKE clusters, buckets, and Object Storage keys. It lists them first and asks before it deletes.
#
#   bash scripts/cleanup.sh sea-ada- --dry-run   list only
#   bash scripts/cleanup.sh sea-ada-             list, ask you to type the prefix again, delete
#   bash scripts/cleanup.sh sea-ada- --yes       list and delete without asking
#
# Needs the Linode CLI with boto3 (00-setup/cli.md). Written for macOS bash 3.2 too, but not yet run there.
# It never cancels Object Storage, and it cannot find NodeBalancers or volumes, whose names are generated.
set -u

PREFIX=""
DRY_RUN=0
YES=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes) YES=1 ;;
    -*) echo "Unknown option: $arg"; exit 2 ;;
    *) PREFIX=$arg ;;
  esac
done

if [ ${#PREFIX} -lt 8 ]; then
  echo "Usage: bash scripts/cleanup.sh <prefix> [--dry-run] [--yes]"
  echo "The prefix needs at least 8 characters, such as sea-ada-, so it includes your name."
  exit 2
fi
case "$PREFIX" in *PASTE_YOUR*) echo "Put your own name in place of PASTE_YOUR_NAME in the prefix, then run this again."; exit 2 ;; esac
command -v linode-cli >/dev/null || { echo "linode-cli not found. See 00-setup/cli.md."; exit 2; }

CLUSTER=us-ord-10  # the Chicago endpoint, where Lab 04 makes its bucket
TAB=$(printf '\t')
FOUND=""
FAILED=0
cli() { linode-cli --suppress-warnings "$@"; }

# collect KIND COMMAND...: run a list command and keep the rows whose label starts with PREFIX.
# Each kept row is: KIND <tab> ID <tab> LABEL <tab> EXTRA
collect() {
  local kind=$1 out rows
  shift
  if ! out=$("$@" 2>&1); then
    echo "Could not list ${kind}s: $(printf '%s\n' "$out" | tail -n 1)"
    FAILED=1
    return
  fi
  rows=$(printf '%s\n' "$out" | awk -F '\t' -v p="$PREFIX" -v k="$kind" \
    'index($2, p) == 1 { print k "\t" $1 "\t" $2 "\t" $3 }')
  if [ -n "$rows" ]; then FOUND="$FOUND$rows"$'\n'; fi
}

collect "LKE cluster" cli lke clusters-list --text --no-headers --format id,label --all-rows
collect "Linode" cli linodes list --text --no-headers --format id,label --all-rows
collect "Firewall" cli firewalls list --text --no-headers --format id,label --all-rows
collect "Database" cli databases list --text --no-headers --format id,label,engine --all-rows

# Buckets come from the obj plugin, which prints "date time name" per bucket. The bucket name is its own ID.
if out=$(cli obj ls --cluster "$CLUSTER" --key-cleanup-enabled no 2>&1); then
  for name in $(printf '%s\n' "$out" | awk 'NF >= 3 { print $NF }'); do
    case "$name" in "$PREFIX"*) FOUND="${FOUND}Bucket${TAB}${name}${TAB}${name}${TAB}"$'\n' ;; esac
  done
else
  echo "Could not list buckets: $(printf '%s\n' "$out" | tail -n 1)"
  FAILED=1
fi

collect "Access key" cli object-storage keys-list --text --no-headers --format id,label --all-rows

if [ -z "$FOUND" ]; then
  echo "Nothing found with a label that starts with $PREFIX"
else
  echo "Found these, labels starting with $PREFIX:"
  printf '%s' "$FOUND" | awk -F '\t' '{ printf "  %-12s %-12s %s\n", $1, $2, $3 }'
fi

if [ "$DRY_RUN" -eq 1 ] || [ -z "$FOUND" ]; then
  [ "$DRY_RUN" -eq 1 ] && echo "Dry run. Nothing deleted."
  exit "$FAILED"
fi

if [ "$YES" -ne 1 ]; then
  printf 'Type the prefix again to delete all of these: '
  answer=""
  read -r answer < /dev/tty || true
  if [ "$answer" != "$PREFIX" ]; then
    echo "That does not match. Nothing deleted."
    exit 1
  fi
fi

# remove KIND ID LABEL EXTRA: the delete command for one row. EXTRA is the database engine.
remove() {
  case "$1" in
    "LKE cluster") cli lke cluster-delete "$2" ;;
    "Linode") cli linodes delete "$2" ;;
    "Firewall") cli firewalls delete "$2" ;;
    "Database") cli databases "$4-delete" "$2" ;;
    "Bucket") cli obj rb "$3" --recursive --cluster "$CLUSTER" --key-cleanup-enabled no ;;
    "Access key") cli object-storage keys-delete "$2" ;;
  esac
}

while IFS="$TAB" read -r kind id label extra; do
  [ -z "$kind" ] && continue
  if err=$(remove "$kind" "$id" "$label" "$extra" 2>&1); then
    echo "  deleted  $kind $label"
  else
    echo "  FAILED   $kind $label: $(printf '%s\n' "$err" | tail -n 1)"
    FAILED=1
  fi
done <<EOF
$FOUND
EOF

cat <<'EOF'

This script does not cover:
  - NodeBalancers and volumes. Their names are generated. Check both lists in Cloud Manager.
    Delete a Kubernetes LoadBalancer Service before its cluster, and its NodeBalancer goes with it.
  - The Object Storage fee, $5 a month until you cancel. Cancelling deletes every bucket in the
    account. To cancel, open Administration, then Account Settings. See docs/cleanup.md.
  - The key linode-cli obj made for itself, labeled linode-cli-. Revoke it on the Access Keys tab.
EOF
exit "$FAILED"
