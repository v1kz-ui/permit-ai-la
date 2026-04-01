# ============================================================================
# WAF (Web Application Firewall) Module for PermitAI LA
# ============================================================================

variable "environment" {
  description = "Deployment environment (e.g., staging, production)"
  type        = string
}

variable "alb_arn" {
  description = "ARN of the Application Load Balancer to protect"
  type        = string
}

# --- WAFv2 WebACL ---

resource "aws_wafv2_web_acl" "main" {
  name        = "permitai-${var.environment}-waf"
  description = "WAF rules for PermitAI LA ${var.environment}"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  # Rule 1: Rate limiting - 2000 requests per 5 minutes per IP
  rule {
    name     = "rate-limit"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "permitai-${var.environment}-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  # Rule 2: AWS Managed - SQL Injection Protection
  rule {
    name     = "aws-sqli-protection"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "permitai-${var.environment}-sqli"
      sampled_requests_enabled   = true
    }
  }

  # Rule 3: AWS Managed - XSS Protection
  rule {
    name     = "aws-xss-protection"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "permitai-${var.environment}-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  # Rule 4: AWS Managed - Common Rule Set (includes XSS)
  rule {
    name     = "aws-common-rules"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "permitai-${var.environment}-common-rules"
      sampled_requests_enabled   = true
    }
  }

  # Rule 5: Geographic restriction - US only for MVP
  rule {
    name     = "geo-restrict-us-only"
    priority = 5

    action {
      block {}
    }

    statement {
      not_statement {
        statement {
          geo_match_statement {
            country_codes = ["US"]
          }
        }
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "permitai-${var.environment}-geo-block"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "permitai-${var.environment}-waf"
    sampled_requests_enabled   = true
  }

  tags = {
    Environment = var.environment
    Project     = "PermitAI-LA"
  }
}

# --- Associate WAF with ALB ---

resource "aws_wafv2_web_acl_association" "alb" {
  resource_arn = var.alb_arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn
}

# --- CloudWatch Logging for WAF ---

resource "aws_cloudwatch_log_group" "waf" {
  name              = "aws-waf-logs-permitai-${var.environment}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
    Project     = "PermitAI-LA"
  }
}

resource "aws_wafv2_web_acl_logging_configuration" "main" {
  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
  resource_arn            = aws_wafv2_web_acl.main.arn
}

# --- Outputs ---

output "web_acl_arn" {
  description = "ARN of the WAF WebACL"
  value       = aws_wafv2_web_acl.main.arn
}

output "web_acl_id" {
  description = "ID of the WAF WebACL"
  value       = aws_wafv2_web_acl.main.id
}
