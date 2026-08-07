locals {
  name_prefix = "${var.project_name}-${var.environment}"

  raw_prefix        = "raw/sec"
  normalized_prefix = "normalized"
  semantic_prefix   = "semantic"
  templates_prefix  = "templates/sql"
  evaluation_prefix = "evaluation"

  basic_view_name = "public.bedrock_basic_financial_metrics"

  bedrock_kb_name = replace("${local.name_prefix}-financial-kb", "-", "_")
}
