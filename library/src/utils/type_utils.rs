use crate::types::ConfigValue;

pub fn type_matches(actual: &str, expected: &str) -> bool {
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

pub fn get_value_type(value: &ConfigValue) -> String {
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
