resource "aws_cloudwatch_log_group" "router" {
  name              = "/aws/lambda/sec-bedrock-poc-router"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "basic_query" {
  name              = "/aws/lambda/sec-bedrock-poc-basic-query"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "complex_query" {
  name              = "/aws/lambda/sec-bedrock-poc-complex-query"
  retention_in_days = 14
}