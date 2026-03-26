import pulumi_aws as aws


def make_bucket(name: str) -> aws.s3.Bucket:
    bucket = aws.s3.Bucket(
        name,
        force_destroy=True,
    )

    aws.s3.BucketPublicAccessBlock(
        f"{name}-block",
        bucket=bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
    )

    aws.s3.BucketCorsConfiguration(
        f"{name}-cors",
        bucket=bucket.id,
        cors_rules=[aws.s3.BucketCorsConfigurationCorsRuleArgs(
            allowed_origins=["*"],
            allowed_methods=["POST", "GET", "HEAD", "PUT"],
            allowed_headers=["*"],
            expose_headers=["ETag"],
            max_age_seconds=3000,
        )],
    )

    return bucket