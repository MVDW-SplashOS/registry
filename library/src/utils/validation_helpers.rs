use crate::types::{ConfigValue, ValidationRule};
use crate::utils::type_utils::type_matches;

pub fn validate_rule(data: &ConfigValue, rule: &ValidationRule) -> Vec<String> {
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
                        let actual_type = crate::utils::get_value_type(value);
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
