import sys

from django.apps import AppConfig


class JournalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.journal"

    def ready(self):
        # Skip S3 bucket initialization during tests
        if "test" in sys.argv:
            return

        import boto3
        import requests
        from botocore.exceptions import ClientError
        from django.conf import settings

        options = settings.STORAGES["stickers"]["OPTIONS"]
        bucket = options["bucket_name"]

        s3 = boto3.client(
            "s3",
            endpoint_url=options["endpoint_url"],
            aws_access_key_id=options["access_key"],
            aws_secret_access_key=options["secret_key"],
            region_name=options["region_name"],
        )

        try:
            s3.head_bucket(Bucket=bucket)
            return  # bucket already exists, nothing to do
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                raise  # unexpected error, re-raise

        # Bucket doesn't exist — create it
        s3.create_bucket(Bucket=bucket)

        # Grant the key read+write via Garage's admin API
        # (this also makes the bucket accessible; Garage doesn't use S3 ACLs)
        admin_url = settings.GARAGE_ADMIN_URL
        headers = {"Authorization": f"Bearer {settings.GARAGE_ADMIN_TOKEN}"}

        keys = requests.get(f"{admin_url}/v2/ListKeys", headers=headers)
        keys.raise_for_status()
        key_id = next(
            k["id"] for k in keys.json() if k["accessKeyId"] == options["access_key"]
        )

        resp = requests.post(
            f"{admin_url}/v2/AllowBucketKey",
            headers=headers,
            json={
                "bucketId": bucket,
                "accessKeyId": key_id,
                "permissions": {"read": True, "write": True, "owner": False},
            },
        )
        resp.raise_for_status()
