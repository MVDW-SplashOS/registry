pub mod schema;

pub use schema::{validate, validate_schema};

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{ConfigStructure, ConfigValue, FileInfo, Schema};

    #[test]
    fn test_validation_required() {
        let mut map = std::collections::HashMap::new();
        map.insert("key".to_string(), ConfigValue::String("value".to_string()));
        let config_value = ConfigValue::Object(map);

        let structure = ConfigStructure {
            file: FileInfo {
                location: String::new(),
            },
            format: None,
            schema: Some(Schema {
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
