use crate::error::RegistryError;
use crate::Result;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum ConfigValue {
    String(String),
    Integer(i64),
    Float(f64),
    Boolean(bool),
    Array(Vec<ConfigValue>),
    Object(HashMap<String, ConfigValue>),
    Null,
}

impl ConfigValue {
    pub fn from_json(json: &str) -> Result<Self> {
        serde_json::from_str(json).map_err(RegistryError::JsonError)
    }

    pub fn to_json(&self) -> Result<String> {
        serde_json::to_string(self).map_err(RegistryError::JsonError)
    }

    pub fn from_yaml(yaml: &str) -> Result<Self> {
        serde_yaml::from_str(yaml).map_err(RegistryError::YamlError)
    }

    pub fn to_yaml(&self) -> Result<String> {
        serde_yaml::to_string(self).map_err(RegistryError::YamlError)
    }

    pub fn get(&self, key: &str) -> Option<&ConfigValue> {
        match self {
            ConfigValue::Object(map) => map.get(key),
            _ => None,
        }
    }

    pub fn is_empty(&self) -> bool {
        match self {
            ConfigValue::Object(map) => map.is_empty(),
            ConfigValue::Array(arr) => arr.is_empty(),
            ConfigValue::String(s) => s.is_empty(),
            ConfigValue::Null => true,
            _ => false,
        }
    }
}

impl std::fmt::Display for ConfigValue {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ConfigValue::String(s) => write!(f, "{}", s),
            ConfigValue::Integer(i) => write!(f, "{}", i),
            ConfigValue::Float(fl) => write!(f, "{}", fl),
            ConfigValue::Boolean(b) => write!(f, "{}", b),
            ConfigValue::Array(arr) => write!(f, "{:?}", arr),
            ConfigValue::Object(map) => write!(f, "{:?}", map),
            ConfigValue::Null => write!(f, "null"),
        }
    }
}

impl Default for ConfigValue {
    fn default() -> Self {
        ConfigValue::Null
    }
}

impl From<String> for ConfigValue {
    fn from(s: String) -> Self {
        ConfigValue::String(s)
    }
}

impl From<&str> for ConfigValue {
    fn from(s: &str) -> Self {
        ConfigValue::String(s.to_string())
    }
}

impl From<i64> for ConfigValue {
    fn from(i: i64) -> Self {
        ConfigValue::Integer(i)
    }
}

impl From<i32> for ConfigValue {
    fn from(i: i32) -> Self {
        ConfigValue::Integer(i as i64)
    }
}

impl From<f64> for ConfigValue {
    fn from(f: f64) -> Self {
        ConfigValue::Float(f)
    }
}

impl From<bool> for ConfigValue {
    fn from(b: bool) -> Self {
        ConfigValue::Boolean(b)
    }
}

impl<T> From<Vec<T>> for ConfigValue
where
    T: Into<ConfigValue>,
{
    fn from(v: Vec<T>) -> Self {
        ConfigValue::Array(v.into_iter().map(|e| e.into()).collect())
    }
}

impl<K, V> From<HashMap<K, V>> for ConfigValue
where
    K: Into<String>,
    V: Into<ConfigValue>,
{
    fn from(m: HashMap<K, V>) -> Self {
        ConfigValue::Object(m.into_iter().map(|(k, v)| (k.into(), v.into())).collect())
    }
}
