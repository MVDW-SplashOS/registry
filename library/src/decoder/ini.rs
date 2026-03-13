use crate::decoder::FileTypeDecoder;
use crate::error::Result;
use crate::types::{ConfigStructure, ConfigValue};
use std::collections::HashMap;

pub struct IniDecoder;

impl IniDecoder {
    pub fn new() -> Self {
        IniDecoder
    }
}

impl Default for IniDecoder {
    fn default() -> Self {
        Self::new()
    }
}

impl FileTypeDecoder for IniDecoder {
    fn decode(&self, content: &str, _structure: &ConfigStructure) -> Result<ConfigValue> {
        let mut result = HashMap::new();
        let mut current_section = String::new();
        let mut current_section_data = HashMap::new();

        for line in content.lines() {
            let line = line.trim();

            if line.is_empty() || line.starts_with(';') || line.starts_with('#') {
                continue;
            }

            if line.starts_with('[') && line.ends_with(']') {
                if !current_section.is_empty() {
                    result.insert(
                        current_section.clone(),
                        ConfigValue::Object(current_section_data.clone()),
                    );
                    current_section_data.clear();
                }
                current_section = line[1..line.len() - 1].to_string();
                continue;
            }

            if let Some(pos) = line.find('=') {
                let key = line[..pos].trim().to_string();
                let value = line[pos + 1..].trim().to_string();
                let parsed_value = parse_ini_value(&value);
                current_section_data.insert(key, parsed_value);
            }
        }

        if !current_section.is_empty() {
            result.insert(current_section, ConfigValue::Object(current_section_data));
        } else if !current_section_data.is_empty() {
            result.insert(
                "DEFAULT".to_string(),
                ConfigValue::Object(current_section_data),
            );
        }

        Ok(ConfigValue::Object(result))
    }

    fn encode(&self, data: &ConfigValue, _structure: &ConfigStructure) -> Result<String> {
        let mut output = String::new();

        if let ConfigValue::Object(map) = data {
            for (section, value) in map {
                output.push_str(&format!("[{}]\n", section));

                if let ConfigValue::Object(section_data) = value {
                    for (key, val) in section_data {
                        output.push_str(&format!("{} = {}\n", key, value_to_ini_string(val)));
                    }
                }
                output.push('\n');
            }
        }

        Ok(output)
    }

    fn validate(&self, data: &ConfigValue, structure: &ConfigStructure) -> Result<Vec<String>> {
        let mut errors = Vec::new();

        if let Some(validation) = &structure.validation {
            for rule in &validation.rules {
                let rule_errors = validate_rule(data, rule);
                errors.extend(rule_errors);
            }
        }

        Ok(errors)
    }

    fn name(&self) -> &str {
        "ini"
    }
}

fn parse_ini_value(value: &str) -> ConfigValue {
    let value = value.trim();

    if value.is_empty() {
        return ConfigValue::String(String::new());
    }

    if let Ok(b) = value.parse::<bool>() {
        return ConfigValue::Boolean(b);
    }

    if let Ok(i) = value.parse::<i64>() {
        return ConfigValue::Integer(i);
    }

    if let Ok(f) = value.parse::<f64>() {
        return ConfigValue::Float(f);
    }

    if (value.starts_with('"') && value.ends_with('"'))
        || (value.starts_with('\'') && value.ends_with('\''))
    {
        return ConfigValue::String(value[1..value.len() - 1].to_string());
    }

    ConfigValue::String(value.to_string())
}

fn value_to_ini_string(value: &ConfigValue) -> String {
    match value {
        ConfigValue::String(s) => {
            if s.contains(' ') || s.contains('#') || s.contains(';') || s.contains('=') {
                format!("\"{}\"", s)
            } else {
                s.clone()
            }
        }
        ConfigValue::Integer(i) => i.to_string(),
        ConfigValue::Float(f) => f.to_string(),
        ConfigValue::Boolean(b) => b.to_string(),
        ConfigValue::Null => String::new(),
        _ => value.to_string(),
    }
}

fn validate_rule(data: &ConfigValue, rule: &crate::types::ValidationRule) -> Vec<String> {
    let mut errors = Vec::new();

    match rule.r#type.as_str() {
        "required" => {
            if let Some(field) = &rule.field {
                if let ConfigValue::Object(map) = data {
                    let found = map.values().any(|v| {
                        if let ConfigValue::Object(section_data) = v {
                            section_data.contains_key(field)
                        } else {
                            false
                        }
                    });
                    if !found {
                        errors.push(format!("Required field missing: {}", field));
                    }
                }
            }
        }
        _ => {}
    }

    errors
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ini_decode() {
        let decoder = IniDecoder::new();
        let structure = ConfigStructure {
            file: crate::types::FileInfo {
                location: String::new(),
            },
            format: None,
            schema: None,
            formatting: None,
            validation: None,
        };

        let content = "[section1]\nkey1 = value1\nkey2 = 123";
        let result = decoder.decode(content, &structure);
        assert!(result.is_ok());
    }
}
