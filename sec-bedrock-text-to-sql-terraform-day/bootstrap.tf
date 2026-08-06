resource "terraform_data" "bootstrap_redshift" {
  count = var.bootstrap_redshift_schema ? 1 : 0

  triggers_replace = [
    filesha256("${path.module}/sql/bootstrap.sql"),
    aws_redshiftserverless_workgroup.this.id
  ]

  provisioner "local-exec" {
    command = "${path.module}/scripts/bootstrap_redshift.sh"
    environment = {
      AWS_REGION            = var.aws_region
      WORKGROUP_NAME        = aws_redshiftserverless_workgroup.this.workgroup_name
      DATABASE_NAME         = var.redshift_database_name
      SQL_FILE              = "${path.module}/sql/bootstrap.sql"
      REDSHIFT_IAM_ROLE_ARN = aws_iam_role.redshift_s3.arn
      NORMALIZED_S3_URI     = "s3://${aws_s3_bucket.data.id}/${local.normalized_prefix}/company_financial_metrics/"
    }
  }
}
