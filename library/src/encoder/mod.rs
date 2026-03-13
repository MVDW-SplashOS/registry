pub use crate::decoder::FileTypeDecoder;

pub struct Encoder {
    encoders: std::collections::HashMap<String, Box<dyn FileTypeDecoder>>,
}

impl Encoder {
    pub fn new() -> Self {
        use crate::decoder::{
            ini::IniDecoder, json::JsonDecoder, keyvalue::KeyValueDecoder, toml::TomlDecoder,
            xml::XmlDecoder, yaml::YamlDecoder,
        };

        let mut encoders: std::collections::HashMap<String, Box<dyn FileTypeDecoder>> =
            std::collections::HashMap::new();
        encoders.insert("json".to_string(), Box::new(JsonDecoder::new()));
        encoders.insert("yaml".to_string(), Box::new(YamlDecoder::new()));
        encoders.insert("toml".to_string(), Box::new(TomlDecoder::new()));
        encoders.insert("xml".to_string(), Box::new(XmlDecoder::new()));
        encoders.insert("ini".to_string(), Box::new(IniDecoder::new()));
        encoders.insert("key-value".to_string(), Box::new(KeyValueDecoder::new()));

        Encoder { encoders }
    }

    pub fn get_encoder(&self, filetype: &str) -> Option<&Box<dyn FileTypeDecoder>> {
        self.encoders.get(filetype)
    }
}

impl Default for Encoder {
    fn default() -> Self {
        Self::new()
    }
}

lazy_static::lazy_static! {
    pub static ref ENCODER: Encoder = Encoder::new();
}

pub fn get_encoder() -> &'static Encoder {
    &ENCODER
}

pub fn encode_file(
    data: &crate::types::ConfigValue,
    structure: &crate::types::ConfigStructure,
    file_path: &str,
) -> crate::Result<()> {
    use std::path::Path;

    let path = Path::new(file_path);
    let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");

    let filetype =
        structure
            .format
            .as_deref()
            .unwrap_or_else(|| match ext.to_lowercase().as_str() {
                "json" => "json",
                "yaml" | "yml" => "yaml",
                "toml" => "toml",
                "xml" => "xml",
                "ini" => "ini",
                _ => "key-value",
            });

    let enc = get_encoder().get_encoder(filetype).ok_or_else(|| {
        crate::error::RegistryError::EncodingError(format!("No encoder for filetype: {}", filetype))
    })?;

    let content = enc.encode(data, structure)?;
    std::fs::write(file_path, content)?;

    Ok(())
}
