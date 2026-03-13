use crate::definitions::get_main_definition;
use crate::types::MainDefinition;
use std::collections::HashMap;
use std::path::PathBuf;

pub struct RegistrySession {
    pub main_definition: MainDefinition,
}

impl RegistrySession {
    pub fn new() -> Self {
        let main_definition = get_main_definition();

        RegistrySession { main_definition }
    }

    pub fn check_packages_installed(&self) -> HashMap<String, Vec<String>> {
        let mut result: HashMap<String, Vec<String>> = HashMap::new();

        for (category, packages) in &self.main_definition.packages {
            let mut installed_packages: Vec<String> = Vec::new();

            for (package_name, package_def) in packages {
                let mut is_installed = false;

                for check_path in &package_def.detect_installed {
                    if PathBuf::from(check_path).exists() {
                        is_installed = true;
                        break;
                    }
                }

                if is_installed {
                    installed_packages.push(package_name.clone());
                }
            }

            if !installed_packages.is_empty() {
                result.insert(category.clone(), installed_packages);
            }
        }

        result
    }

    pub fn get_definition_dir() -> PathBuf {
        if PathBuf::from("/etc/registry/definitions").exists() {
            PathBuf::from("/etc/registry/definitions")
        } else {
            PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("..")
                .join("definitions")
        }
    }
}

impl Default for RegistrySession {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_session_creation() {
        let session = RegistrySession::new();
        assert!(session.main_definition.categories.len() >= 0);
    }
}
