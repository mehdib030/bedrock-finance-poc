output "data_bucket_name" {
  value = aws_s3_bucket.data.id
}

output "raw_sec_prefix" {
  value = "s3://${aws_s3_bucket.data.id}/${local.raw_prefix}/"
}

output "normalized_data_prefix" {
  value = "s3://${aws_s3_bucket.data.id}/${local.normalized_prefix}/"
}

output "template_registry_prefix" {
  value = "s3://${aws_s3_bucket.data.id}/${local.templates_prefix}/"
}

output "redshift_namespace_name" {
  value = aws_redshiftserverless_namespace.this.namespace_name
}

output "redshift_workgroup_name" {
  value = aws_redshiftserverless_workgroup.this.workgroup_name
}

output "redshift_workgroup_arn" {
  value = aws_redshiftserverless_workgroup.this.arn
}

output "redshift_database_name" {
  value = var.redshift_database_name
}

output "redshift_admin_secret_arn" {
  value     = aws_secretsmanager_secret.redshift_admin.arn
  sensitive = true
}

output "bedrock_knowledge_base_id" {
  value = var.create_bedrock_knowledge_base ? aws_cloudformation_stack.bedrock_kb[0].outputs["KnowledgeBaseId"] : null
}

output "api_endpoint" {
  value = var.enable_api_gateway ? aws_apigatewayv2_api.this[0].api_endpoint : null
}

output "lambda_function_name" {
  value = aws_lambda_function.app.function_name
}

output "aws_region" {
  value = var.aws_region
}
