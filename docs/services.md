# Which service do I need?

Find your need in the left column, then open the lab. A row with no lab links to TechDocs, Akamai's documentation site. Create everything in Seattle, `us-sea`, except Object Storage buckets, which go in Chicago, `us-ord`.

| I need | Service | Start here | When to use it |
|---|---|---|---|
| A model that answers, calls tools, embeds text, or reads images | Akamai Cloud Inference | [Lab 01](../01-inference/README.md) | Any AI feature. Your team's key costs your account nothing |
| A server for my app | Linode | [Lab 02](../02-linode/README.md) | One web app, API, bot, or worker. Start here if unsure |
| Several containers, or Kubernetes I already know | LKE | [Lab 05](../05-lke/README.md) | Teams fluent in Kubernetes. Everyone else uses one Linode |
| Data that survives a restart, or vector search | Managed Databases, PostgreSQL | [Lab 03](../03-database/README.md) | Users, history, scores, embeddings |
| MySQL instead of PostgreSQL | Managed Databases, MySQL | [MySQL](https://techdocs.akamai.com/cloud-computing/docs/aiven-mysql) | An app or ORM that already uses MySQL |
| Uploads, images, PDFs, audio | Object Storage | [Lab 04](../04-object-storage/README.md) | Files your app saves, or shares with a link |
| A disk that keeps its data when the Linode is deleted | Block Storage | [Block Storage](https://techdocs.akamai.com/cloud-computing/docs/block-storage) | Files your app reads from a path, beyond the Linode's own disk |
| One public address in front of several servers | NodeBalancers | [NodeBalancers](https://techdocs.akamai.com/cloud-computing/docs/nodebalancer) | Two or more Linodes behind one IP. LKE makes one for you |
| Only the traffic I choose reaching a Linode | Cloud Firewall | [Lab 02](../02-linode/README.md#add-a-firewall) | Every Linode you keep running. It is free |
| A private network between my servers | VPC | [VPC](https://techdocs.akamai.com/cloud-computing/docs/vpc) | A database or worker that should not face the internet. It is free |
| A GPU | GPU Linodes | [GPU Linodes](https://techdocs.akamai.com/cloud-computing/docs/gpu-compute-instances) | Running your own model or encoding video. A new account may need a $100 deposit first, so ask event staff before you plan on one |
| My own domain name pointing at my app | DNS Manager | [DNS Manager](https://techdocs.akamai.com/cloud-computing/docs/dns-manager) | You already own a domain |
| A ready-made open source app, such as WordPress | Quick Deploy Apps | [Quick Deploy Apps](https://techdocs.akamai.com/quick-deploy-apps/docs/get-started) | A known app on a Linode in 5 to 10 minutes |

Choose services for the features your users need. More services do not automatically mean a higher score. Explain why each service fits and show it working. See [judging](judging.md) for what to show.
