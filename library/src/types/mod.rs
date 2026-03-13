pub mod config_value;
pub mod definition;
pub mod structure;

pub use config_value::ConfigValue;
pub use definition::{MainDefinition, PackageDefinition};
pub use structure::{
    ConfigStructure, FileInfo, Formatting, Schema, SchemaProperty, Validation, ValidationRule,
};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_value_from_json() {
        let json = r#"{"key": "value"}"#;
        let val = ConfigValue::from_json(json).unwrap();
        assert!(matches!(val, ConfigValue::Object(_)));
    }

    #[test]
    fn test_config_value_to_json() {
        let val = ConfigValue::String("test".to_string());
        let json = val.to_json().unwrap();
        assert!(json.contains("test"));
    }
}
