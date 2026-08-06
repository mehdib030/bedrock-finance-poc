variable "project_name" {
  description = "Short lowercase project name used in resource names."
  type        = string
  default     = "sec-bedrock-poc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.project_name))
    error_message = "project_name must be 3-31 lowercase letters, numbers, or hyphens and start with a letter."
  }
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "poc"
}

variable "aws_region" {
  description = "AWS Region. Confirm Bedrock structured knowledge bases and your chosen model are supported here."
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR for the POC VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "redshift_database_name" {
  description = "Initial Redshift database name."
  type        = string
  default     = "financial_poc"
}

variable "redshift_admin_username" {
  description = "Redshift Serverless administrator username."
  type        = string
  default     = "pocadmin"
  sensitive   = true
}

variable "redshift_base_capacity" {
  description = "Base Redshift Serverless capacity in RPUs. Choose a value supported in your Region/account."
  type        = number
  default     = 8
}

variable "bedrock_model_id" {
  description = "Foundation model used by the advanced-report parameter extractor Lambda."
  type        = string
  default     = "amazon.nova-lite-v1:0"
}

variable "create_bedrock_knowledge_base" {
  description = "Create the structured Bedrock knowledge base through a CloudFormation stack."
  type        = bool
  default     = true
}

variable "bootstrap_redshift_schema" {
  description = "Run the local AWS CLI bootstrap script during apply. Requires AWS CLI on the Terraform runner."
  type        = bool
  default     = false
}

variable "enable_api_gateway" {
  description = "Create a public HTTP API for the POC Lambda. Add authentication before broader use."
  type        = bool
  default     = true
}

variable "allowed_cors_origins" {
  description = "Allowed CORS origins for the POC HTTP API. Restrict this for anything beyond a local demo."
  type        = list(string)
  default     = ["http://localhost:8501", "http://localhost:3000"]
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention period."
  type        = number
  default     = 14
}

variable "tags" {
  description = "Additional resource tags."
  type        = map(string)
  default     = {}
}
