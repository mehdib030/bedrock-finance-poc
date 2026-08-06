resource "random_password" "redshift_admin" {
  length  = 32
  upper   = true
  lower   = true
  numeric = true
  special = true

  min_upper   = 1
  min_lower   = 1
  min_numeric = 1
  min_special = 1

  # Redshift rejects / @ " space \ and '
  override_special = "!#$%&*+-=_"
}

resource "aws_secretsmanager_secret" "redshift_admin" {
  name                    = "${local.name_prefix}/redshift/admin"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "redshift_admin" {
  secret_id = aws_secretsmanager_secret.redshift_admin.id
  secret_string = jsonencode({
    username = var.redshift_admin_username
    password = random_password.redshift_admin.result
  })
}

resource "aws_redshiftserverless_namespace" "this" {
  namespace_name      = "${local.name_prefix}-ns"
  db_name             = var.redshift_database_name
  admin_username      = var.redshift_admin_username
  admin_user_password = random_password.redshift_admin.result

  default_iam_role_arn = aws_iam_role.redshift_s3.arn
  iam_roles            = [aws_iam_role.redshift_s3.arn]
}

resource "aws_redshiftserverless_workgroup" "this" {
  namespace_name       = aws_redshiftserverless_namespace.this.namespace_name
  workgroup_name       = "${local.name_prefix}-wg"
  base_capacity        = var.redshift_base_capacity
  publicly_accessible  = false
  enhanced_vpc_routing = true

  subnet_ids         = aws_subnet.private[*].id
  security_group_ids = [aws_security_group.redshift.id]

  config_parameter {
    parameter_key   = "enable_user_activity_logging"
    parameter_value = "true"
  }
}
