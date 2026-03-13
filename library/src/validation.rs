use crate::error::{RegistryError, Result};
use crate::types::{ConfigStructure, ConfigValue, ValidationRule};

pub fn validate(data: &ConfigValue, structure: &ConfigStructure) -> Result<Vec<String>> {
    let mut errors = Vec::new();

    if let Some(schema) = &structure.schema {
        errors.extend(validate_schema(data, schema)?);
    }

    if let Some(validation) = &structure.validation {
        for rule in &validation.rules {
            errors.extend(validate_rule(data, rule));
        }
    }

    Ok(errors)
}

fn validate_schema(data: &ConfigValue, schema: &crate::types::Schema) -> Result<Vec<String>> {
    let mut errors = Vec::new();

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
                                    "Field '{}' expected type '{}', got '{}'",
                                    field, expected_type, actual_type
                                ));
                            }
                        }
                    }
                }
            }
        }
    } else if let Some(props) = &schema.properties {
        if let ConfigValue::Object(map) = data {
            for (field, value) in map {
                if let Some(prop_schema) = props.get(field) {
                    if let Some(expected_type) = &prop_schema.r#type {
                        let actual_type = get_value_type(value);
                        if !type_matches(&actual_type, expected_type) {
                            errors.push(format!(
                                "Field '{}' expected type '{}', got '{}'",
                                field, expected_type, actual_type
                            ));
                        }
                    }
                }
            }
        }
    }

    Ok(errors)
}

fn validate_rule(data: &ConfigValue, rule: &ValidationRule) -> Vec<String> {
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
                        let actual_type = get_value_type(value);
                        if !type_matches(&actual_type, expected_type) {
                            errors.push(format!("Field '{}' must be a {}", field, expected_type));
                        }
                    }
                }
            }
        }
        "range" => {
            if let (Some(field), Some(min), Some(max)) = (&rule.field, rule.min, rule.max) {
                if let ConfigValue::Object(map) = data {
                    if let Some(value) = map.get(field) {
                        match value {
                            ConfigValue::Integer(i) => {
                                if *i < min as i64 {
                                    errors.push(format!("Field '{}' must be >= {}", field, min));
                                }
                                if *i > max as i64 {
                                    errors.push(format!("Field '{}' must be <= {}", field, max));
                                }
                            }
                            ConfigValue::Float(f) => {
                                if *f < min {
                                    errors.push(format!("Field '{}' must be >= {}", field, min));
                                }
                                if *f > max {
                                    errors.push(format!("Field '{}' must be <= {}", field, max));
                                }
                            }
                            _ => {}
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
                            errors.push(format!("Field '{}' must be one of: {:?}", field, allowed));
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
                                    "Field '{}' must match pattern: {}",
                                    field, pattern
                                ));
                            }
                        }
                    }
                }
            }
        }
        "custom" => {
            if let Some(message) = &rule.message {
                errors.push(format!("Custom validation: {}", message));
            }
        }
        _ => {}
    }

    errors
}

fn get_value_type(value: &ConfigValue) -> String {
    match value {
        ConfigValue::String(_) => "string".to_string(),
        ConfigValue::Integer(_) => "integer".to_string(),
        ConfigValue::Float(_) => "number".to_string(),
        ConfigValue::Boolean(_) => "boolean".to_string(),
        ConfigValue::Array(_) => "array".to_string(),
        ConfigValue::Object(_) => "object".to_string(),
        ConfigValue::Null => "null".to_string(),
    }
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
    fn test_validation_required() {
        let data = serde_json::json!({"key": "value"});
        let mut map = std::collections::HashMap::new();
        map.insert("key".to_string(), ConfigValue::String("value".to_string()));
        let config_value = ConfigValue::Object(map);

        let structure = ConfigStructure {
            file: crate::types::FileInfo {
                location: String::new(),
            },
            format: None,
            schema: Some(crate::types::Schema {
                r#type: None,
                properties: None,
                required: Some(vec!["key".to_string()]),
            }),
            formatting: None,
            validation: None,
        };

        let result = validate(&config_value, &structure);
        assert!(result.unwrap().is_empty());
    }
}
