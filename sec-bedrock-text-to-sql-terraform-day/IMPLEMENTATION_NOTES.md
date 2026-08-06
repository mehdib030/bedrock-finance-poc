# Implementation notes

- Bedrock structured Knowledge Bases require a Redshift query engine configuration and one storage configuration. This project uses Redshift Serverless with IAM authentication and native Redshift storage.
- The structured Knowledge Base is provisioned through `aws_cloudformation_stack`, which keeps the overall deployment Terraform-managed while using the current `AWS::Bedrock::KnowledgeBase` SQL schema.
- SQL/parameter validators are application code, not standalone AWS services.
- The Lambda SQL validator is intentionally conservative and should be upgraded to an AST parser such as `sqlglot` in a Lambda layer before a production pilot.
- The complex templates contain placeholder conventions that the application must render safely; never concatenate arbitrary model text into SQL.
