use crate::decoder::FileTypeDecoder;
use crate::error::{RegistryError, Result};
use crate::types::{ConfigStructure, ConfigValue};

pub struct YamlDecoder;

impl YamlDecoder {
    pub fn new() -> Self {
        YamlDecoder
    }
}

impl Default for YamlDecoder {
    fn default() -> Self {
        Self::new()
    }
}

impl FileTypeDecoder for YamlDecoder {
    fn decode(&self, content: &str, _structure: &ConfigStructure) -> Result<ConfigValue> {
        serde_yaml::from_str(content).map_err(|e| RegistryError::DecodingError(e.to_string()))
    }

    fn encode(&self, data: &ConfigValue, _structure: &ConfigStructure) -> Result<String> {
        serde_yaml::to_string(data).map_err(|e| RegistryError::EncodingError(e.to_string()))
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
                }
            }
        }

        if let Some(validation) = &structure.validation {
            for rule in &validation.rules {
                let rule_errors = validate_rule(data, rule);
                errors.extend(rule_errors);
            }
        }

        Ok(errors)
    }

    fn name(&self) -> &str {
        "yaml"
    }
}

fn validate_rule(data: &ConfigValue, rule: &crate::types::ValidationRule) -> Vec<String> {
    let mut errors = Vec::new();

    match rule.r#type.as_str() {
        "required" => {
            if let Some(field) = &rule.field {
                if let ConfigValue::Object(map) = data {
                    if !map.contains_key(field) {
                        errors.push(format!("Required field missing: {}", field));
                    }
                }
            }
        }
        "type" => {
            if let (Some(field), Some(expected_type)) = (&rule.field, &rule.expected_type) {
                if let ConfigValue::Object(map) = data {
                    if let Some(value) = map.get(field) {
                        let actual_type = match value {
                            ConfigValue::String(_) => "string",
                            ConfigValue::Integer(_) => "integer",
                            ConfigValue::Float(_) => "number",
                            ConfigValue::Boolean(_) => "boolean",
                            ConfigValue::Array(_) => "array",
                            ConfigValue::Object(_) => "object",
                            ConfigValue::Null => "null",
                        };
                        if !type_matches(actual_type, expected_type) {
                            errors.push(format!("Field {} must be a {}", field, expected_type));
                        }
                    }
                }
            }
        }
        "range" => {
            if let (Some(field), Some(min), Some(max)) = (&rule.field, rule.min, rule.max) {
                if let ConfigValue::Object(map) = data {
                    if let Some(value) = map.get(field) {
                        if let ConfigValue::Integer(i) = value {
                            if *i < min as i64 {
                                errors.push(format!("Field {} must be >= {}", field, min));
                            }
                            if *i > max as i64 {
                                errors.push(format!("Field {} must be <= {}", field, max));
                            }
                        } else if let ConfigValue::Float(f) = value {
                            if *f < min {
                                errors.push(format!("Field {} must be >= {}", field, min));
                            }
                            if *f > max {
                                errors.push(format!("Field {} must be <= {}", field, max));
                            }
                        }
                    }
                }
            }
        }
        "enum" => {
            if let (Some(field), Some(allowed)) = (&rule.field, &rule.allowed_values) {
                if let ConfigValue::Object(map) = data {
                    if let Some(value) = map.get(field) {
                        if !allowed.contains(value) {
                            errors.push(format!("Field {} must be one of: {:?}", field, allowed));
                        }
                    }
                }
            }
        }
        "pattern" => {
            if let (Some(field), Some(pattern)) = (&rule.field, &rule.pattern) {
                if let ConfigValue::Object(map) = data {
                    if let Some(ConfigValue::String(s)) = map.get(field) {
                        if let Ok(re) = regex::Regex::new(pattern) {
                            if !re.is_match(s) {
                                errors.push(format!(
                                    "Field {} must match pattern: {}",
                                    field, pattern
                                ));
                            }
                        }
                    }
                }
            }
        }
        _ => {}
    }

    errors
}

fn type_matches(actual: &str, expected: &str) -> bool {
    match expected {
        "string" => actual == "string",
        "number" => actual == "number" || actual == "integer",
        "integer" => actual == "integer",
        "boolean" => actual == "boolean",
        "array" => actual == "array",
        "object" => actual == "object",
        _ => true,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_yaml_decode() {
        let decoder = YamlDecoder::new();
        let structure = ConfigStructure {
            file: crate::types::FileInfo {
                location: String::new(),
            },
            format: None,
            schema: None,
            formatting: None,
            validation: None,
        };

        let result = decoder.decode("key: value", &structure);
        assert!(result.is_ok());
    }
}
