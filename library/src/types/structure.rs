use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigStructure {
    pub file: FileInfo,
    pub format: Option<String>,
    pub schema: Option<Schema>,
    pub formatting: Option<Formatting>,
    pub validation: Option<Validation>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileInfo {
    pub location: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Schema {
    pub r#type: Option<String>,
    pub properties: Option<HashMap<String, SchemaProperty>>,
    pub required: Option<Vec<String>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchemaProperty {
    pub r#type: Option<String>,
    pub format: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Formatting {
    pub indent: Option<usize>,
    pub sort_keys: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Validation {
    pub rules: Vec<ValidationRule>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationRule {
    pub r#type: String,
    pub field: Option<String>,
    pub expected_type: Option<String>,
    pub min: Option<f64>,
    pub max: Option<f64>,
    pub allowed_values: Option<Vec<super::ConfigValue>>,
    pub pattern: Option<String>,
    pub message: Option<String>,
}
