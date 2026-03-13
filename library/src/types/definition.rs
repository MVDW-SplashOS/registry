use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MainDefinition {
    pub categories: Vec<String>,
    pub packages: HashMap<String, HashMap<String, PackageDefinition>>,
}

impl Default for MainDefinition {
    fn default() -> Self {
        MainDefinition {
            categories: Vec::new(),
            packages: HashMap::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackageDefinition {
    pub name: Option<String>,
    pub description: Option<String>,
    pub detect_installed: Vec<String>,
    pub structure: HashMap<String, String>,
    pub dependencies: Option<Vec<String>>,
}
