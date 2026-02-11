use serde::{Deserialize, Serialize};

/// Configuration for a custom S3-compatible endpoint
/// Supports both simple string format (backward compatible) and detailed object format
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(untagged)]
pub enum EndpointConfig {
    /// Simple string format: just the endpoint URL (backward compatible)
    Simple(String),
    /// Detailed configuration object with credentials and settings
    Detailed(EndpointDetails),
}

/// Detailed configuration for a custom endpoint
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct EndpointDetails {
    /// The endpoint URL (required)
    pub endpoint_url: String,
    
    /// AWS access key ID (optional, overrides environment variable)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub aws_access_key_id: Option<String>,
    
    /// AWS secret access key (optional, overrides environment variable)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub aws_secret_access_key: Option<String>,
    
    /// AWS region (optional, overrides hostname-based extraction)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub region: Option<String>,
    
    /// Whether to verify SSL certificates (optional, defaults to true)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub verify_ssl: Option<bool>,
}

impl EndpointConfig {
    /// Get the endpoint URL from either format
    pub fn get_endpoint_url(&self) -> String {
        match self {
            EndpointConfig::Simple(url) => url.clone(),
            EndpointConfig::Detailed(details) => details.endpoint_url.clone(),
        }
    }
    
    /// Get the detailed configuration, converting from simple format if needed
    pub fn get_details(&self) -> EndpointDetails {
        match self {
            EndpointConfig::Simple(url) => EndpointDetails {
                endpoint_url: url.clone(),
                aws_access_key_id: None,
                aws_secret_access_key: None,
                region: None,
                verify_ssl: None,
            },
            EndpointConfig::Detailed(details) => details.clone(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_simple_format_deserialization() {
        let json = r#""https://s3.example.com""#;
        let config: EndpointConfig = serde_json::from_str(json).unwrap();
        assert_eq!(config.get_endpoint_url(), "https://s3.example.com");
    }

    #[test]
    fn test_detailed_format_deserialization() {
        let json = r#"{
            "endpoint_url": "https://s3.example.com",
            "aws_access_key_id": "test_key",
            "aws_secret_access_key": "test_secret",
            "region": "us-east-1"
        }"#;
        let config: EndpointConfig = serde_json::from_str(json).unwrap();
        let details = config.get_details();
        assert_eq!(details.endpoint_url, "https://s3.example.com");
        assert_eq!(details.aws_access_key_id, Some("test_key".to_string()));
        assert_eq!(details.region, Some("us-east-1".to_string()));
    }
}

// Made with Bob
