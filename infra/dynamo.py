import pulumi_aws as aws

def make_table(name: str) -> aws.dynamodb.Table:
    return aws.dynamodb.Table(
        name,
        billing_mode="PAY_PER_REQUEST",
        hash_key="pk",
        range_key="sk",
        attributes=[
            aws.dynamodb.TableAttributeArgs(name="pk", type="S"),
            aws.dynamodb.TableAttributeArgs(name="sk", type="S"),
            aws.dynamodb.TableAttributeArgs(name="gsi1pk", type="S"),
        ],
        global_secondary_indexes=[
            aws.dynamodb.TableGlobalSecondaryIndexArgs(
                name="GSI1",
                hash_key="gsi1pk",
                projection_type="ALL",
            )
        ],
    )