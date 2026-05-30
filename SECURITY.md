# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | ✅ Yes             |
| < latest | ❌ No              |

This project follows a rolling-release model. Only the latest version receives security updates.

## Reporting a Vulnerability

If you discover a security vulnerability in this project, **please do not open a public issue**. Instead, report it privately.

### How to report

1. **Email**: [INSERT CONTACT EMAIL] with the subject line "Security Vulnerability: [brief description]"
2. **Include**:
   - A description of the vulnerability
   - Steps to reproduce (proof of concept or example is helpful)
   - Potential impact
   - Suggested fix (if known)

### What to expect

- **Acknowledgement**: Within 48 hours, you'll receive confirmation that we've received your report.
- **Assessment**: We'll investigate and determine the severity and impact.
- **Resolution**: A fix will be developed and released as soon as possible, depending on severity.
- **Disclosure**: Once a fix is released, we'll credit you in the release notes (unless you prefer to remain anonymous).

## Scope

This policy covers the Python calculator code, the FastAPI backend, and the React frontend. Dependencies (pip packages, npm packages) should have their own vulnerabilities reported to their respective maintainers.

## Data Handling

This tool processes financial transaction data. By design:
- All calculation data is ephemeral (stored only for the duration of the API session or until the user clears their results).
- No personal data is collected, stored, or transmitted beyond what is necessary for the calculation.
- File uploads are processed in memory and not persisted on the server (unless DynamoDB persistence is configured).

See the [Future Direction](docs/design/future_direction.md) document for details on the project's privacy-by-design approach.
