output "vpc_id" {
  value = module.vpc.vpc_id
}

output "api_url" {
  value = module.ecs.api_url
}

output "database_endpoint" {
  value     = module.rds.endpoint
  sensitive = true
}

output "redis_endpoint" {
  value     = module.elasticache.endpoint
  sensitive = true
}
