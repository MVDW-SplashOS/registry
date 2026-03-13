use crate::decoder::FileTypeDecoder;
use crate::error::Result;
use crate::types::{ConfigStructure, ConfigValue};
use crate::utils::validate_rule as shared_validate_rule;
use std::collections::HashMap;

pub struct KeyValueDecoder;

impl KeyValueDecoder {
    pub fn new() -> Self {
        KeyValueDecoder
    }
}

impl Default for KeyValueDecoder {
    fn default() -> Self {
        Self::new()
    }
}

impl FileTypeDecoder for KeyValueDecoder {
    fn decode(&self, content: &str, _structure: &ConfigStructure) -> Result<ConfigValue> {
        let mut result = HashMap::new();
        let mut current_comment = String::new();

        for line in content.lines() {
            let line = line.trim();

            if line.is_empty() {
                current_comment.clear();
                continue;
            }

            if line.starts_with('#') || line.starts_with(';') {
                current_comment = line[1..].trim().to_string();
                continue;
            }

            if let Some(pos) = find_key_value_separator(line) {
                let key = line[..pos].trim().to_string();
                let mut value = line[pos + 1..].trim().to_string();

                value = expand_value(&value);

                if !current_comment.is_empty() {
                    let key_with_comment = format!("#{}", key);
                    result.insert(
                        key_with_comment,
                        ConfigValue::String(current_comment.clone()),
                    );
                    current_comment.clear();
                }

                if let Some(existing) = result.get(&key) {
                    if let ConfigValue::Array(mut arr) = existing.clone() {
                        arr.push(ConfigValue::String(value));
                        result.insert(key, ConfigValue::Array(arr));
                    } else {
                        let old_value = existing.clone();
                        result.insert(
                            key,
                            ConfigValue::Array(vec![old_value, ConfigValue::String(value)]),
                        );
                    }
                } else {
                    result.insert(key, ConfigValue::String(value));
                }
            } else {
                if !line.is_empty() {
                    result.insert(line.to_string(), ConfigValue::String(String::new()));
                }
            }
        }

        Ok(ConfigValue::Object(result))
    }

    fn encode(&self, data: &ConfigValue, _structure: &ConfigStructure) -> Result<String> {
        let mut output = String::new();

        if let ConfigValue::Object(map) = data {
            let mut keys: Vec<_> = map.keys().collect();
            keys.sort();

            for key in keys {
                if key.starts_with('#') {
                    output.push_str(&format!("# {}\n", map.get(key).unwrap()));
                    continue;
                }

                if let Some(value) = map.get(key) {
                    output.push_str(&format!("{} {}\n", key, value_to_keyvalue_string(value)));
                }
            }
        }

        Ok(output)
    }

    fn validate(&self, data: &ConfigValue, structure: &ConfigStructure) -> Result<Vec<String>> {
        let mut errors = Vec::new();

        if let Some(validation) = &structure.validation {
            for rule in &validation.rules {
                let rule_errors = shared_validate_rule(data, rule);
                errors.extend(rule_errors);
            }
        }

        Ok(errors)
    }

    fn name(&self) -> &str {
        "key-value"
    }
}

fn find_key_value_separator(line: &str) -> Option<usize> {
    for (i, c) in line.char_indices() {
        if c == ' ' || c == '\t' || c == '=' || c == ':' {
            if i > 0 {
                return Some(i);
            }
        }
    }
    None
}

fn expand_value(value: &str) -> String {
    let mut result = value.to_string();

    if (result.starts_with('"') && result.ends_with('"'))
        || (result.starts_with('\'') && result.ends_with('\''))
    {
        result = result[1..result.len() - 1].to_string();
    }

    result
}

fn value_to_keyvalue_string(value: &ConfigValue) -> String {
    match value {
        ConfigValue::String(s) => {
            if s.contains(' ') || s.contains('#') || s.starts_with('"') {
                format!("\"{}\"", s)
            } else {
                s.clone()
            }
        }
        ConfigValue::Integer(i) => i.to_string(),
        ConfigValue::Float(f) => f.to_string(),
        ConfigValue::Boolean(b) => if *b { "yes" } else { "no" }.to_string(),
        ConfigValue::Array(arr) => arr
            .iter()
            .map(|v| value_to_keyvalue_string(v))
            .collect::<Vec<_>>()
            .join(" "),
        ConfigValue::Null => String::new(),
        _ => value.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_keyvalue_decode() {
        let decoder = KeyValueDecoder::new();
        let structure = ConfigStructure {
            file: crate::types::FileInfo {
                location: String::new(),
            },
            format: None,
            schema: None,
            formatting: None,
            validation: None,
        };

        let content = "Port 22\n# Comment\nHostKey /etc/ssh/ssh_host_rsa_key";
        let result = decoder.decode(content, &structure);
        assert!(result.is_ok());
    }
}
