pub mod ini;
pub mod json;
pub mod keyvalue;
pub mod toml;
pub mod xml;
pub mod yaml;

use crate::error::{RegistryError, Result};
use crate::types::{ConfigStructure, ConfigValue};
use std::collections::HashMap;
use std::path::Path;

pub trait FileTypeDecoder: Send + Sync {
    fn decode(&self, content: &str, structure: &ConfigStructure) -> Result<ConfigValue>;
    fn encode(&self, data: &ConfigValue, structure: &ConfigStructure) -> Result<String>;
    fn validate(&self, data: &ConfigValue, structure: &ConfigStructure) -> Result<Vec<String>>;
    fn name(&self) -> &str;
}

pub struct Decoder {
    decoders: HashMap<String, Box<dyn FileTypeDecoder>>,
}

impl Decoder {
    pub fn new() -> Self {
        let mut decoders: HashMap<String, Box<dyn FileTypeDecoder>> = HashMap::new();
        decoders.insert("json".to_string(), Box::new(json::JsonDecoder::new()));
        decoders.insert("yaml".to_string(), Box::new(yaml::YamlDecoder::new()));
        decoders.insert("toml".to_string(), Box::new(toml::TomlDecoder::new()));
        decoders.insert("xml".to_string(), Box::new(xml::XmlDecoder::new()));
        decoders.insert("ini".to_string(), Box::new(ini::IniDecoder::new()));
        decoders.insert(
            "key-value".to_string(),
            Box::new(keyvalue::KeyValueDecoder::new()),
        );

        Decoder { decoders }
    }

    pub fn get_decoder(&self, filetype: &str) -> Option<&Box<dyn FileTypeDecoder>> {
        self.decoders.get(filetype)
    }

    pub fn decode_file(&self, file_path: &str, structure: &ConfigStructure) -> Result<ConfigValue> {
        let content = std::fs::read_to_string(file_path)?;

        let filetype = structure
            .format
            .as_deref()
            .unwrap_or_else(|| self.detect_filetype(file_path));

        let decoder = self.get_decoder(filetype).ok_or_else(|| {
            RegistryError::DecodingError(format!("No decoder for filetype: {}", filetype))
        })?;

        decoder.decode(&content, structure)
    }

    pub fn encode_file(
        &self,
        data: &ConfigValue,
        structure: &ConfigStructure,
        file_path: &str,
    ) -> Result<()> {
        let filetype = structure
            .format
            .as_deref()
            .unwrap_or_else(|| self.detect_filetype(file_path));

        let decoder = self.get_decoder(filetype).ok_or_else(|| {
            RegistryError::EncodingError(format!("No encoder for filetype: {}", filetype))
        })?;

        let content = decoder.encode(data, structure)?;
        std::fs::write(file_path, content)?;

        Ok(())
    }

    pub fn validate_file(
        &self,
        file_path: &str,
        structure: &ConfigStructure,
    ) -> Result<Vec<String>> {
        let data = self.decode_file(file_path, structure)?;

        let filetype = structure
            .format
            .as_deref()
            .unwrap_or_else(|| self.detect_filetype(file_path));

        let decoder = self.get_decoder(filetype).ok_or_else(|| {
            RegistryError::ValidationError(format!("No decoder for filetype: {}", filetype))
        })?;

        decoder.validate(&data, structure)
    }

    fn detect_filetype(&self, file_path: &str) -> &str {
        let path = Path::new(file_path);
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");

        match ext.to_lowercase().as_str() {
            "json" => "json",
            "yaml" | "yml" => "yaml",
            "toml" => "toml",
            "xml" => "xml",
            "ini" => "ini",
            "conf" | "cfg" | "cnf" => "key-value",
            _ => "key-value",
        }
    }
}

impl Default for Decoder {
    fn default() -> Self {
        Self::new()
    }
}

lazy_static::lazy_static! {
    pub static ref DECODER: Decoder = Decoder::new();
}

pub fn get_decoder() -> &'static Decoder {
    &DECODER
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_decoder_creation() {
        let decoder = Decoder::new();
        assert!(decoder.get_decoder("json").is_some());
    }

    #[test]
    fn test_filetype_detection() {
        let decoder = Decoder::new();
        assert_eq!(decoder.detect_filetype("/path/to/config.json"), "json");
        assert_eq!(decoder.detect_filetype("/path/to/config.yaml"), "yaml");
        assert_eq!(decoder.detect_filetype("/path/to/config.conf"), "key-value");
    }
}
