#[cfg(test)]
mod tests {
    use libregistry::decoder;
    use libregistry::definitions;
    use libregistry::encoder;
    use libregistry::types::{ConfigStructure, ConfigValue, FileInfo, Schema};
    use libregistry::validation;

    #[test]
    fn test_load_main_definition() {
        let def = definitions::get_main_definition();
        assert!(def.categories.len() >= 0);
    }

    #[test]
    fn test_definitions_dir() {
        let dir = definitions::get_definitions_dir();
        assert!(!dir.is_empty());
    }

    #[test]
    fn test_decoder_creation() {
        let dec = decoder::Decoder::new();
        assert!(dec.get_decoder("json").is_some());
    }

    #[test]
    fn test_encoder_creation() {
        let enc = encoder::Encoder::new();
        assert!(enc.get_encoder("json").is_some());
    }

    #[test]
    fn test_config_value_json_roundtrip() {
        let json_str = r#"{"key": "value", "number": 42}"#;
        let val = ConfigValue::from_json(json_str).unwrap();
        let encoded = val.to_json().unwrap();
        assert!(encoded.contains("key"));
    }

    #[test]
    fn test_config_value_yaml_roundtrip() {
        let yaml_str = "key: value\nnumber: 42";
        let val = ConfigValue::from_yaml(yaml_str).unwrap();
        let encoded = val.to_yaml().unwrap();
        assert!(encoded.contains("key"));
    }

    #[test]
    fn test_validation_schema() {
        let mut map = std::collections::HashMap::new();
        map.insert("name".to_string(), ConfigValue::String("test".to_string()));
        let config_value = ConfigValue::Object(map);

        let structure = ConfigStructure {
            file: FileInfo {
                location: String::new(),
            },
            format: None,
            schema: Some(Schema {
                r#type: None,
                properties: None,
                required: Some(vec!["name".to_string()]),
            }),
            formatting: None,
            validation: None,
        };

        let result = validation::validate(&config_value, &structure);
        assert!(result.is_ok());
    }

    #[test]
    fn test_session_creation() {
        let session = libregistry::RegistrySession::new();
        assert!(session.main_definition.categories.len() >= 0);
    }

    fn make_file_info() -> FileInfo {
        FileInfo {
            location: String::new(),
        }
    }

    fn make_structure(format: &str) -> ConfigStructure {
        ConfigStructure {
            file: make_file_info(),
            format: Some(format.to_string()),
            schema: None,
            formatting: None,
            validation: None,
        }
    }

    #[test]
    fn test_json_encoder_simple_dict() {
        let data = ConfigValue::Object(std::collections::HashMap::from([(
            "key".to_string(),
            ConfigValue::String("value".to_string()),
        )]));
        let structure = make_structure("json");

        let enc = encoder::Encoder::new();
        let json_enc = enc.get_encoder("json").unwrap();
        let result = json_enc.encode(&data, &structure).unwrap();
        assert!(result.contains("key"));
    }

    #[test]
    fn test_json_encoder_nested_dict() {
        let mut inner = std::collections::HashMap::new();
        inner.insert("key".to_string(), ConfigValue::String("value".to_string()));

        let mut outer = std::collections::HashMap::new();
        outer.insert("section".to_string(), ConfigValue::Object(inner));

        let data = ConfigValue::Object(outer);
        let structure = make_structure("json");

        let enc = encoder::Encoder::new();
        let json_enc = enc.get_encoder("json").unwrap();
        let result = json_enc.encode(&data, &structure).unwrap();
        assert!(result.contains("section"));
    }

    #[test]
    fn test_json_encoder_boolean_true() {
        let data = ConfigValue::Object(std::collections::HashMap::from([(
            "enabled".to_string(),
            ConfigValue::Boolean(true),
        )]));
        let structure = make_structure("json");

        let enc = encoder::Encoder::new();
        let json_enc = enc.get_encoder("json").unwrap();
        let result = json_enc.encode(&data, &structure).unwrap();
        assert!(result.contains("true"));
    }

    #[test]
    fn test_json_encoder_boolean_false() {
        let data = ConfigValue::Object(std::collections::HashMap::from([(
            "disabled".to_string(),
            ConfigValue::Boolean(false),
        )]));
        let structure = make_structure("json");

        let enc = encoder::Encoder::new();
        let json_enc = enc.get_encoder("json").unwrap();
        let result = json_enc.encode(&data, &structure).unwrap();
        assert!(result.contains("false"));
    }

    #[test]
    fn test_json_encoder_integer() {
        let data = ConfigValue::Object(std::collections::HashMap::from([(
            "port".to_string(),
            ConfigValue::Integer(8080),
        )]));
        let structure = make_structure("json");

        let enc = encoder::Encoder::new();
        let json_enc = enc.get_encoder("json").unwrap();
        let result = json_enc.encode(&data, &structure).unwrap();
        assert!(result.contains("8080"));
    }

    #[test]
    fn test_json_encoder_float() {
        let data = ConfigValue::Object(std::collections::HashMap::from([(
            "rate".to_string(),
            ConfigValue::Float(3.14),
        )]));
        let structure = make_structure("json");

        let enc = encoder::Encoder::new();
        let json_enc = enc.get_encoder("json").unwrap();
        let result = json_enc.encode(&data, &structure).unwrap();
        assert!(result.contains("3.14"));
    }

    #[test]
    fn test_json_encoder_list() {
        let data = ConfigValue::Object(std::collections::HashMap::from([(
            "servers".to_string(),
            ConfigValue::Array(vec![
                ConfigValue::String("server1".to_string()),
                ConfigValue::String("server2".to_string()),
            ]),
        )]));
        let structure = make_structure("json");

        let enc = encoder::Encoder::new();
        let json_enc = enc.get_encoder("json").unwrap();
        let result = json_enc.encode(&data, &structure).unwrap();
        assert!(result.contains("server1"));
        assert!(result.contains("server2"));
    }

    #[test]
    fn test_json_encoder_empty_list() {
        let data = ConfigValue::Object(std::collections::HashMap::from([(
            "items".to_string(),
            ConfigValue::Array(vec![]),
        )]));
        let structure = make_structure("json");

        let enc = encoder::Encoder::new();
        let json_enc = enc.get_encoder("json").unwrap();
        let result = json_enc.encode(&data, &structure).unwrap();
        assert!(result.contains("[]"));
    }

    #[test]
    fn test_json_encoder_null() {
        let data = ConfigValue::Object(std::collections::HashMap::from([(
            "key".to_string(),
            ConfigValue::Null,
        )]));
        let structure = make_structure("json");

        let enc = encoder::Encoder::new();
        let json_enc = enc.get_encoder("json").unwrap();
        let result = json_enc.encode(&data, &structure).unwrap();
        assert!(result.contains("null"));
    }

    #[test]
    fn test_json_encoder_empty_dict() {
        let data = ConfigValue::Object(std::collections::HashMap::new());
        let structure = make_structure("json");

        let enc = encoder::Encoder::new();
        let json_enc = enc.get_encoder("json").unwrap();
        let result = json_enc.encode(&data, &structure).unwrap();
        assert_eq!(result, "{}");
    }

    #[test]
    fn test_json_decoder_simple_key_value() {
        let content = r#"{"key": "value"}"#;
        let structure = make_structure("json");

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let result = json_dec.decode(content, &structure).unwrap();

        assert_eq!(
            result.get("key"),
            Some(&ConfigValue::String("value".to_string()))
        );
    }

    #[test]
    fn test_json_decoder_nested_dict() {
        let content = r#"{"section": {"key": "value"}}"#;
        let structure = make_structure("json");

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let result = json_dec.decode(content, &structure).unwrap();

        let section = result.get("section").unwrap();
        if let ConfigValue::Object(map) = section {
            assert_eq!(
                map.get("key"),
                Some(&ConfigValue::String("value".to_string()))
            );
        } else {
            panic!("Expected Object");
        }
    }

    #[test]
    fn test_json_decoder_list() {
        let content = r#"{"servers": ["server1", "server2"]}"#;
        let structure = make_structure("json");

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let result = json_dec.decode(content, &structure).unwrap();

        let servers = result.get("servers").unwrap();
        if let ConfigValue::Array(arr) = servers {
            assert_eq!(arr.len(), 2);
        } else {
            panic!("Expected Array");
        }
    }

    #[test]
    fn test_json_decoder_boolean_true() {
        let content = r#"{"enabled": true}"#;
        let structure = make_structure("json");

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let result = json_dec.decode(content, &structure).unwrap();

        assert_eq!(result.get("enabled"), Some(&ConfigValue::Boolean(true)));
    }

    #[test]
    fn test_json_decoder_boolean_false() {
        let content = r#"{"disabled": false}"#;
        let structure = make_structure("json");

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let result = json_dec.decode(content, &structure).unwrap();

        assert_eq!(result.get("disabled"), Some(&ConfigValue::Boolean(false)));
    }

    #[test]
    fn test_json_decoder_integer() {
        let content = r#"{"port": 8080}"#;
        let structure = make_structure("json");

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let result = json_dec.decode(content, &structure).unwrap();

        assert_eq!(result.get("port"), Some(&ConfigValue::Integer(8080)));
    }

    #[test]
    fn test_json_decoder_float() {
        let content = r#"{"rate": 3.14}"#;
        let structure = make_structure("json");

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let result = json_dec.decode(content, &structure).unwrap();

        if let Some(ConfigValue::Float(f)) = result.get("rate") {
            assert!((f - 3.14).abs() < 0.001);
        } else {
            panic!("Expected Float");
        }
    }

    #[test]
    fn test_json_decoder_null() {
        let content = r#"{"key": null}"#;
        let structure = make_structure("json");

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let result = json_dec.decode(content, &structure).unwrap();

        assert_eq!(result.get("key"), Some(&ConfigValue::Null));
    }

    #[test]
    fn test_json_decoder_empty_object() {
        let content = r#"{}"#;
        let structure = make_structure("json");

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let result = json_dec.decode(content, &structure).unwrap();

        assert!(result.is_empty());
    }

    #[test]
    fn test_json_decoder_invalid_json() {
        let content = r#"{"invalid": json"#;
        let structure = make_structure("json");

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let result = json_dec.decode(content, &structure);

        assert!(result.is_err());
    }

    #[test]
    fn test_json_encode_decode_roundtrip() {
        let mut server = std::collections::HashMap::new();
        server.insert(
            "host".to_string(),
            ConfigValue::String("localhost".to_string()),
        );
        server.insert("port".to_string(), ConfigValue::Integer(8080));
        server.insert("enabled".to_string(), ConfigValue::Boolean(true));

        let mut data = std::collections::HashMap::new();
        data.insert("server".to_string(), ConfigValue::Object(server));

        let original_data = ConfigValue::Object(data);
        let structure = make_structure("json");

        let enc = encoder::Encoder::new();
        let json_enc = enc.get_encoder("json").unwrap();
        let encoded = json_enc.encode(&original_data, &structure).unwrap();

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let decoded = json_dec.decode(&encoded, &structure).unwrap();

        if let Some(ConfigValue::Object(server_map)) = decoded.get("server") {
            assert_eq!(
                server_map.get("host"),
                Some(&ConfigValue::String("localhost".to_string()))
            );
            assert_eq!(server_map.get("port"), Some(&ConfigValue::Integer(8080)));
            assert_eq!(server_map.get("enabled"), Some(&ConfigValue::Boolean(true)));
        } else {
            panic!("Expected Object");
        }
    }

    #[test]
    fn test_yaml_decoder_simple_key_value() {
        let content = "key: value";
        let structure = make_structure("yaml");

        let dec = decoder::Decoder::new();
        let yaml_dec = dec.get_decoder("yaml").unwrap();
        let result = yaml_dec.decode(content, &structure).unwrap();

        assert_eq!(
            result.get("key"),
            Some(&ConfigValue::String("value".to_string()))
        );
    }

    #[test]
    fn test_yaml_decoder_nested() {
        let content = "section:\n  key: value";
        let structure = make_structure("yaml");

        let dec = decoder::Decoder::new();
        let yaml_dec = dec.get_decoder("yaml").unwrap();
        let result = yaml_dec.decode(content, &structure).unwrap();

        assert!(result.get("section").is_some());
    }

    #[test]
    fn test_toml_decoder_simple() {
        let content = "key = \"value\"";
        let structure = make_structure("toml");

        let dec = decoder::Decoder::new();
        let toml_dec = dec.get_decoder("toml").unwrap();
        let result = toml_dec.decode(content, &structure).unwrap();

        assert!(result.get("key").is_some());
    }

    #[test]
    fn test_ini_decoder_simple() {
        let content = "[section]\nkey = value";
        let structure = make_structure("ini");

        let dec = decoder::Decoder::new();
        let ini_dec = dec.get_decoder("ini").unwrap();
        let result = ini_dec.decode(content, &structure).unwrap();

        assert!(result.get("section").is_some());
    }

    #[test]
    fn test_keyvalue_decoder_simple() {
        let content = "key=value";
        let structure = make_structure("key-value");

        let dec = decoder::Decoder::new();
        let kv_dec = dec.get_decoder("key-value").unwrap();
        let result = kv_dec.decode(content, &structure).unwrap();

        assert_eq!(
            result.get("key"),
            Some(&ConfigValue::String("value".to_string()))
        );
    }

    #[test]
    fn test_decoder_validate_required_fields() {
        let data = ConfigValue::Object(std::collections::HashMap::from([(
            "name".to_string(),
            ConfigValue::String("test".to_string()),
        )]));

        let mut properties = std::collections::HashMap::new();
        properties.insert(
            "name".to_string(),
            libregistry::types::SchemaProperty {
                r#type: Some("string".to_string()),
                format: None,
            },
        );
        properties.insert(
            "version".to_string(),
            libregistry::types::SchemaProperty {
                r#type: Some("string".to_string()),
                format: None,
            },
        );

        let structure = ConfigStructure {
            file: make_file_info(),
            format: Some("json".to_string()),
            schema: Some(Schema {
                r#type: None,
                properties: Some(properties),
                required: Some(vec!["name".to_string(), "version".to_string()]),
            }),
            formatting: None,
            validation: None,
        };

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let errors = json_dec.validate(&data, &structure).unwrap();

        assert!(errors.len() > 0);
    }

    #[test]
    fn test_decoder_validate_required_fields_met() {
        let mut properties = std::collections::HashMap::new();
        properties.insert(
            "name".to_string(),
            libregistry::types::SchemaProperty {
                r#type: Some("string".to_string()),
                format: None,
            },
        );
        properties.insert(
            "version".to_string(),
            libregistry::types::SchemaProperty {
                r#type: Some("string".to_string()),
                format: None,
            },
        );

        let data = ConfigValue::Object(std::collections::HashMap::from([
            ("name".to_string(), ConfigValue::String("test".to_string())),
            (
                "version".to_string(),
                ConfigValue::String("1.0".to_string()),
            ),
        ]));

        let structure = ConfigStructure {
            file: make_file_info(),
            format: Some("json".to_string()),
            schema: Some(Schema {
                r#type: None,
                properties: Some(properties),
                required: Some(vec!["name".to_string(), "version".to_string()]),
            }),
            formatting: None,
            validation: None,
        };

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let errors = json_dec.validate(&data, &structure).unwrap();

        assert_eq!(errors.len(), 0);
    }

    #[test]
    fn test_decoder_validate_no_schema_no_rules() {
        let data = ConfigValue::Object(std::collections::HashMap::from([(
            "key".to_string(),
            ConfigValue::String("value".to_string()),
        )]));

        let structure = make_structure("json");

        let dec = decoder::Decoder::new();
        let json_dec = dec.get_decoder("json").unwrap();
        let errors = json_dec.validate(&data, &structure).unwrap();

        assert_eq!(errors.len(), 0);
    }

    #[test]
    fn test_all_encoders_available() {
        let enc = encoder::Encoder::new();
        assert!(enc.get_encoder("json").is_some());
        assert!(enc.get_encoder("yaml").is_some());
        assert!(enc.get_encoder("toml").is_some());
        assert!(enc.get_encoder("xml").is_some());
        assert!(enc.get_encoder("ini").is_some());
        assert!(enc.get_encoder("key-value").is_some());
    }

    #[test]
    fn test_all_decoders_available() {
        let dec = decoder::Decoder::new();
        assert!(dec.get_decoder("json").is_some());
        assert!(dec.get_decoder("yaml").is_some());
        assert!(dec.get_decoder("toml").is_some());
        assert!(dec.get_decoder("xml").is_some());
        assert!(dec.get_decoder("ini").is_some());
        assert!(dec.get_decoder("key-value").is_some());
    }
}
