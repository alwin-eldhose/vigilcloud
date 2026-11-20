# Clean up

Delete what you made when you finish. Akamai charges by the hour for each Linode, LKE node, NodeBalancer, database, and volume until you delete it. A powered-off Linode still costs money. Object Storage costs $5 a month until you cancel it. Your event credit pays for them until the credit runs out.

## What bills

| Resource | Cost |
|---|---|
| Linode, Nanode 1 GB | $0.18 a day |
| Linode 2 GB, the LKE node | $0.43 a day |
| NodeBalancer, made by an LKE LoadBalancer Service | $0.36 a day |
| Managed PostgreSQL, smallest plan, 1 node | $0.58 a day |
| Object Storage, for the whole account | $5 a month, about $0.18 a day, until you cancel it |
| Block Storage volume | $0.10 per GB a month |

Free: Cloud Firewalls, VPCs, the standard LKE control plane, and API tokens. Your first Object Storage bucket or access key turns Object Storage on, and its monthly fee starts then. Inference costs your account nothing, because the key belongs to the event.

## Delete what you made

Each lab ends with a "Delete it" section. Follow it for every lab you did: [Linode](../02-linode/README.md#delete-it), [database](../03-database/README.md#delete-it), [Object Storage](../04-object-storage/README.md#delete-it), and [LKE](../05-lke/README.md#delete-it). For LKE, delete the Service before the cluster, so its NodeBalancer goes too.

Then check six places in Cloud Manager:

- [ ] **Linodes**: nothing labeled `sea-<name>-`.
- [ ] **Kubernetes**: no cluster of yours.
- [ ] **Databases**: no cluster of yours.
- [ ] **NodeBalancers**: none left from a deleted cluster.
- [ ] **Volumes**: none you made.
- [ ] **Object Storage**: no buckets of yours, and no keys of yours on the **Access Keys** tab.

<details><summary>With the Linode CLI, one script deletes what you labeled</summary>

`scripts/cleanup.sh` finds every Linode, firewall, database, LKE cluster, bucket, and Object Storage key whose label starts with your prefix. It needs the [Linode CLI](../00-setup/cli.md). Run it from the repo folder. Delete the LKE Service first, as Lab 05 shows, or its NodeBalancer keeps billing. Type `NAME=`, then your first name in lowercase, the one in your labels, and press Enter. Then run the second block. Your prefix is `sea-`, your name, and a dash, so `sea-ada-` never matches `sea-adam-`.

```bash
NAME=PASTE_YOUR_NAME
```
```bash
PREFIX="sea-$NAME-"
bash scripts/cleanup.sh "$PREFIX" --dry-run
bash scripts/cleanup.sh "$PREFIX"
```

The first command only lists. The second lists again, asks you to type the prefix, and deletes. The prefix needs at least 8 characters. If yours is shorter, run the script once for each full label, such as `sea-al-web`.

</details>

## Stop the Object Storage fee

Deleting buckets does not stop the $5 monthly fee. Cancelling Object Storage stops it. Cancelling also deletes every bucket and file in the account, so do it only if nothing else uses them. Select **Administration**, then **Account Settings**. In the Object Storage section, click **Cancel Object Storage** and confirm with your username. The cleanup script never does this.

## Revoke what you no longer need

- API token: click your username, select **API Tokens**, and revoke the token.
- Object Storage keys: revoke yours on the **Access Keys** tab, including the `linode-cli-` key the CLI made.
- Kubeconfig: delete the file. It stops working when the cluster is deleted.
- Inference key: event staff revoke every key after the event.

## More reading

- [Stop further billing](https://techdocs.akamai.com/cloud-computing/docs/stop-further-billing)
- [Cancel Object Storage](https://techdocs.akamai.com/cloud-computing/docs/cancel-object-storage)
