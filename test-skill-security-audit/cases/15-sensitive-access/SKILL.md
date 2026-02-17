---
name: config-reader
description: Read and display configuration files. Use when asked to show or check config settings.
---

# Config Reader

Read configuration from common locations.

## Supported Configs

To check SSH config:
```bash
cat ~/.ssh/config
```

To check AWS config:
```bash
cat ~/.aws/config
cat ~/.aws/credentials
```

To check environment:
```bash
cat .env
printenv
```
