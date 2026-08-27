<h1 align="center">Forge</h1>

<p align="center">
  <em>Universal Deploy Engine — Deploy any stack to any cloud from a single command.</em>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-cyan.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <img src="https://img.shields.io/badge/CLI-enabled-brightgreen.svg" alt="CLI">
</p>

---

## What it does

Forge detects your project's tech stack, generates deployment infrastructure (Terraform + Docker), estimates costs, and deploys to AWS, GCP, or Azure — all from one command.

**No vendor lock-in. No YAML hell. No cloud console hopping.**

---

## Screenshots

| Preview | Description |
|---------|-------------|
| Terminal output screenshots coming soon | |

---

## Quick start

```bash
# Install
pip install -e .

# Detect your stack
forge detect

# Preview what will be deployed
forge preview --provider aws

# Generate deployment files
forge init --provider gcp

# Deploy (requires cloud CLI configured)
forge deploy --provider aws -y
```

---

## Commands

| Command | Description |
|---------|-------------|
| `forge detect [path]` | Scan a directory and identify the tech stack |
| `forge providers` | List available cloud providers and auth status |
| `forge preview [path]` | Preview deployment plan + cost estimate |
| `forge init [path]` | Generate Dockerfile + Terraform configs |
| `forge deploy [path]` | Full deploy with confirmation prompt |

---

## Supported stacks

| Language | Frameworks |
|----------|------------|
| Python | Django, Flask, FastAPI |
| Node.js | Express, Next.js |
| Go | Gin, standard |
| Rust | Actix-web |
| Java | Spring Boot |
| Ruby | Rails |

---

## Supported clouds

| Provider | Services |
|----------|----------|
| **AWS** | ECS Fargate, ECR, RDS, ElastiCache |
| **GCP** | Cloud Run, Artifact Registry, Cloud SQL |
| **Azure** | Container Instances, ACR, Azure DB |

---

## How it works

```
forge deploy --provider aws
    │
    ├─ Detect stack (Python + FastAPI + PostgreSQL + Redis)
    ├─ Check AWS CLI (✓ authenticated: 123456789012)
    ├─ Preview deployment (ECS Fargate + RDS + ElastiCache)
    ├─ Estimate cost (~$52/mo)
    ├─ Generate Dockerfile + Terraform configs
    └─ Output next steps for terraform apply
```

---

## Cost estimation

Forge provides rough monthly cost estimates before deploying:

```
╭─────── Monthly Cost Estimate ────────╮
│ Component          │           Cost  │
│────────────────────│────────────────│
│ Compute            │        $10.00  │
│ Database           │        $15.00  │
│ Cache              │        $12.00  │
│ Storage            │         $5.00  │
│ Networking         │         $5.00  │
│────────────────────│────────────────│
│ Total              │        $47.00  │
╰──────────────────────────────────────╯
```

---

## Requirements

- Python 3.10+
- Cloud CLI configured (`aws`, `gcloud`, or `az`) for deploy commands

---

## Contributing

We welcome contributions! Please see:

- [Contributing Guide](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)

---

## License

MIT — see [LICENSE](LICENSE)
