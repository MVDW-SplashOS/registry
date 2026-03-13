use crate::decoder::FileTypeDecoder;
use crate::error::{RegistryError, Result};
use crate::types::{ConfigStructure, ConfigValue};
use quick_xml::events::{BytesEnd, BytesStart, BytesText, Event};
use quick_xml::{Reader, Writer};
use std::collections::HashMap;
use std::io::Cursor;

pub struct XmlDecoder;

impl XmlDecoder {
    pub fn new() -> Self {
        XmlDecoder
    }
}

impl Default for XmlDecoder {
    fn default() -> Self {
        Self::new()
    }
}

impl FileTypeDecoder for XmlDecoder {
    fn decode(&self, content: &str, _structure: &ConfigStructure) -> Result<ConfigValue> {
        let mut reader = Reader::from_str(content);
        reader.config_mut().trim_text(true);

        let mut stack: Vec<(String, ConfigValue)> = Vec::new();
        let mut root: Option<ConfigValue> = None;

        loop {
            match reader.read_event() {
                Ok(Event::Start(e)) => {
                    let tag = String::from_utf8_lossy(e.name().as_ref()).to_string();
                    let mut attrs = HashMap::new();
                    for attr in e.attributes() {
                        if let Ok(attr) = attr {
                            let key = String::from_utf8_lossy(attr.key.as_ref()).to_string();
                            let value = String::from_utf8_lossy(&attr.value).to_string();
                            attrs.insert(key, value);
                        }
                    }

                    let element = if attrs.is_empty() {
                        ConfigValue::Object(HashMap::new())
                    } else {
                        let mut map = HashMap::new();
                        for (k, v) in attrs {
                            map.insert(format!("@{}", k), ConfigValue::String(v));
                        }
                        ConfigValue::Object(map)
                    };

                    stack.push((tag, element));
                }
                Ok(Event::Text(e)) => {
                    let text = e.unescape().unwrap_or_default().to_string();
                    if !text.is_empty() {
                        if let Some((_, value)) = stack.last_mut() {
                            if let ConfigValue::Object(ref mut map) = value {
                                if map.is_empty() {
                                    *value = ConfigValue::String(text);
                                } else {
                                    map.insert("#text".to_string(), ConfigValue::String(text));
                                }
                            }
                        }
                    }
                }
                Ok(Event::End(_)) => {
                    if let Some((tag, value)) = stack.pop() {
                        if let Some((_, parent)) = stack.last_mut() {
                            if let ConfigValue::Object(ref mut map) = parent {
                                map.insert(tag, value);
                            } else if let ConfigValue::Array(ref mut arr) = parent {
                                arr.push(value);
                            }
                        } else {
                            root = Some(value);
                        }
                    }
                }
                Ok(Event::Empty(e)) => {
                    let tag = String::from_utf8_lossy(e.name().as_ref()).to_string();
                    let mut attrs = HashMap::new();
                    for attr in e.attributes() {
                        if let Ok(attr) = attr {
                            let key = String::from_utf8_lossy(attr.key.as_ref()).to_string();
                            let value = String::from_utf8_lossy(&attr.value).to_string();
                            attrs.insert(key, value);
                        }
                    }

                    let element = if attrs.is_empty() {
                        ConfigValue::String(String::new())
                    } else {
                        let mut map = HashMap::new();
                        for (k, v) in attrs {
                            map.insert(format!("@{}", k), ConfigValue::String(v));
                        }
                        ConfigValue::Object(map)
                    };

                    if let Some((_, parent)) = stack.last_mut() {
                        if let ConfigValue::Object(ref mut map) = parent {
                            map.insert(tag, element);
                        }
                    } else {
                        root = Some(element);
                    }
                }
                Ok(Event::Eof) => break,
                Err(e) => {
                    return Err(RegistryError::XmlError(e.to_string()));
                }
                _ => {}
            }
        }

        root.ok_or_else(|| RegistryError::DecodingError("Empty XML".to_string()))
    }

    fn encode(&self, data: &ConfigValue, _structure: &ConfigStructure) -> Result<String> {
        let mut writer = Writer::new_with_indent(Cursor::new(Vec::new()), b' ', 2);
        encode_element(&mut writer, "root", data)?;
        let result = writer.into_inner().into_inner();
        String::from_utf8(result).map_err(|e| RegistryError::EncodingError(e.to_string()))
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
        "xml"
    }
}

fn encode_element(
    writer: &mut Writer<Cursor<Vec<u8>>>,
    tag: &str,
    value: &ConfigValue,
) -> Result<()> {
    match value {
        ConfigValue::String(s) => {
            writer
                .write_event(Event::Start(BytesStart::new(tag)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
            writer
                .write_event(Event::Text(BytesText::new(s)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
            writer
                .write_event(Event::End(BytesEnd::new(tag)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
        }
        ConfigValue::Object(map) => {
            writer
                .write_event(Event::Start(BytesStart::new(tag)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
            for (k, v) in map {
                encode_element(writer, k, v)?;
            }
            writer
                .write_event(Event::End(BytesEnd::new(tag)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
        }
        ConfigValue::Array(arr) => {
            for item in arr {
                encode_element(writer, tag, item)?;
            }
        }
        ConfigValue::Integer(i) => {
            writer
                .write_event(Event::Start(BytesStart::new(tag)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
            writer
                .write_event(Event::Text(BytesText::new(&i.to_string())))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
            writer
                .write_event(Event::End(BytesEnd::new(tag)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
        }
        ConfigValue::Float(f) => {
            writer
                .write_event(Event::Start(BytesStart::new(tag)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
            writer
                .write_event(Event::Text(BytesText::new(&f.to_string())))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
            writer
                .write_event(Event::End(BytesEnd::new(tag)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
        }
        ConfigValue::Boolean(b) => {
            writer
                .write_event(Event::Start(BytesStart::new(tag)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
            writer
                .write_event(Event::Text(BytesText::new(&b.to_string())))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
            writer
                .write_event(Event::End(BytesEnd::new(tag)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
        }
        ConfigValue::Null => {
            writer
                .write_event(Event::Empty(BytesStart::new(tag)))
                .map_err(|e| RegistryError::EncodingError(e.to_string()))?;
        }
    }
    Ok(())
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_xml_decode() {
        let decoder = XmlDecoder::new();
        let structure = ConfigStructure {
            file: crate::types::FileInfo {
                location: String::new(),
            },
            format: None,
            schema: None,
            formatting: None,
            validation: None,
        };

        let result = decoder.decode("<root><key>value</key></root>", &structure);
        assert!(result.is_ok());
    }
}
