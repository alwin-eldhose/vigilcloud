# Object Storage: a bucket for your files

Object Storage keeps files in a bucket, a named folder in the cloud. It uses the same API as Amazon S3, so S3 libraries such as boto3 work with it. Use it for any file your app saves: uploads, images, PDFs, audio.

**You get:** a private bucket in Chicago, a key that can use only that bucket, and a link that shares one file for an hour.
**Time:** 10 minutes.
**Cost:** $5 a month for the whole account, about $0.18 a day, prorated. It starts with your first bucket or key and continues until you cancel Object Storage, even with no buckets left.
**You need:** an active account, the [setup](../00-setup/README.md) done, and a terminal in the repo folder.

## 1. Create it

1. In [Cloud Manager](https://cloud.linode.com), the Akamai Cloud web console, select **Object Storage**, then **Create Bucket**.
2. Name the bucket `sea-<name>-files` with your first name in lowercase letters a to z, for example `sea-ada-files`.
3. Choose **Chicago, IL** in **Region**, not Seattle. Chicago offers the current endpoint type, E3, and Seattle offers it by request only. If the form shows **Object Storage Endpoint Type**, choose **Standard (E3)**.
4. Click **Create Bucket**. If Cloud Manager asks, click **Enable Object Storage**. This starts the monthly fee.
5. Open the **Access Keys** tab and click **Create Access Key**.
6. Set the label to `sea-<name>-files-key`. In the regions, choose **Chicago, IL**.
7. Turn on **Limited Access**. Set your bucket to **Read/Write** and leave every other bucket at **No Access**.
8. Click **Create Access Key**. Keep the window with the **Access Key** and the **Secret Key** open, and do [Connect](#2-connect) now. The secret is shown only once, so click **I Have Saved My Secret Key** only after that.

<details><summary>Same thing with the CLI</summary>

`linode-cli obj` also makes its own key the first time. See [cli.md](../00-setup/cli.md). Type `NAME=`, then your first name in lowercase, the one in your labels, and press Enter. Then run the second block:
```bash
NAME=PASTE_YOUR_NAME
```
```bash
linode-cli obj mb "sea-$NAME-files" --cluster us-ord-10
ACCESS='[{"region": "us-ord", "bucket_name": "sea-'"$NAME"'-files", "permissions": "read_write"}]'
linode-cli object-storage keys-create --label "sea-$NAME-files-key" --bucket_access "$ACCESS" \
  --text --format access_key,secret_key
```

</details>

## 2. Connect

Open `.env`, in the repo folder, in your code editor. If you cannot find it, see [troubleshooting](../docs/troubleshooting.md). Add the bucket name and both keys, then save the file. `OBJ_ENDPOINT` is already set for Chicago.

```text
OBJ_ENDPOINT=https://us-ord-10.linodeobjects.com
OBJ_BUCKET=the bucket name
OBJ_ACCESS_KEY=the Access Key value
OBJ_SECRET_KEY=the Secret Key value
```

## 3. Check it works

```bash
uv run 04-object-storage/storage.py
```

`storage.py` uploads `hello.txt`, lists the bucket, reads the file back, and prints a link. You should see:

```text
uploaded  hello.txt
listed    hello.txt  19 bytes
read      19 bytes back from hello.txt

This link works for one hour:
https://us-ord-10.linodeobjects.com/sea-ada-files/hello.txt?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...&X-Amz-Date=...&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=...
```

Open the link in a browser. You should see `Hello from Seattle`. To upload one of your own files, pass its path in place of `photo.png`: `uv run 04-object-storage/storage.py photo.png`.

## 4. Use it in your app

`boto3` is the AWS library for Python. It works with Object Storage when you keep the `Config` line from `storage.py`. Copy `storage.py` into your project and keep everything down to `bucket = os.environ["OBJ_BUCKET"]`. These three calls upload a file, download it, and make a one-hour link:

```python
s3.upload_file("photo.png", bucket, "photo.png")
s3.download_file(bucket, "photo.png", "copy.png")
url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": "photo.png"}, ExpiresIn=3600)
```

Keep the bucket private. Give users presigned links, signed links that expire, instead of making files public.

## Problems

| What you see | What to do |
|---|---|
| The bucket name is already in use | Another customer has it. Add a number, like `sea-ada-files2`, and use that name in `OBJ_BUCKET`. |
| `AccessDenied` | The key lacks **Read/Write** on this bucket, or `OBJ_BUCKET` has a typo. Make a new key as in [Create it](#1-create-it). |
| `InvalidAccessKeyId` | A new key can take a few seconds to work, so run it once more. If it repeats, copy the access key into `.env` again. A revoked key stops working at once. |
| `SignatureDoesNotMatch` or `MissingContentLength` on upload | boto3 1.36 and later add checksums the service does not support. Keep the `Config(signature_version="s3v4", request_checksum_calculation="when_required")` line. Then check the secret key. |
| `NoSuchBucket` | `OBJ_BUCKET` does not match the bucket's name, or `OBJ_ENDPOINT` is not the Chicago endpoint, `https://us-ord-10.linodeobjects.com`. If you made the bucket in Seattle, delete it and create it again in Chicago. |
| A link that worked shows `AccessDenied` an hour later | Links last one hour. Run `storage.py` again for a new one. |

## Delete it

Deleting the bucket and key does not stop the $5 monthly fee. Only cancelling Object Storage stops it, and cancelling deletes every bucket and file in the account.

1. Open your bucket in Cloud Manager and delete each file. Cloud Manager deletes only empty buckets.
2. Click **Delete** for your bucket in the bucket list. Type its name and click **Delete Bucket**.
3. Open the **...** menu for your key on the **Access Keys** tab and choose **Revoke**. Confirm with **Revoke**.
4. Cancel Object Storage to stop the fee, only if nothing else in the account uses it. Select **Administration**, then **Account Settings**. In the Object Storage section, click **Cancel Object Storage** and confirm with your username.

<details><summary>Same thing with the CLI</summary>

This removes the bucket with its files, then the key. It does not cancel Object Storage. Type `NAME=`, then your first name in lowercase, the one in your labels, and press Enter. Then run the second block:
```bash
NAME=PASTE_YOUR_NAME
```
```bash
linode-cli obj rb "sea-$NAME-files" --recursive --cluster us-ord-10
KEY_ID=$(linode-cli object-storage keys-list --text --no-headers --format id,label | awk -v l="sea-$NAME-files-key" '$2 == l {print $1}')
linode-cli object-storage keys-delete "$KEY_ID"
```

</details>

## More reading

- [Get started with Object Storage](https://techdocs.akamai.com/cloud-computing/docs/getting-started-with-object-storage), including when billing starts
- [Manage access keys](https://techdocs.akamai.com/cloud-computing/docs/manage-access-keys)
- [boto3 and Object Storage](https://techdocs.akamai.com/cloud-computing/docs/using-the-aws-sdk-for-python-boto3-with-object-storage)
- [Cancel Object Storage](https://techdocs.akamai.com/cloud-computing/docs/cancel-object-storage)
