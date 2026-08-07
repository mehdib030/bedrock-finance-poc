resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "data" {
  bucket        = "${local.name_prefix}-${data.aws_caller_identity.current.account_id}-${random_id.suffix.hex}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_object" "prefixes" {
  for_each = toset([
    "${local.raw_prefix}/.keep",
    "${local.normalized_prefix}/.keep",
    "${local.semantic_prefix}/.keep",
    "${local.evaluation_prefix}/.keep"
  ])

  bucket  = aws_s3_bucket.data.id
  key     = each.value
  content = ""
}

resource "aws_s3_object" "sql_templates" {
  for_each = fileset("${path.module}/sql/templates", "*.sql")

  bucket = aws_s3_bucket.data.id
  key    = "${local.templates_prefix}/${each.value}"
  source = "${path.module}/sql/templates/${each.value}"
  etag   = filemd5("${path.module}/sql/templates/${each.value}")
}
