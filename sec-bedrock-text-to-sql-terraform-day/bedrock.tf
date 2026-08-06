locals {
  bedrock_kb_template = yamlencode({
    AWSTemplateFormatVersion = "2010-09-09"
    Description              = "Structured Bedrock Knowledge Base for the SEC financial POC"
    Resources = {
      StructuredKnowledgeBase = {
        Type = "AWS::Bedrock::KnowledgeBase"
        Properties = {
          Name        = local.bedrock_kb_name
          Description = "Generates basic SQL over the restricted SEC financial metrics view."
          RoleArn     = aws_iam_role.bedrock_kb.arn
          KnowledgeBaseConfiguration = {
            Type = "SQL"
            SqlKnowledgeBaseConfiguration = {
              Type = "REDSHIFT"
              RedshiftConfiguration = {
                QueryEngineConfiguration = {
                  Type = "SERVERLESS"
                  ServerlessConfiguration = {
                    WorkgroupArn = aws_redshiftserverless_workgroup.this.arn
                    AuthConfiguration = {
                      Type = "IAM"
                    }
                  }
                }
                StorageConfigurations = [{
                  Type = "REDSHIFT"
                  RedshiftConfiguration = {
                    DatabaseName = var.redshift_database_name
                  }
                }]
                QueryGenerationConfiguration = {
                  ExecutionTimeoutSeconds = 60
                  GenerationContext = {
                    Tables = [{
                      Name        = local.basic_view_name
                      Description = "Restricted view containing normalized SEC 10-K and 10-Q financial metrics. Generate only simple, read-only queries over this view."
                      Inclusion   = "INCLUDE"
                      Columns = [
                        { Name = "company_name", Description = "SEC registrant name; use case-insensitive matching for common names." },
                        { Name = "sic", Description = "Standard Industrial Classification code." },
                        { Name = "filing_type", Description = "10-K means annual; 10-Q means quarterly." },
                        { Name = "fiscal_year", Description = "Company fiscal year, which may differ from calendar year." },
                        { Name = "fiscal_period", Description = "Fiscal period such as FY, Q1, Q2, or Q3." },
                        { Name = "period_end", Description = "Financial reporting period end date." },
                        { Name = "metric_name", Description = "Canonical metric such as revenue, net_income, total_assets, total_liabilities, stockholders_equity, cash_and_equivalents, or operating_cash_flow." },
                        { Name = "metric_value", Description = "Reported numeric metric value." },
                        { Name = "unit", Description = "Reporting unit; the POC normally uses USD." },
                        { Name = "duration_quarters", Description = "4 annual duration, 1 quarterly duration, 0 point-in-time balance." }
                      ]
                    }]
                    CuratedQueries = [
                      {
                        NaturalLanguage = "What was Microsoft's annual revenue from 2022 through 2025?"
                        Sql             = "SELECT fiscal_year, MAX(metric_value) AS revenue FROM public.bedrock_basic_financial_metrics WHERE LOWER(company_name) LIKE '%microsoft%' AND metric_name = 'revenue' AND filing_type = '10-K' AND duration_quarters = 4 AND fiscal_year BETWEEN 2022 AND 2025 GROUP BY fiscal_year ORDER BY fiscal_year LIMIT 100;"
                      },
                      {
                        NaturalLanguage = "Show the ten companies with the largest total assets in fiscal 2025."
                        Sql             = "SELECT company_name, MAX(metric_value) AS total_assets FROM public.bedrock_basic_financial_metrics WHERE metric_name = 'total_assets' AND filing_type = '10-K' AND duration_quarters = 0 AND fiscal_year = 2025 GROUP BY company_name ORDER BY total_assets DESC LIMIT 10;"
                      }
                    ]
                  }
                }
              }
            }
          }
        }
      }
    }
    Outputs = {
      KnowledgeBaseId = {
        Value = { Ref = "StructuredKnowledgeBase" }
      }
      KnowledgeBaseArn = {
        Value = { "Fn::GetAtt" = ["StructuredKnowledgeBase", "KnowledgeBaseArn"] }
      }
    }
  })
}

resource "aws_cloudformation_stack" "bedrock_kb" {
  count = var.create_bedrock_knowledge_base ? 1 : 0

  name          = "${local.name_prefix}-bedrock-kb"
  template_body = local.bedrock_kb_template

  capabilities = ["CAPABILITY_NAMED_IAM"]

  depends_on = [
    aws_iam_role_policy.bedrock_kb,
    aws_redshiftserverless_workgroup.this
  ]
}
