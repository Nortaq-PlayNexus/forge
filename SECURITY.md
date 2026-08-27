# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | ✅ Active          |
| < latest | ❌ Not supported  |

## Reporting a Vulnerability

Please do **not** open a public issue. Report privately via GitHub's security advisory or email the maintainers.

Include a description, affected versions, reproduction steps, and impact. We acknowledge reports within 48 hours.

## Scope

Forge generates deployment configurations locally. It uses cloud CLIs (aws, gcloud, az) that you already have installed. Forge does not store credentials — it relies on your existing cloud CLI authentication.
