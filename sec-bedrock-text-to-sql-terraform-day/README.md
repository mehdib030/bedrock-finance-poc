# SEC Financial Text-to-SQL POC — Terraform

This project provisions the AWS infrastructure for the hybrid POC:

- Basic questions: Amazon Bedrock Knowledge Bases `GenerateQuery` creates SQL; Lambda applies a strict basic-SQL policy; Redshift Data API submits the approved query.
- Complex questions: approved SQL files live in a versioned S3 registry; Bedrock should extract only `template_id` and parameters. The sample Lambda intentionally leaves this path as the next implementation step.

## Resources created

- Private VPC and three private subnets
- Encrypted, versioned S3 data/template bucket
- Redshift Serverless namespace and private workgroup
- IAM roles for Redshift, Lambda, and Bedrock Knowledge Bases
- Structured Bedrock Knowledge Base through `AWS::Bedrock::KnowledgeBase` in a Terraform-managed CloudFormation stack
- Lambda orchestration skeleton and CloudWatch log group
- API Gateway HTTP API (`POST /query`)
- Three approved complex SQL templates in S3

## Important boundaries

Terraform creates infrastructure. It does **not** download or normalize the SEC dataset. Use your ingestion Python program to upload raw ZIPs and normalized Parquet files.

The database table/view must exist before the Bedrock knowledge base can successfully use its generation context. For the cleanest first deployment:

1. Set `create_bedrock_knowledge_base = false`.
2. Apply Terraform.
3. Run the Redshift schema bootstrap.
4. Load normalized data.
5. Set `create_bedrock_knowledge_base = true` and apply again.

## Prerequisites

- Terraform 1.7+
- AWS CLI v2
- AWS credentials with permissions to create the included services
- Bedrock model access in the selected Region
- A Region supporting Bedrock Knowledge Bases with structured data and Redshift Serverless

## Deploy

```bash
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

Recommended staged first deployment:

```hcl
create_bedrock_knowledge_base = false
bootstrap_redshift_schema     = false
```

After the workgroup is available, bootstrap the table and view:

```bash
export AWS_REGION=$(terraform output -raw aws_region 2>/dev/null || echo us-east-1)
export WORKGROUP_NAME=$(terraform output -raw redshift_workgroup_name)
export DATABASE_NAME=$(terraform output -raw redshift_database_name)
export SQL_FILE="$PWD/sql/bootstrap.sql"
./scripts/bootstrap_redshift.sh
```

Alternatively set `bootstrap_redshift_schema = true` and run `terraform apply`; this uses a local-exec provisioner and requires the AWS CLI on the Terraform runner.

Upload normalized Parquet data under the output `normalized_data_prefix`, then run a `COPY` command using the commented example in `sql/bootstrap.sql`.

Finally enable the structured knowledge base:

```hcl
create_bedrock_knowledge_base = true
```

and run `terraform apply` again.

## Test API

```bash
API=$(terraform output -raw api_endpoint)
curl -sS -X POST "$API/query" \
  -H 'content-type: application/json' \
  -d '{"mode":"basic","question":"What was Microsoft annual revenue in 2024?"}'
```

The sample endpoint returns a Redshift statement ID. Add polling of `DescribeStatement` and `GetStatementResult` in the application/UI as the next step.

## Security notes

- Redshift is private and not publicly accessible.
- The S3 bucket blocks public access, uses encryption, and enables versioning.
- Generated SQL is rejected when it is not one `SELECT` over the restricted view or contains complex constructs.
- The sample API is unauthenticated for POC convenience. Add Cognito/JWT authorization before sharing it.
- Tighten IAM resource scopes after confirming the exact Bedrock and Redshift ARNs used in your account.

## Destroy

The S3 bucket uses `force_destroy = true` and the Redshift administrator secret uses zero-day recovery for easy POC cleanup:

```bash
terraform destroy
```

Change those settings before adapting this design for production.

## Day-one network note

`network_endpoints.tf` adds a private route table and an Amazon S3 gateway VPC
endpoint. The workgroup has enhanced VPC routing enabled, so this endpoint is
needed before a later Redshift `COPY` reads normalized files from S3 without a
NAT gateway.
