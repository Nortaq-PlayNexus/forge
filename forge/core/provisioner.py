"""Infrastructure provisioner.

Generates Terraform configs, Dockerfiles, and deployment manifests.
"""



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
        "azure": '''provider "azurerm" {
  features {}
}

variable "project_name" {
  default = "forge-deploy"
}

variable "environment" {
  default = "production"
}''',
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
    """Generate a Dockerfile for the detected stack with multi-stage builds, non-root user, and health check."""
    lang = stack.primary_language
    fw = stack.primary_framework
    port = stack.port or 8080

    health_check = f"HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\\n  CMD curl -f http://localhost:{port}/health || exit 1"

    if lang == "python":
        return f'''FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE {port}
{health_check}

CMD ["python", "-m", "forge.app"]
'''
    elif lang == "node":
        return f'''FROM node:20-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

FROM node:20-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE {port}
{health_check}

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

RUN addgroup -S appuser && adduser -S appuser -G appuser

COPY --from=builder /app/server /server
RUN chown appuser:appuser /server
USER appuser

EXPOSE {port}
{health_check}

CMD ["/server"]
'''
    elif lang == "rust":
        return f'''FROM rust:1.77-slim AS builder

WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

COPY --from=builder /app/target/release/app /app
RUN chown appuser:appuser /app
USER appuser

EXPOSE {port}
{health_check}

CMD ["/app"]
'''
    elif lang == "java":
        return f'''FROM eclipse-temurin:21-jdk-alpine AS builder

WORKDIR /app
COPY . .
RUN ./gradlew build -x test

FROM eclipse-temurin:21-jre-alpine

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

COPY --from=builder /app/build/libs/*.jar /app.jar
RUN chown appuser:appuser /app.jar
USER appuser

EXPOSE {port}
{health_check}

CMD ["java", "-jar", "/app.jar"]
'''
    elif lang == "ruby":
        return f'''FROM ruby:3.3-slim AS builder

WORKDIR /app
COPY Gemfile Gemfile.lock ./
RUN bundle install

FROM ruby:3.3-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app
COPY --from=builder /usr/local/bundle /usr/local/bundle
COPY . .

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE {port}
{health_check}

CMD ["bundle", "exec", "ruby", "app.rb"]
'''
    else:
        return f'''FROM alpine:3.19

RUN addgroup -S appuser && adduser -S appuser -G appuser

WORKDIR /app
COPY . .
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE {port}
{health_check}

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


def generate_kubernetes(stack) -> dict[str, str]:
    """Generate K8s deployment.yaml, service.yaml, ingress.yaml."""
    port = stack.port or 8080
    app_name = "forge-app"

    deployment = f'''apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  labels:
    app: {app_name}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
        - name: {app_name}
          image: {app_name}:latest
          ports:
            - containerPort: {port}
          readinessProbe:
            httpGet:
              path: /health
              port: {port}
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: {port}
            initialDelaySeconds: 15
            periodSeconds: 20
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "500m"
'''

    service = f'''apiVersion: v1
kind: Service
metadata:
  name: {app_name}
spec:
  selector:
    app: {app_name}
  ports:
    - protocol: TCP
      port: 80
      targetPort: {port}
  type: ClusterIP
'''

    ingress = f'''apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {app_name}
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
    - host: {app_name}.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {app_name}
                port:
                  number: 80
'''

    return {
        "deployment.yaml": deployment,
        "service.yaml": service,
        "ingress.yaml": ingress,
    }


def generate_helm_chart(stack) -> dict[str, str]:
    """Generate a basic Helm chart structure."""
    port = stack.port or 8080
    app_name = "forge-app"

    chart_yaml = f'''apiVersion: v2
name: {app_name}
description: A Helm chart for {app_name}
type: application
version: 0.1.0
appVersion: "1.0.0"
'''

    values_yaml = f'''replicaCount: 2

image:
  repository: {app_name}
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: {app_name}.example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 500m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi

autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 10
'''

    deployment_tmpl = (
        'apiVersion: apps/v1\n'
        'kind: Deployment\n'
        'metadata:\n'
        '  name: ' + '{{ include "' + app_name + '.fullname" . }}' + '\n'
        '  labels:\n'
        '    ' + '{{- include "' + app_name + '.labels" . | nindent 4 }}' + '\n'
        'spec:\n'
        '  ' + '{{- if not .Values.autoscaling.enabled }}' + '\n'
        '  replicas: ' + '{{ .Values.replicaCount }}' + '\n'
        '  ' + '{{- end }}' + '\n'
        '  selector:\n'
        '    matchLabels:\n'
        '      ' + '{{- include "' + app_name + '.selectorLabels" . | nindent 6 }}' + '\n'
        '  template:\n'
        '    metadata:\n'
        '      labels:\n'
        '        ' + '{{- include "' + app_name + '.selectorLabels" . | nindent 8 }}' + '\n'
        '    spec:\n'
        '      containers:\n'
        '        - name: ' + '{{ .Chart.Name }}' + '\n'
        '          image: "' + '{{ .Values.image.repository }}' + ':' + '{{ .Values.image.tag }}' + '"\n'
        '          ports:\n'
        '            - containerPort: ' + str(port) + '\n'
        '          resources:\n'
        '            ' + '{{- toYaml .Values.resources | nindent 12 }}' + '\n'
    )

    helpers_tpl = (
        '{{- define "' + app_name + '.fullname" -}}\n'
        '{{- if .Values.fullnameOverride }}\n'
        '{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}\n'
        '{{- else }}\n'
        '{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}\n'
        '{{- end }}\n'
        '{{- end }}\n'
        '\n'
        '{{- define "' + app_name + '.labels" -}}\n'
        'helm.sh/chart: ' + '{{ .Chart.Name }}' + '-' + '{{ .Chart.Version }}' + '\n'
        '{{ include "' + app_name + '.selectorLabels" . }}\n'
        '{{- end }}\n'
        '\n'
        '{{- define "' + app_name + '.selectorLabels" -}}\n'
        'app: ' + '{{ .Chart.Name }}' + '\n'
        '{{- end }}\n'
    )

    return {
        "Chart.yaml": chart_yaml,
        "values.yaml": values_yaml,
        "templates/deployment.yaml": deployment_tmpl,
        "templates/_helpers.tpl": helpers_tpl,
    }


def generate_github_actions(stack, provider: str = "aws") -> str:
    """Generate GitHub Actions workflow."""
    app_name = "forge-app"
    return (
        'name: Deploy\n'
        '\n'
        'on:\n'
        '  push:\n'
        '    branches: [main]\n'
        '  workflow_dispatch:\n'
        '\n'
        'env:\n'
        '  APP_NAME: ' + app_name + '\n'
        '  PROVIDER: ' + provider + '\n'
        '\n'
        'jobs:\n'
        '  build-and-deploy:\n'
        '    runs-on: ubuntu-latest\n'
        '    steps:\n'
        '      - uses: actions/checkout@v4\n'
        '\n'
        '      - name: Set up Docker Buildx\n'
        '        uses: docker/setup-buildx-action@v3\n'
        '\n'
        '      - name: Build Docker image\n'
        '        run: docker build -t ${{ env.APP_NAME }}:${{ github.sha }} .\n'
        '\n'
        '      - name: Run tests\n'
        '        run: echo "Add your test commands here"\n'
        '\n'
        '      - name: Deploy\n'
        '        run: echo "Deploy to ' + provider.upper() + ' using the generated Terraform files"\n'
    )


def generate_gitlab_ci(stack, provider: str = "aws") -> str:
    """Generate GitLab CI configuration."""
    app_name = "forge-app"
    return (
        'stages:\n'
        '  - build\n'
        '  - test\n'
        '  - deploy\n'
        '\n'
        'variables:\n'
        '  APP_NAME: ' + app_name + '\n'
        '\n'
        'build:\n'
        '  stage: build\n'
        '  image: docker:latest\n'
        '  services:\n'
        '    - docker:dind\n'
        '  script:\n'
        '    - docker build -t ${APP_NAME}:${CI_COMMIT_SHA} .\n'
        '    - docker tag ${APP_NAME}:${CI_COMMIT_SHA} ${APP_NAME}:latest\n'
        '  only:\n'
        '    - main\n'
        '\n'
        'test:\n'
        '  stage: test\n'
        '  script:\n'
        '    - echo "Add your test commands here"\n'
        '  only:\n'
        '    - main\n'
        '\n'
        'deploy:\n'
        '  stage: deploy\n'
        '  script:\n'
        '    - echo "Deploy to ' + provider.upper() + ' using the generated Terraform files"\n'
        '  only:\n'
        '    - main\n'
        '  when: manual\n'
    )
