data "archive_file" "app" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/.terraform-build/app.zip"
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/aws/lambda/${local.name_prefix}-app"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "app" {
  function_name = "${local.name_prefix}-app"
  role          = aws_iam_role.app_lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.13"
  timeout       = 60
  memory_size   = 512

  filename         = data.archive_file.app.output_path
  source_code_hash = data.archive_file.app.output_base64sha256

  environment {
    variables = {
      AWS_ACCOUNT_ID             = data.aws_caller_identity.current.account_id
      BEDROCK_KNOWLEDGE_BASE_ARN = var.create_bedrock_knowledge_base ? aws_cloudformation_stack.bedrock_kb[0].outputs["KnowledgeBaseArn"] : ""
      BEDROCK_MODEL_ID           = var.bedrock_model_id
      REDSHIFT_WORKGROUP_NAME    = aws_redshiftserverless_workgroup.this.workgroup_name
      REDSHIFT_DATABASE_NAME     = var.redshift_database_name
      TEMPLATE_BUCKET            = aws_s3_bucket.data.id
      TEMPLATE_PREFIX            = local.templates_prefix
      BASIC_VIEW_NAME            = local.basic_view_name
      MAX_RESULT_ROWS            = "500"
    }
  }

  depends_on = [aws_cloudwatch_log_group.app]
}
