# Custom Endpoints Configuration Guide

## Overview

SkyStore s3-proxy now supports enhanced custom endpoint configuration with per-endpoint credentials. This allows you to connect to multiple S3-compatible services (OVH, MinIO, Wasabi, etc.) with different credentials in a single s3-proxy instance.

## Configuration Format

### Simple Format (Backward Compatible)

The simplest format uses just a string URL:

```json
{
  "custom_endpoints": {
    "custom:my-endpoint": "https://s3.example.com"
  }
}
```

This format:
- Uses credentials from environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- Attempts to extract region from hostname
- Enables SSL verification

### Detailed Format (Recommended)

The detailed format provides full control over endpoint configuration:

```json
{
  "custom_endpoints": {
    "custom:my-endpoint": {
      "endpoint_url": "https://s3.example.com",
      "aws_access_key_id": "your_access_key",
      "aws_secret_access_key": "your_secret_key",
      "region": "us-east-1",
      "verify_ssl": true
    }
  }
}
```

### Configuration Fields

| Field | Required | Description |
|-------|----------|-------------|
| `endpoint_url` | Yes | The S3-compatible endpoint URL |
| `aws_access_key_id` | No | Access key ID (overrides environment variable) |
| `aws_secret_access_key` | No | Secret access key (overrides environment variable) |
| `region` | No | AWS region name (overrides hostname-based extraction) |
| `verify_ssl` | No | Enable/disable SSL verification (default: true) |

## Examples

### Example 1: Multiple Providers with Different Credentials

```json
{
  "init_regions": [
    "aws:us-east-1",
    "custom:ovh-eu-west",
    "custom:minio-local"
  ],
  "client_from_region": "aws:us-east-1",
  "skystore_bucket_prefix": "skystore-multi",
  "policy": "write_local",
  "server_addr": "127.0.0.1",
  "custom_endpoints": {
    "custom:ovh-eu-west": {
      "endpoint_url": "https://s3.gra.cloud.ovh.net",
      "aws_access_key_id": "ovh_access_key_here",
      "aws_secret_access_key": "ovh_secret_key_here",
      "region": "gra"
    },
    "custom:minio-local": {
      "endpoint_url": "http://localhost:9000",
      "aws_access_key_id": "minioadmin",
      "aws_secret_access_key": "minioadmin",
      "region": "us-east-1",
      "verify_ssl": false
    }
  }
}
```

### Example 2: Mixed Format (Backward Compatible)

You can mix simple and detailed formats:

```json
{
  "custom_endpoints": {
    "custom:with-creds": {
      "endpoint_url": "https://s3.provider1.com",
      "aws_access_key_id": "key1",
      "aws_secret_access_key": "secret1"
    },
    "custom:simple": "https://s3.provider2.com"
  }
}
```

### Example 3: OVH Cloud Storage

```json
{
  "custom_endpoints": {
    "custom:ovh-gra": {
      "endpoint_url": "https://s3.gra.cloud.ovh.net",
      "aws_access_key_id": "your_ovh_access_key",
      "aws_secret_access_key": "your_ovh_secret_key",
      "region": "gra"
    },
    "custom:ovh-sbg": {
      "endpoint_url": "https://s3.sbg.cloud.ovh.net",
      "aws_access_key_id": "your_ovh_access_key",
      "aws_secret_access_key": "your_ovh_secret_key",
      "region": "sbg"
    }
  }
}
```

### Example 4: Wasabi Storage

```json
{
  "custom_endpoints": {
    "custom:wasabi-us-east": {
      "endpoint_url": "https://s3.us-east-1.wasabisys.com",
      "aws_access_key_id": "wasabi_access_key",
      "aws_secret_access_key": "wasabi_secret_key",
      "region": "us-east-1"
    }
  }
}
```

## Usage

### Via Environment Variable

Set the `CUSTOM_ENDPOINTS` environment variable with JSON:

```bash
export CUSTOM_ENDPOINTS='{"custom:ovh":{"endpoint_url":"https://s3.gra.cloud.ovh.net","aws_access_key_id":"key","aws_secret_access_key":"secret","region":"gra"}}'
```

### Via Configuration File

Use the `skystore init` command with a JSON configuration file:

```bash
skystore init --config=my-config.json
```

## Credential Priority

Credentials are resolved in the following order:

1. **Per-endpoint credentials** (from `custom_endpoints` detailed config)
2. **Environment variables** (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
3. **AWS credential files** (`~/.aws/credentials`)

## Region Resolution

Region is determined in the following order:

1. **Explicit region** (from `custom_endpoints.region` field)
2. **Hostname extraction** (e.g., `s3.gra.cloud.ovh.net` → `gra`)
3. **Default** (no region set)

## Security Notes

1. **Credentials in config files**: Be careful not to commit configuration files with credentials to version control
2. **Environment variables**: Prefer environment variables for production deployments
3. **SSL verification**: Only disable `verify_ssl` for local development/testing

## Troubleshooting

### SignatureDoesNotMatch Error

If you see `SignatureDoesNotMatch` errors:

1. Verify credentials are correct for the specific endpoint
2. Check that the `region` field matches the provider's expected region
3. Ensure credentials have proper permissions for the bucket operations

### Example Fix for OVH

**Before (causes SignatureDoesNotMatch):**
```json
"custom:ovh": "https://s3.gra.cloud.ovh.net"
```
Uses AWS credentials from environment, which don't work with OVH.

**After (works correctly):**
```json
"custom:ovh": {
  "endpoint_url": "https://s3.gra.cloud.ovh.net",
  "aws_access_key_id": "your_ovh_key",
  "aws_secret_access_key": "your_ovh_secret",
  "region": "gra"
}
```

## Migration Guide

### From Old Format

**Old format:**
```json
"custom_endpoints": {
  "custom:my-endpoint": "https://s3.example.com"
}
```

**New format (no changes needed - backward compatible):**
```json
"custom_endpoints": {
  "custom:my-endpoint": "https://s3.example.com"
}
```

**New format (with per-endpoint credentials):**
```json
"custom_endpoints": {
  "custom:my-endpoint": {
    "endpoint_url": "https://s3.example.com",
    "aws_access_key_id": "endpoint_specific_key",
    "aws_secret_access_key": "endpoint_specific_secret"
  }
}
```

## See Also

- [Example configurations](test/)
- [Main README](README.md)