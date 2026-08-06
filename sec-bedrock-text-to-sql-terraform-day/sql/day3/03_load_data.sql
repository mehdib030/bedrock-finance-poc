COPY analytics.company_financial_metrics
FROM 's3://sec-bedrock-poc-poc-461081837269-ae55331b/semantic/company_financial_metrics/'
IAM_ROLE 'arn:aws:iam::461081837269:role/sec-bedrock-poc-poc-redshift-s3'
FORMAT AS PARQUET;