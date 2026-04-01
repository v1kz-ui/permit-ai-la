# ============================================================================
# CloudWatch Monitoring Module for PermitAI LA
# ============================================================================

variable "environment" {
  description = "Deployment environment (e.g., staging, production)"
  type        = string
}

variable "alarm_email" {
  description = "Email address for alarm notifications"
  type        = string
}

variable "retention_days" {
  description = "Log retention period in days"
  type        = number
  default     = 30
}

# --- SNS Topic for Alarm Notifications ---

resource "aws_sns_topic" "alarms" {
  name = "permitai-${var.environment}-alarms"

  tags = {
    Environment = var.environment
    Project     = "PermitAI-LA"
  }
}

resource "aws_sns_topic_subscription" "alarm_email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# --- CloudWatch Log Groups ---

resource "aws_cloudwatch_log_group" "api" {
  name              = "/permitai/${var.environment}/api"
  retention_in_days = var.retention_days

  tags = {
    Environment = var.environment
    Project     = "PermitAI-LA"
  }
}

resource "aws_cloudwatch_log_group" "airflow" {
  name              = "/permitai/${var.environment}/airflow"
  retention_in_days = var.retention_days

  tags = {
    Environment = var.environment
    Project     = "PermitAI-LA"
  }
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/permitai/${var.environment}/application"
  retention_in_days = var.retention_days

  tags = {
    Environment = var.environment
    Project     = "PermitAI-LA"
  }
}

# --- CloudWatch Metric Filters ---

resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "permitai-${var.environment}-api-errors"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ $.status_code >= 500 }"

  metric_transformation {
    name          = "APIServerErrors"
    namespace     = "PermitAI/${var.environment}"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_log_metric_filter" "api_requests" {
  name           = "permitai-${var.environment}-api-requests"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ $.status_code = * }"

  metric_transformation {
    name          = "APITotalRequests"
    namespace     = "PermitAI/${var.environment}"
    value         = "1"
    default_value = "0"
  }
}

# --- CloudWatch Alarms ---

resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "permitai-${var.environment}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  threshold           = 5
  alarm_description   = "API error rate exceeds 5% of total requests"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  metric_query {
    id          = "error_rate"
    expression  = "(errors / requests) * 100"
    label       = "Error Rate %"
    return_data = true
  }

  metric_query {
    id = "errors"

    metric {
      metric_name = "APIServerErrors"
      namespace   = "PermitAI/${var.environment}"
      period      = 300
      stat        = "Sum"
    }
  }

  metric_query {
    id = "requests"

    metric {
      metric_name = "APITotalRequests"
      namespace   = "PermitAI/${var.environment}"
      period      = 300
      stat        = "Sum"
    }
  }

  tags = {
    Environment = var.environment
    Project     = "PermitAI-LA"
  }
}

resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "permitai-${var.environment}-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "p99"
  threshold           = 3
  alarm_description   = "P99 API latency exceeds 3 seconds"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  tags = {
    Environment = var.environment
    Project     = "PermitAI-LA"
  }
}

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "permitai-${var.environment}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "ECS service CPU utilization exceeds 80%"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  dimensions = {
    ClusterName = "permitai-${var.environment}"
    ServiceName = "permitai-api"
  }

  tags = {
    Environment = var.environment
    Project     = "PermitAI-LA"
  }
}

resource "aws_cloudwatch_metric_alarm" "low_disk_space" {
  alarm_name          = "permitai-${var.environment}-low-disk-space"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS free storage is critically low"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  dimensions = {
    DBInstanceIdentifier = "permitai-${var.environment}"
  }

  tags = {
    Environment = var.environment
    Project     = "PermitAI-LA"
  }
}

# --- CloudWatch Dashboard ---

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "permitai-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "API Request Count"
          metrics = [["PermitAI/${var.environment}", "APITotalRequests", { stat = "Sum", period = 300 }]]
          view    = "timeSeries"
          region  = "us-west-2"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "API Server Errors (5xx)"
          metrics = [["PermitAI/${var.environment}", "APIServerErrors", { stat = "Sum", period = 300 }]]
          view    = "timeSeries"
          region  = "us-west-2"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title = "ECS CPU Utilization"
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ClusterName", "permitai-${var.environment}", "ServiceName", "permitai-api", { stat = "Average", period = 300 }]
          ]
          view   = "timeSeries"
          region = "us-west-2"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title = "ECS Memory Utilization"
          metrics = [
            ["AWS/ECS", "MemoryUtilization", "ClusterName", "permitai-${var.environment}", "ServiceName", "permitai-api", { stat = "Average", period = 300 }]
          ]
          view   = "timeSeries"
          region = "us-west-2"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          title = "RDS Free Storage Space"
          metrics = [
            ["AWS/RDS", "FreeStorageSpace", "DBInstanceIdentifier", "permitai-${var.environment}", { stat = "Average", period = 300 }]
          ]
          view   = "timeSeries"
          region = "us-west-2"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          title = "API Response Time (P99)"
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { stat = "p99", period = 300 }]
          ]
          view   = "timeSeries"
          region = "us-west-2"
        }
      }
    ]
  })
}

# --- Outputs ---

output "sns_topic_arn" {
  description = "ARN of the alarm notification SNS topic"
  value       = aws_sns_topic.alarms.arn
}

output "api_log_group_name" {
  description = "Name of the API CloudWatch log group"
  value       = aws_cloudwatch_log_group.api.name
}

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}
