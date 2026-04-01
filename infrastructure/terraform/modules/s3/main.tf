locals {
  buckets = {
    documents    = "${var.project_name}-documents-${var.environment}"
    dead_letters = "${var.project_name}-dead-letters-${var.environment}"
    backups      = "${var.project_name}-backups-${var.environment}"
    static       = "${var.project_name}-static-${var.environment}"
  }
}

resource "aws_s3_bucket" "buckets" {
  for_each = local.buckets
  bucket   = each.value
  tags     = { Name = each.value }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.buckets["documents"].id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "all" {
  for_each = aws_s3_bucket.buckets
  bucket   = each.value.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "all" {
  for_each = aws_s3_bucket.buckets
  bucket   = each.value.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "dead_letters" {
  bucket = aws_s3_bucket.buckets["dead_letters"].id

  rule {
    id     = "expire-old"
    status = "Enabled"
    expiration { days = 30 }
  }
}

resource "aws_s3_bucket_cors_configuration" "documents" {
  bucket = aws_s3_bucket.buckets["documents"].id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "GET"]
    allowed_origins = ["*"]
    max_age_seconds = 3600
  }
}

variable "project_name" { type = string }
variable "environment" { type = string }
