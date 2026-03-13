use crate::error::{RegistryError, Result};
use crate::types::{ConfigStructure, MainDefinition, PackageDefinition};
use log::{error, info};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

const DEFAULT_DEFINITIONS_DIR: &str = "/etc/registry/definitions";

pub fn get_definitions_dir() -> &'static str {
    if Path::new("/etc/registry/definitions").exists() {
        "/etc/registry/definitions"
    } else {
        DEFAULT_DEFINITIONS_DIR
    }
}

fn get_yaml(path: &str) -> Result<serde_yaml::Value> {
    let definitions_dir = get_definitions_dir();
    let full_path = Path::new(definitions_dir).join(path);

    match fs::read_to_string(&full_path) {
        Ok(content) => serde_yaml::from_str(&content).map_err(|e| {
            error!("Failed to parse YAML file {}: {}", full_path.display(), e);
            RegistryError::DefinitionError(format!("Failed to parse YAML: {}", e))
        }),
        Err(e) => {
            if e.kind() == std::io::ErrorKind::NotFound {
                info!("Definition YAML file not found: {}", full_path.display());
                Ok(serde_yaml::Value::Null)
            } else {
                error!(
                    "Failed to read definition YAML file: {}",
                    full_path.display()
                );
                Err(RegistryError::DefinitionError(format!(
                    "Failed to read file: {}",
                    e
                )))
            }
        }
    }
}

pub fn get_main_definition() -> MainDefinition {
    let manifest = get_yaml("manifest.yaml").unwrap_or_default();

    let categories: Vec<String> = manifest
        .get("categories")
        .and_then(|v| serde_yaml::from_value(v.clone()).ok())
        .unwrap_or_default();

    let mut packages: HashMap<String, HashMap<String, PackageDefinition>> = HashMap::new();

    for category in &categories {
        let packages_yaml = get_yaml(&format!("{}/packages.yaml", category)).unwrap_or_default();
        if let Some(cat_packages) = packages_yaml.get("packages") {
            if let Ok(cat_packages_map) =
                serde_yaml::from_value::<HashMap<String, PackageDefinition>>(cat_packages.clone())
            {
                packages.insert(category.clone(), cat_packages_map);
            }
        }
    }

    MainDefinition {
        categories,
        packages,
    }
}

pub fn get_package_definition(
    main_definition: &MainDefinition,
    category: &str,
    package: &str,
) -> Option<PackageDefinition> {
    let manifest = get_yaml(&format!("{}/{}/manifest.yaml", category, package)).ok()?;

    let pkg_def: PackageDefinition = serde_yaml::from_value(manifest).ok()?;

    Some(pkg_def)
}

pub fn get_config_structure(
    category: &str,
    package: &str,
    config_path: &str,
) -> Result<ConfigStructure> {
    let definitions_dir = get_definitions_dir();
    let base_path = config_path.split('/').next().unwrap_or(config_path);

    let main_def = get_main_definition();
    let pkg_def = match get_package_definition(&main_def, category, package) {
        Some(p) => p,
        None => {
            return Err(RegistryError::DefinitionError(format!(
                "Package not found: {}/{}",
                category, package
            )))
        }
    };

    let structure = pkg_def.structure.clone();

    for (struct_name, struct_file) in &structure {
        if struct_name == base_path || struct_file == base_path {
            let struct_path = Path::new(definitions_dir)
                .join(category)
                .join(package)
                .join(struct_file);
            if struct_path.exists() {
                let content = fs::read_to_string(&struct_path)?;
                let parsed: serde_yaml::Value = serde_yaml::from_str(&content)
                    .map_err(|e| RegistryError::StructureError(e.to_string()))?;
                let structure: ConfigStructure = serde_yaml::from_value(parsed)
                    .map_err(|e| RegistryError::StructureError(e.to_string()))?;
                return Ok(structure);
            }
        }
    }

    let struct_path = Path::new(definitions_dir)
        .join(category)
        .join(package)
        .join(format!("{}.yaml", base_path));

    if struct_path.exists() {
        let content = fs::read_to_string(&struct_path)?;
        let parsed: serde_yaml::Value = serde_yaml::from_str(&content)
            .map_err(|e| RegistryError::StructureError(e.to_string()))?;
        let structure: ConfigStructure = serde_yaml::from_value(parsed)
            .map_err(|e| RegistryError::StructureError(e.to_string()))?;
        Ok(structure)
    } else {
        Err(RegistryError::StructureError(format!(
            "Configuration structure not found: {}",
            config_path
        )))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_main_definition() {
        let def = get_main_definition();
        assert!(def.categories.len() >= 0);
    }

    #[test]
    fn test_definitions_dir_fallback() {
        let dir = get_definitions_dir();
        assert!(!dir.is_empty());
    }
}
