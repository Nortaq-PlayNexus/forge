"""Infrastructure provisioner.

Generates Terraform configs, Dockerfiles, and deployment manifests.
"""

from pathlib import Path
from typing import Optional


def generate_terraform(stack, provider: str = "aws", region: str = "us-east-1") -> str:
    """Generate Terraform configuration for the detected stack."""
    services = stack.services or []
    has_db = any(s in services for s in ["postgres", "mysql", "mongo"])
    has_redis = "redis" in services

    provider_block = {
        "aws": f'''provider "aws" {{
  region = "{region}"
}}

variable "project_name" {{
  default = "forge-deploy"
}}

variable "environment" {{
  default = "production"
}}''',
        "gcp": f'''provider "google" {{
  project = var.project_name
  region  = "{region}"
}}

variable "project_name" {{
  default = "forge-deploy"
}}

variable "environment" {{
  default = "production"
}}''',
        "azure": f'''provider "azurerm" {{
  features {{}}
}}

variable "project_name" {{
  default = "forge-deploy"
}}

variable "environment" {{
  default = "production"
}}''',
    }

    resources = []

    if provider == "aws":
        resources.append('''
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"

  container_definitions = jsonencode([{
    name  = "app"
    image = "${aws_ecr_repository.app.repository_url}:latest"
    portMappings = [{
      containerPort = ''' + str(stack.port or 8080) + '''
      hostPort      = ''' + str(stack.port or 8080) + '''
    }]
  }])
}

resource "aws_ecr_repository" "app" {
  name = "${var.project_name}"
}''')

        if has_db:
            resources.append('''
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.micro"

  db_name  = "appdb"
  username = "admin"
  password = var.db_password

  skip_final_snapshot = true
}

variable "db_password" {
  sensitive = true
}''')

        if has_redis:
            resources.append('''
resource "aws_elasticache_cluster" "cache" {
  cluster_id      = "${var.project_name}-cache"
  engine          = "redis"
  node_type       = "cache.t3.micro"
  num_cache_nodes = 1
  port            = 6379
}''')

    elif provider == "gcp":
        resources.append('''
resource "google_cloud_run_service" "app" {
  name     = "${var.project_name}"
  location = "''' + region + '''"

  template {
    spec {
      containers {
        image = "gcr.io/${var.project_name}/app:latest"
        ports {
          container_port = ''' + str(stack.port or 8080) + '''
        }
      }
    }
  }
}

resource "google_artifact_registry_repository" "app" {
  location      = "''' + region + '''"
  repository_id = "${var.project_name}"
  format        = "DOCKER"
}''')

    elif provider == "azure":
        resources.append('''
resource "azurerm_container_group" "app" {
  name                = "${var.project_name}-app"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"

  container {
    name   = "app"
    image  = "${azurerm_container_registry.acr.login_server}/app:latest"
    cpu    = "0.5"
    memory = "1.0"

    ports {
      port     = ''' + str(stack.port or 8080) + '''
      protocol = "TCP"
    }
  }
}

resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-rg"
  location = "''' + region + '''"
}

resource "azurerm_container_registry" "acr" {
  name                = "${replace(var.project_name, "-", "")}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
}''')

    return f'''{provider_block.get(provider, provider_block["aws"])}

{"".join(resources)}
'''


def generate_dockerfile(stack) -> str:
    """Generate a Dockerfile for the detected stack."""
    lang = stack.primary_language
    fw = stack.primary_framework
    port = stack.port or 8080

    if lang == "python":
        return f'''FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE {port}

CMD ["python", "-m", "forge.app"]
'''
    elif lang == "node":
        return f'''FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE {port}

CMD ["node", "src/index.js"]
'''
    elif lang == "go":
        return f'''FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /app/server .

FROM alpine:3.19
COPY --from=builder /app/server /server
EXPOSE {port}
CMD ["/server"]
'''
    elif lang == "rust":
        return f'''FROM rust:1.77-slim AS builder

WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/app /app
EXPOSE {port}
CMD ["/app"]
'''
    elif lang == "java":
        return f'''FROM eclipse-temurin:21-jdk-alpine AS builder

WORKDIR /app
COPY . .
RUN ./gradlew build -x test

FROM eclipse-temurin:21-jre-alpine
COPY --from=builder /app/build/libs/*.jar /app.jar
EXPOSE {port}
CMD ["java", "-jar", "/app.jar"]
'''
    elif lang == "ruby":
        return f'''FROM ruby:3.3-slim

WORKDIR /app
COPY Gemfile Gemfile.lock ./
RUN bundle install
COPY . .

EXPOSE {port}
CMD ["bundle", "exec", "ruby", "app.rb"]
'''
    else:
        return f'''FROM alpine:3.19
WORKDIR /app
COPY . .
EXPOSE {port}
CMD ["./start.sh"]
'''


def generate_docker_compose(stack) -> str:
    """Generate docker-compose.yml for the detected stack."""
    port = stack.port or 8080
    services = []

    services.append(f'''  app:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - DATABASE_URL=postgres://postgres:postgres@db:5432/appdb
      - REDIS_URL=redis://cache:6379
    depends_on:
      - db
      - cache''')

    if any(s in stack.services for s in ["postgres"]):
        services.append('''  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"''')

    if "redis" in stack.services:
        services.append('''  cache:
    image: redis:7-alpine
    ports:
      - "6379:6379"''')

    volumes = "\nvolumes:\n  pgdata:" if any(s in stack.services for s in ["postgres"]) else ""

    return f'''version: "3.8"

services:
{"".join(services)}
{volumes}
'''


def generate_terraform_modules(stack, provider: str = "aws") -> dict[str, str]:
    """Generate Terraform module files."""
    main_tf = generate_terraform(stack, provider)
    variables_tf = '''variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}'''

    outputs_tf = '''output "app_url" {
  description = "Application endpoint URL"
  value       = aws_ecs_cluster.main.name
}

output "db_endpoint" {
  description = "Database endpoint"
  value       = aws_db_instance.main.endpoint
}'''

    return {
        "main.tf": main_tf,
        "variables.tf": variables_tf,
        "outputs.tf": outputs_tf,
    }
