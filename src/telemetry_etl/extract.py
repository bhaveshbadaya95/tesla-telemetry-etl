from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import boto3


@dataclass(frozen=True)
class S3Object:
    # This stores the S3 metadata needed for loading and processed-file tracking.
    bucket: str
    key: str
    size: int
    etag: str
    last_modified: str


def list_partitioned_objects(bucket: str, prefix: str, region_name: str = "us-east-1") -> list[S3Object]:
    # Create an S3 client in the configured AWS region.
    client = boto3.client("s3", region_name=region_name)
    # Pagination is required because large buckets may return results in many pages.
    paginator = client.get_paginator("list_objects_v2")
    objects: list[S3Object] = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            # Skip folder placeholder keys because they are not real data files.
            if key.endswith("/"):
                continue
            # Keep the ETag so Snowflake can track exactly which object version was processed.
            objects.append(
                S3Object(
                    bucket=bucket,
                    key=key,
                    size=item["Size"],
                    etag=item["ETag"].strip('"'),
                    last_modified=item["LastModified"].isoformat(),
                )
            )
    return objects


def download_object(bucket: str, key: str, local_path: str | Path, region_name: str = "us-east-1") -> Path:
    # Pulls one raw telemetry object down to a local path so it can be transformed.
    client = boto3.client("s3", region_name=region_name)
    destination = Path(local_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, key, str(destination))
    return destination
