use crate::error::Result;
use crate::types::{ConfigStructure, ConfigValue};
use crate::utils::{get_value_type, type_matches};

pub fn validate(data: &ConfigValue, structure: &ConfigStructure) -> Result<Vec<String>> {
    let mut errors = Vec::new();

    if let Some(schema) = &structure.schema {
        errors.extend(validate_schema(data, schema)?);
    }

    if let Some(validation) = &structure.validation {
        for rule in &validation.rules {
            errors.extend(crate::utils::validate_rule(data, rule));
        }
    }

    Ok(errors)
}

pub fn validate_schema(data: &ConfigValue, schema: &crate::types::Schema) -> Result<Vec<String>> {
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
