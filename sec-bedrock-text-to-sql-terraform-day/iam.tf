data "aws_iam_policy_document" "redshift_s3_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["redshift.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "redshift_s3" {
  name               = "${local.name_prefix}-redshift-s3"
  assume_role_policy = data.aws_iam_policy_document.redshift_s3_assume.json
}

data "aws_iam_policy_document" "redshift_s3" {
  statement {
    sid       = "ListDataBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn]
  }

  statement {
    sid       = "ReadNormalizedData"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.data.arn}/${local.normalized_prefix}/*"]
  }
}

resource "aws_iam_role_policy" "redshift_s3" {
  name   = "${local.name_prefix}-redshift-s3"
  role   = aws_iam_role.redshift_s3.id
  policy = data.aws_iam_policy_document.redshift_s3.json
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app_lambda" {
  name               = "${local.name_prefix}-app-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "app_lambda" {
  statement {
    sid = "Logs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"]
  }

  statement {
    sid = "GenerateQueries"
    actions = [
      "bedrock:GenerateQuery",
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = ["*"]
  }

  statement {
    sid = "ExecuteRedshift"
    actions = [
      "redshift-data:ExecuteStatement",
      "redshift-data:DescribeStatement",
      "redshift-data:GetStatementResult",
      "redshift-data:CancelStatement",
      "redshift-serverless:GetCredentials"
    ]
    resources = ["*"]
  }

  statement {
    sid       = "ReadApprovedTemplates"
    actions   = ["s3:GetObject", "s3:GetObjectVersion"]
    resources = ["${aws_s3_bucket.data.arn}/${local.templates_prefix}/*"]
  }
}

resource "aws_iam_role_policy" "app_lambda" {
  name   = "${local.name_prefix}-app"
  role   = aws_iam_role.app_lambda.id
  policy = data.aws_iam_policy_document.app_lambda.json
}

data "aws_iam_policy_document" "bedrock_kb_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "bedrock_kb" {
  name               = "${local.name_prefix}-bedrock-kb"
  assume_role_policy = data.aws_iam_policy_document.bedrock_kb_assume.json
}

data "aws_iam_policy_document" "bedrock_kb" {
  statement {
    sid = "RedshiftServerless"
    actions = [
      "redshift-serverless:GetCredentials",
      "redshift-serverless:GetWorkgroup",
      "redshift-serverless:GetNamespace",
      "redshift-data:ExecuteStatement",
      "redshift-data:DescribeStatement",
      "redshift-data:GetStatementResult"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "bedrock_kb" {
  name   = "${local.name_prefix}-bedrock-kb"
  role   = aws_iam_role.bedrock_kb.id
  policy = data.aws_iam_policy_document.bedrock_kb.json
}
