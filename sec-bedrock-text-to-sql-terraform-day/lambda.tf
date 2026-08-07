resource "aws_lambda_function" "basic_query" {
  function_name = "sec-bedrock-poc-basic-query"
  role          = aws_iam_role.basic_lambda.arn
  runtime       = "python3.12"
  handler       = "handler.lambda_handler"

  filename = "${path.module}/../build/basic-query.zip"
  source_code_hash = filebase64sha256(
    "${path.module}/../build/basic-query.zip"
  )

  timeout     = 90
  memory_size = 512

  environment {
    variables = {
      BEDROCK_KB_ARN        = var.bedrock_knowledge_base_arn
      ALLOWED_RELATIONS     = var.allowed_relations
      REDSHIFT_WORKGROUP    = aws_redshiftserverless_workgroup.this.workgroup_name
      REDSHIFT_DATABASE     = var.redshift_database
      QUERY_TIMEOUT_SECONDS = "45"
      MAX_RESULT_ROWS       = "100"
    }
  }
}

resource "aws_lambda_function" "complex_query" {
  function_name = "sec-bedrock-poc-complex-query"
  role          = aws_iam_role.complex_lambda.arn
  runtime       = "python3.12"
  handler       = "handler.lambda_handler"

  filename = "${path.module}/../build/complex-query.zip"
  source_code_hash = filebase64sha256(
    "${path.module}/../build/complex-query.zip"
  )

  timeout     = 90
  memory_size = 512

  environment {
    variables = {
      BEDROCK_MODEL_ID      = var.bedrock_model_id
      REDSHIFT_WORKGROUP    = aws_redshiftserverless_workgroup.this.workgroup_name
      REDSHIFT_DATABASE     = var.redshift_database
      QUERY_TIMEOUT_SECONDS = "45"
      MAX_RESULT_ROWS       = "100"
    }
  }
}

resource "aws_lambda_function" "router" {
  function_name = "sec-bedrock-poc-router"
  role          = aws_iam_role.router_lambda.arn
  runtime       = "python3.12"
  handler       = "handler.lambda_handler"

  filename = "${path.module}/../build/router.zip"

  source_code_hash = filebase64sha256(
    "${path.module}/../build/router.zip"
  )

  timeout     = 120
  memory_size = 256

  environment {
    variables = {
      BASIC_FUNCTION_NAME   = aws_lambda_function.basic_query.function_name
      COMPLEX_FUNCTION_NAME = aws_lambda_function.complex_query.function_name
    }
  }
}
