use crate::decoder::FileTypeDecoder;
use crate::error::{RegistryError, Result};
use crate::types::{ConfigStructure, ConfigValue};

pub struct TomlDecoder;

impl TomlDecoder {
    pub fn new() -> Self {
        TomlDecoder
    }
}

impl Default for TomlDecoder {
    fn default() -> Self {
        Self::new()
    }
}

impl FileTypeDecoder for TomlDecoder {
    fn decode(&self, content: &str, _structure: &ConfigStructure) -> Result<ConfigValue> {
        let value: toml::Value =
            toml::from_str(content).map_err(|e| RegistryError::DecodingError(e.to_string()))?;
        toml_to_config_value(value)
    }

    fn encode(&self, data: &ConfigValue, _structure: &ConfigStructure) -> Result<String> {
        let toml_value = config_value_to_toml(data)?;
        toml::to_string_pretty(&toml_value).map_err(|e| RegistryError::EncodingError(e.to_string()))
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
        "toml"
    }
}

fn toml_to_config_value(value: toml::Value) -> Result<ConfigValue> {
    match value {
        toml::Value::String(s) => Ok(ConfigValue::String(s)),
        toml::Value::Integer(i) => Ok(ConfigValue::Integer(i)),
        toml::Value::Float(f) => Ok(ConfigValue::Float(f)),
        toml::Value::Boolean(b) => Ok(ConfigValue::Boolean(b)),
        toml::Value::Datetime(dt) => Ok(ConfigValue::String(dt.to_string())),
        toml::Value::Array(arr) => {
            let values: Result<Vec<ConfigValue>> =
                arr.into_iter().map(toml_to_config_value).collect();
            Ok(ConfigValue::Array(values?))
        }
        toml::Value::Table(table) => {
            let mut map = std::collections::HashMap::new();
            for (k, v) in table {
                map.insert(k, toml_to_config_value(v)?);
            }
            Ok(ConfigValue::Object(map))
        }
    }
}

fn config_value_to_toml(value: &ConfigValue) -> Result<toml::Value> {
    match value {
        ConfigValue::String(s) => Ok(toml::Value::String(s.clone())),
        ConfigValue::Integer(i) => Ok(toml::Value::Integer(*i)),
        ConfigValue::Float(f) => Ok(toml::Value::Float(*f)),
        ConfigValue::Boolean(b) => Ok(toml::Value::Boolean(*b)),
        ConfigValue::Array(arr) => {
            let values: Result<Vec<toml::Value>> = arr.iter().map(config_value_to_toml).collect();
            Ok(toml::Value::Array(values?))
        }
        ConfigValue::Object(map) => {
            let mut table = toml::map::Map::new();
            for (k, v) in map {
                table.insert(k.clone(), config_value_to_toml(v)?);
            }
            Ok(toml::Value::Table(table))
        }
        ConfigValue::Null => Ok(toml::Value::String(String::new())),
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
    fn test_toml_decode() {
        let decoder = TomlDecoder::new();
        let structure = ConfigStructure {
            file: crate::types::FileInfo {
                location: String::new(),
            },
            format: None,
            schema: None,
            formatting: None,
            validation: None,
        };

        let result = decoder.decode("key = \"value\"", &structure);
        assert!(result.is_ok());
    }
}
