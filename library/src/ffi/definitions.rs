use crate::definitions;
use crate::ffi::{cstring_to_ptr, null_ptr};
use std::ffi::CStr;
use std::os::raw::c_char;
use std::path::Path;

#[no_mangle]
pub extern "C" fn registry_get_main_definition_json() -> *mut c_char {
    let main_def = definitions::get_main_definition();
    match serde_json::to_string(&main_def) {
        Ok(json) => cstring_to_ptr(&json),
        Err(_) => null_ptr(),
    }
}

#[no_mangle]
pub extern "C" fn registry_get_package_definition_json(
    category: *const c_char,
    package: *const c_char,
) -> *mut c_char {
    if category.is_null() || package.is_null() {
        return null_ptr();
    }

    let category = unsafe { CStr::from_ptr(category).to_string_lossy().into_owned() };
    let package = unsafe { CStr::from_ptr(package).to_string_lossy().into_owned() };

    let main_def = definitions::get_main_definition();
    match definitions::get_package_definition(&main_def, &category, &package) {
        Some(pkg_def) => match serde_json::to_string(&pkg_def) {
            Ok(json) => cstring_to_ptr(&json),
            Err(_) => null_ptr(),
        },
        None => null_ptr(),
    }
}

#[no_mangle]
pub extern "C" fn registry_get_config_structure_json(
    category: *const c_char,
    package: *const c_char,
    config_path: *const c_char,
) -> *mut c_char {
    if category.is_null() || package.is_null() || config_path.is_null() {
        return null_ptr();
    }

    let category = unsafe { CStr::from_ptr(category).to_string_lossy().into_owned() };
    let package = unsafe { CStr::from_ptr(package).to_string_lossy().into_owned() };
    let config_path = unsafe { CStr::from_ptr(config_path).to_string_lossy().into_owned() };

    match definitions::get_config_structure(&category, &package, &config_path) {
        Ok(structure) => match serde_json::to_string(&structure) {
            Ok(json) => cstring_to_ptr(&json),
            Err(_) => null_ptr(),
        },
        Err(_) => null_ptr(),
    }
}

#[no_mangle]
pub extern "C" fn registry_check_packages_installed() -> *mut c_char {
    let session = crate::session::RegistrySession::new();
    let installed = session.check_packages_installed();

    match serde_json::to_string(&installed) {
        Ok(json) => cstring_to_ptr(&json),
        Err(_) => null_ptr(),
    }
}

#[no_mangle]
pub extern "C" fn registry_get_completions(prefix: *const c_char) -> *mut c_char {
    let prefix = if prefix.is_null() {
        String::new()
    } else {
        unsafe { CStr::from_ptr(prefix).to_string_lossy().into_owned() }
    };

    let main_def = definitions::get_main_definition();
    let mut completions: Vec<String> = Vec::new();

    // If empty or contains only category part
    if !prefix.contains('/') {
        for category in &main_def.categories {
            if prefix.is_empty() || category.starts_with(&prefix) {
                completions.push(category.clone() + "/");
            }
        }
    } else {
        let parts: Vec<&str> = prefix.split('/').filter(|s| !s.is_empty()).collect();

        if parts.len() == 0 {
            // Just a trailing slash, show categories
            for category in &main_def.categories {
                completions.push(category.clone() + "/");
            }
        } else if parts.len() == 1 {
            // Complete package names for the given category
            let category = parts[0];
            // Read packages from the filesystem
            let definitions_dir = definitions::get_definitions_dir();
            let category_path = Path::new(definitions_dir).join(category);
            if let Ok(entries) = std::fs::read_dir(&category_path) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.is_dir() {
                        if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                            if !name.starts_with('.') && name != "packages.yaml" {
                                // Return just the package name, not full path
                                completions.push(name.to_string());
                            }
                        }
                    }
                }
            }
        } else if parts.len() == 2 {
            // Could be either:
            // 1. Complete package names for category with filter (e.g., "cat/pkg" or "cat/pk")
            // 2. Complete config names for a package (e.g., "cat/package/")
            let category = parts[0];
            let filter = parts[1];
            let main_def = definitions::get_main_definition();

            // Check if filter is a complete package name and prefix ends with /
            let wants_configs = prefix.ends_with('/');

            if let Some(pkg_def) = definitions::get_package_definition(&main_def, category, filter)
            {
                if wants_configs {
                    // User wants to see configs for this package
                    for config_name in pkg_def.structure.keys() {
                        completions.push(config_name.clone());
                    }
                } else {
                    // Package is complete (exact match with no trailing /)
                    // Return nothing to indicate completion is done
                }
            } else {
                // Filter is partial, list matching packages
                let definitions_dir = definitions::get_definitions_dir();
                let category_path = Path::new(definitions_dir).join(category);
                if let Ok(entries) = std::fs::read_dir(&category_path) {
                    for entry in entries.flatten() {
                        let path = entry.path();
                        if path.is_dir() {
                            if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                                if !name.starts_with('.')
                                    && name != "packages.yaml"
                                    && name.starts_with(filter)
                                {
                                    // Return just the package name, not full path
                                    completions.push(name.to_string());
                                }
                            }
                        }
                    }
                }
            }
        } else if parts.len() == 3 {
            // Could be either:
            // 1. Completing config names for category/package with filter (e.g., "cat/pkg/con")
            // 2. Completing nested keys for a specific config (e.g., "cat/pkg/config/")
            let category = parts[0];
            let package = parts[1];
            let filter = parts[2];
            let main_def = definitions::get_main_definition();
            if let Some(pkg_def) = definitions::get_package_definition(&main_def, category, package)
            {
                // Check if filter matches a config name exactly (and prefix ends with /)
                let exact_match = pkg_def.structure.contains_key(filter);
                let wants_nested = prefix.ends_with('/');

                if exact_match && wants_nested {
                    // User wants nested keys for this config
                    if let Some(struct_file) = pkg_def.structure.get(filter) {
                        let definitions_dir = definitions::get_definitions_dir();
                        // Structure files have .yaml extension
                        let struct_file_yaml = if struct_file.ends_with(".yaml") {
                            struct_file.clone()
                        } else {
                            format!("{}.yaml", struct_file)
                        };
                        let struct_path = Path::new(definitions_dir)
                            .join(category)
                            .join(package)
                            .join(struct_file_yaml);

                        if let Ok(content) = std::fs::read_to_string(&struct_path) {
                            if let Ok(parsed) = serde_yaml::from_str::<serde_yaml::Value>(&content)
                            {
                                // Navigate to structures.main.options to get config keys
                                if let Some(structures) = parsed.get("structures") {
                                    if let Some(main) = structures.get("main") {
                                        if let Some(options) = main.get("options") {
                                            if let Some(options_map) = options.as_mapping() {
                                                for (key, _) in options_map {
                                                    if let Some(key_str) = key.as_str() {
                                                        // Return just the key name
                                                        completions.push(key_str.to_string());
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    if completions.is_empty() {
                        completions.push(prefix.to_string());
                    }
                } else if exact_match && !wants_nested {
                    // Path is already complete (exact config match with no trailing /)
                    // Return nothing to indicate completion is done
                } else {
                    // Normal config name completion
                    for config_name in pkg_def.structure.keys() {
                        if filter.is_empty() || config_name.starts_with(filter) {
                            // Return just the config name, not full path
                            completions.push(config_name.clone());
                        }
                    }
                }
            }
        } else if parts.len() == 4 {
            // Complete nested keys: category/package/config/nested_key
            let category = parts[0];
            let package = parts[1];
            let config_name = parts[2];
            let filter = parts[3];

            let main_def = definitions::get_main_definition();
            if let Some(pkg_def) = definitions::get_package_definition(&main_def, category, package)
            {
                if let Some(struct_file) = pkg_def.structure.get(config_name) {
                    let definitions_dir = definitions::get_definitions_dir();
                    // Structure files have .yaml extension
                    let struct_file_yaml = if struct_file.ends_with(".yaml") {
                        struct_file.clone()
                    } else {
                        format!("{}.yaml", struct_file)
                    };
                    let struct_path = Path::new(definitions_dir)
                        .join(category)
                        .join(package)
                        .join(struct_file_yaml);

                    if let Ok(content) = std::fs::read_to_string(&struct_path) {
                        if let Ok(parsed) = serde_yaml::from_str::<serde_yaml::Value>(&content) {
                            // Navigate to structures.main.options to get config keys
                            if let Some(structures) = parsed.get("structures") {
                                if let Some(main) = structures.get("main") {
                                    if let Some(options) = main.get("options") {
                                        if let Some(options_map) = options.as_mapping() {
                                            for (key, _) in options_map {
                                                if let Some(key_str) = key.as_str() {
                                                    if filter.is_empty()
                                                        || key_str.starts_with(filter)
                                                    {
                                                        // Return just the key name
                                                        completions.push(key_str.to_string());
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            if completions.is_empty() {
                completions.push(prefix.to_string());
            }
        } else if parts.len() > 4 {
            // Already have full path, return the full path as completion
            completions.push(prefix.to_string());
        }
    }

    match serde_json::to_string(&completions) {
        Ok(json) => cstring_to_ptr(&json),
        Err(_) => null_ptr(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_main_definition() {
        let json = registry_get_main_definition_json();
        assert!(!json.is_null());
        crate::ffi::registry_free_string(json);
    }
}
