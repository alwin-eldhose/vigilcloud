# LKE: containers on a Kubernetes cluster

LKE is Kubernetes that Akamai runs for you. Akamai runs the control plane, and your containers run on Linodes in the cluster. Use it if your team already knows Kubernetes or runs several containers. Everyone else should use one [Linode](../02-linode/README.md).

**You get:** a one-node cluster in Seattle running a small web server behind a public IP address.
**Time:** 15 minutes, plus about 3 minutes of waiting.
**Cost:** $0.79 a day: $0.43 for the Linode 2 GB node and $0.36 for the NodeBalancer, the load balancer that holds the public address. The control plane is free. Both bill by the hour until you delete them.
**You need:** an active account, the [setup](../00-setup/README.md) done, a terminal in the repo folder, and [kubectl](https://kubernetes.io/docs/tasks/tools/), the command-line tool for Kubernetes. `kubectl version --client` should print a line that starts with `Client Version:`. Section 4 also needs Docker and an account on a registry such as Docker Hub.

## 1. Create it

1. In [Cloud Manager](https://cloud.linode.com), the Akamai Cloud web console, select **Kubernetes**, then **Create Cluster**.
2. Set **Cluster Label** to `sea-<name>-lke` with your first name in lowercase letters a to z, for example `sea-ada-lke`.
3. Choose the **LKE** tier, not LKE Enterprise.
4. Choose **Seattle, WA** in **Region**.
5. Choose the highest number in **Kubernetes Version**.
6. If the form shows **Akamai App Platform**, choose **No**. It adds a paid HA control plane and larger nodes that this lab does not use.
7. Choose **No** under **HA Control Plane**. HA runs spare copies of the control plane and costs extra.
8. Leave **Enable Control Plane ACL** off. It limits which addresses can run `kubectl`, and venue Wi-Fi addresses change.
9. Set **Linode 2 GB** to 1 node on the **Shared CPU** tab of **Add Node Pools**, and click **Add**. LKE does not offer the 1 GB plan.
10. Click **Create Cluster**.
11. If your `Downloads` folder holds an older `sea-<name>-lke-kubeconfig.yaml`, delete it first, so the new one keeps that name. Wait about 2 minutes. Then, on your cluster's page, click `sea-<name>-lke-kubeconfig.yaml` next to **Kubeconfig**. The file lands in your `Downloads` folder. kubectl uses it to log in to your cluster, so treat it like a password.

<details><summary>Same thing with the CLI</summary>

Set up the [Linode CLI](../00-setup/cli.md) first. Type `NAME=`, then your first name in lowercase, the one in your labels, and press Enter. Then run the second block:
```bash
NAME=PASTE_YOUR_NAME
```
```bash
VERSION=$(linode-cli lke versions-list --text --no-headers | head -1)
linode-cli lke cluster-create --label "sea-$NAME-lke" --region us-sea --k8s_version "$VERSION" \
  --node_pools.type g6-standard-1 --node_pools.count 1 --text --format id,label
CLUSTER_ID=$(linode-cli lke clusters-list --label "sea-$NAME-lke" --text --no-headers --format id)
linode-cli lke kubeconfig-view "$CLUSTER_ID" --text --no-headers | base64 -d > ~/Downloads/sea-$NAME-lke-kubeconfig.yaml
```

The kubeconfig can take about 2 minutes to exist. Until then the last command fails with `503`.

</details>

## 2. Connect

In your laptop terminal, point kubectl at the kubeconfig in your `Downloads` folder, then list the nodes. Type `NAME=`, then your first name in lowercase, the one in your cluster label, and press Enter. Then run the second block:
```bash
NAME=PASTE_YOUR_NAME
```
```bash
export KUBECONFIG=~/Downloads/sea-$NAME-lke-kubeconfig.yaml
kubectl get nodes
```

You should see one node with the status `Ready`. A new node shows `NotReady` for about its first minute.
```text
NAME                         STATUS   ROLES    AGE   VERSION
lke12345678-12345678-abcde   Ready    <none>   74s   v1.37.1
```

## 3. Check it works

1. Start the web server and its public address. The Deployment in `deployment.yaml` keeps one copy of the server running. The Service in `service.yaml` puts a NodeBalancer with a public address in front of it:
```bash
kubectl apply -f 05-lke/
```
You should see:
```text
deployment.apps/hello created
service/hello created
```
2. Wait for the address. Run this until `EXTERNAL-IP` shows a number instead of `<pending>`, usually under a minute:
```bash
kubectl get service hello
```
3. Send it a request. `LB_IP` holds the NodeBalancer's public address:
```bash
LB_IP=$(kubectl get service hello -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl "http://$LB_IP/"
```
You should see the name of the pod that answered, the pod's addresses, the node that passed your request on as `RemoteAddr`, and your request:
```text
Hostname: hello-5f77f9d645-zsczz
IP: 127.0.0.1
IP: ::1
IP: 10.2.0.8
IP: fe80::2429:5bff:fe34:f71f
RemoteAddr: 203.0.113.20:65409
GET / HTTP/1.1
Host: 203.0.113.10
User-Agent: curl/8.5.0
Accept: */*
```

## 4. Use it in your app

### Run your own image

Push your image to a public registry, such as Docker Hub, then point the Deployment at it. Anyone can pull a public image, so keep `.env` out of it. `demo/Dockerfile` copies only `app.py` and `index.html`. Step 1 builds the demo app's image. For your own app, put its folder in place of `demo/`.

1. Log in to your registry with `docker login`. Then build and push. Type `DOCKER_USER=`, then your Docker Hub username, and press Enter. Then run the second block. `IMAGE` is your registry path and tag. `--platform linux/amd64` matches the cluster's nodes, even when you build on an Apple Silicon Mac:
```bash
DOCKER_USER=PASTE_YOUR_DOCKER_USERNAME
```
```bash
IMAGE=docker.io/$DOCKER_USER/sea-app:1
docker build --platform linux/amd64 -t "$IMAGE" demo/
docker push "$IMAGE"
```
2. Open `05-lke/deployment.yaml` in your code editor. On the `image:` line, change `traefik/whoami:v1.12.0` to your `IMAGE` value, written out, such as `docker.io/PASTE_YOUR_DOCKER_USERNAME/sea-app:1` with your username. Keep the spaces in front of `image:`. kubectl does not fill in `$IMAGE` inside a file.
3. In the same file, delete the `#` and the space after it at the start of each of the last four lines, the `envFrom` block. `envFrom:` then starts in the same column as `env:` above it. This block gives the container every line of your `.env`, so do it only after step 2. The image the file ships with prints every environment variable, your key included, to anyone who asks.
4. If your app listens on a port other than 80, set `containerPort` to it. Save the file.
5. Load your `.env` into the cluster as a Secret, the cluster's store for keys and passwords. The Deployment sets each line as an environment variable in your container:
```bash
kubectl create secret generic app-env --from-env-file=.env
kubectl apply -f 05-lke/
kubectl rollout status deployment/hello
```
The last line reads `deployment "hello" successfully rolled out`. If it waits more than two minutes, press Ctrl+C and run `kubectl get pods`.
6. Ask the demo for its services, with `LB_IP` from [Check it works](#3-check-it-works):
```bash
curl "http://$LB_IP/health"
```
The database reads `connected` once Akamai adds the node to the [database](../03-database/README.md) allow list, usually within 10 minutes. If it still reads an error after 15 minutes, add the node's address by hand, as Lab 03 shows under "Let your Linode in". The node is on your **Linodes** page, with a label that starts with `lke`. Without Labs 03 and 04, the database and object storage read `not set`. With both, you should see:
```text
{"inference":"configured","database":"connected","object_storage":"connected"}
```

The NodeBalancer's address is open to the whole internet, and the app has no login. No firewall limits it, unlike the Linode in Lab 02. Anyone who finds the address can spend your key's quota and read or upload files. Use practice data, and delete the Service when you finish testing.

## Problems

| What you see | What to do |
|---|---|
| `No resources found` or `NotReady` from `kubectl get nodes` | The node is still joining. Wait a minute and run it again. |
| `Unable to connect to the server` or `connection refused` on `localhost:8080` | This terminal has no `KUBECONFIG`, or `NAME` does not match the file's name. Set `NAME` to your name, then run the `export KUBECONFIG` line again. |
| The same, right after the `export` line, on Windows with WSL | The browser saved the kubeconfig in the Windows `Downloads` folder. Copy it into WSL with `mkdir -p ~/Downloads && cp /mnt/c/Users/*/Downloads/sea-*-lke-kubeconfig.yaml ~/Downloads/`, then run the `export` line again. |
| `EXTERNAL-IP` stays `<pending>` | The NodeBalancer is starting. Give it two minutes. |
| `curl: (52) Empty reply from server` | The NodeBalancer is up but still checking the node. Wait up to a minute. If it goes on, run `kubectl get pods`. |
| `ErrImagePull`, `ImagePullBackOff`, or `InvalidImageName` in `kubectl get pods` | The image name has a typo, or the image is private. Write the full name after `image:`, not `$IMAGE`. |
| `exec format error` in `kubectl logs deployment/hello` | The image was built for ARM. Build it again with `--platform linux/amd64`. |
| `Error` or `CrashLoopBackOff` in `kubectl get pods`, and `kubectl logs deployment/hello` says `AKAMAI_BASE_URL is not set` | The last four lines of `05-lke/deployment.yaml`, the `envFrom` block, still start with `# `. Delete the `#` and the space after it on all four, then run `kubectl apply -f 05-lke/` again. |
| `secrets "app-env" already exists` | Run `kubectl delete secret app-env`, create it again, then `kubectl rollout restart deployment hello`. |

## Delete it

Delete the Service first. Deleting it deletes its NodeBalancer. A cluster deleted first leaves its NodeBalancers behind, and they keep billing.

1. In your laptop terminal, delete the Service, and with it the NodeBalancer. Type `NAME=`, then your first name in lowercase, the one in your cluster label, and press Enter. Then run the second block:
```bash
NAME=PASTE_YOUR_NAME
```
```bash
export KUBECONFIG=~/Downloads/sea-$NAME-lke-kubeconfig.yaml
kubectl delete service hello
```
2. In Cloud Manager, open **Kubernetes** and select your cluster. Click **Delete Cluster**. Type the cluster's name in **Cluster Name**, then click **Delete Cluster** again.
3. Open **NodeBalancers**. If one is left from your cluster, open its **...** menu and choose **Delete**.
4. Delete your kubeconfig. The cluster it pointed to is gone:
```bash
rm ~/Downloads/sea-$NAME-lke-kubeconfig.yaml
```

## More reading

- [Create a cluster](https://techdocs.akamai.com/cloud-computing/docs/create-a-cluster)
- [Manage a cluster with kubectl](https://techdocs.akamai.com/cloud-computing/docs/manage-a-cluster-with-kubectl)
- [Load balancing on LKE](https://techdocs.akamai.com/cloud-computing/docs/get-started-with-load-balancing-on-an-lke-cluster)
- [Manage Kubernetes clusters on LKE](https://techdocs.akamai.com/cloud-computing/docs/manage-kubernetes-clusters-on-lke)
