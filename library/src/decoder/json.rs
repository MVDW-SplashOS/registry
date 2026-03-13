use crate::decoder::FileTypeDecoder;
use crate::error::{RegistryError, Result};
use crate::types::{ConfigStructure, ConfigValue};
use crate::utils::{get_value_type, type_matches, validate_rule as shared_validate_rule};

pub struct JsonDecoder;

impl JsonDecoder {
    pub fn new() -> Self {
        JsonDecoder
    }
}

impl Default for JsonDecoder {
    fn default() -> Self {
        Self::new()
    }
}

impl FileTypeDecoder for JsonDecoder {
    fn decode(&self, content: &str, _structure: &ConfigStructure) -> Result<ConfigValue> {
        serde_json::from_str(content).map_err(|e| RegistryError::DecodingError(e.to_string()))
    }

    fn encode(&self, data: &ConfigValue, _structure: &ConfigStructure) -> Result<String> {
        serde_json::to_string_pretty(data).map_err(|e| RegistryError::EncodingError(e.to_string()))
    }

    fn validate(&self, data: &ConfigValue, structure: &ConfigStructure) -> Result<Vec<String>> {
        let mut errors = Vec::new();

        if let Some(schema) = &structure.schema {
            if let Some(required) = &schema.required {
                if let ConfigValue::Object(map) = data {
                    for field in required {
                        if !map.contains_key(field) {
                            errors.push(format!("Required field missing: {}", field));
                        }
                    }

                    if let Some(props) = &schema.properties {
                        for (field, value) in map {
                            if let Some(prop_schema) = props.get(field) {
                                if let Some(expected_type) = &prop_schema.r#type {
                                    let actual_type = get_value_type(value);

                                    if !type_matches(&actual_type, expected_type) {
                                        errors.push(format!(
                                            "Field {} must be a {}",
                                            field, expected_type
                                        ));
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        if let Some(validation) = &structure.validation {
            for rule in &validation.rules {
                let rule_errors = shared_validate_rule(data, rule);
                errors.extend(rule_errors);
            }
        }

        Ok(errors)
    }

    fn name(&self) -> &str {
        "json"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_json_decode() {
        let decoder = JsonDecoder::new();
        let structure = ConfigStructure {
            file: crate::types::FileInfo {
                location: String::new(),
            },
            format: None,
            schema: None,
            formatting: None,
            validation: None,
        };

        let result = decoder.decode(r#"{"key": "value"}"#, &structure);
        assert!(result.is_ok());
    }

    #[test]
    fn test_json_encode() {
        let decoder = JsonDecoder::new();
        let structure = ConfigStructure {
            file: crate::types::FileInfo {
                location: String::new(),
            },
            format: None,
            schema: None,
            formatting: None,
            validation: None,
        };

        let data = ConfigValue::String("test".to_string());
        let result = decoder.encode(&data, &structure);
        assert!(result.is_ok());
    }
}
