# Lord-of-the-Mods
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.5.x   | :white_check_mark: |

## Reporting a Vulnerability

Lord of the Mods processes untrusted binary `.big` archives and `.ini`/`.inc`/`.str` configuration files. If you discover a security vulnerability (such as a path traversal or `#include` virtual chroot evasion, integer or 32-bit SAGE buffer overflow, or memory/stack exhaustion exploit):

1. **Do not open a public GitHub issue.**
2. Send a vulnerability report directly to [blazej.chojnacki@outlook.com](mailto:blazej.chojnacki@outlook.com).
3. Include a minimal reproduction case (e.g., a sample malformed `.big` or `.ini` file) and details of the expected vs. observed behavior.

Security reports will be acknowledged within 48 hours, and a patch will be released before public disclosure.
