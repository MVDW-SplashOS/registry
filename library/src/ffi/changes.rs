use crate::constants::STAGING_DIR_NAME;
use crate::error::RegistryErrorCode;
use crate::ffi::{cstring_to_ptr, null_ptr};
use crate::types::ConfigValue;
use crate::{decoder, definitions, encoder};
use std::collections::HashMap;
use std::fs;
use std::os::raw::c_char;
use std::path::PathBuf;

fn get_staging_dir() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());
    PathBuf::from(home).join(STAGING_DIR_NAME).join("staging")
}

fn set_config_value_at_path(
    value: &mut ConfigValue,
    key_path: &str,
    new_value: ConfigValue,
) -> bool {
    let keys: Vec<&str> = key_path.split('.').collect();
    if keys.is_empty() {
        return false;
    }

    if keys.len() == 1 {
        if let ConfigValue::Object(ref mut map) = value {
            map.insert(keys[0].to_string(), new_value);
            return true;
        }
        return false;
    }

    if let ConfigValue::Object(ref mut map) = value {
        if let Some(sub_value) = map.get_mut(keys[0]) {
            return set_config_value_at_path(sub_value, &keys[1..].join("."), new_value);
        }
    }
    false
}

#[no_mangle]
pub extern "C" fn registry_discard_changes() -> i32 {
    let staging_dir = get_staging_dir();
    if !staging_dir.exists() {
        return RegistryErrorCode::Success as i32;
    }

    match fs::remove_dir_all(&staging_dir) {
        Ok(_) => RegistryErrorCode::Success as i32,
        Err(e) => {
            if e.kind() == std::io::ErrorKind::NotFound {
                RegistryErrorCode::Success as i32
            } else {
                RegistryErrorCode::IoError as i32
            }
        }
    }
}

#[no_mangle]
pub extern "C" fn registry_apply_changes() -> i32 {
    let staging_dir = get_staging_dir();
    if !staging_dir.exists() {
        return RegistryErrorCode::Success as i32;
    }

    let entries = match fs::read_dir(&staging_dir) {
        Ok(e) => e,
        Err(_) => return RegistryErrorCode::IoError as i32,
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if path.extension().map_or(false, |e| e == "json") {
            if let Ok(content) = fs::read_to_string(&path) {
                if let Ok(staged_value) = serde_json::from_str::<ConfigValue>(&content) {
                    let filename = path.file_stem().and_then(|s| s.to_str()).unwrap_or("");
                    let parts: Vec<&str> = filename.split('_').collect();
                    if parts.len() >= 3 {
                        let category = parts[0];
                        let package = parts[1];
                        let config_path = parts[2..].join("/");

                        if let Ok(structure) =
                            definitions::get_config_structure(category, package, &config_path)
                        {
                            let file_path = structure.file.location.clone();

                            let d = decoder::get_decoder();

                            let existing_value: ConfigValue = if PathBuf::from(&file_path).exists()
                            {
                                match d.decode_file(&file_path, &structure) {
                                    Ok(v) => v,
                                    Err(_) => ConfigValue::Object(HashMap::new()),
                                }
                            } else {
                                ConfigValue::Object(HashMap::new())
                            };

                            let mut merged_value = existing_value;
                            let key_path = if config_path.contains('/') {
                                config_path.split('/').skip(2).collect::<Vec<_>>().join(".")
                            } else {
                                "".to_string()
                            };

                            if key_path.is_empty() {
                                merged_value = staged_value;
                            } else {
                                let _ = set_config_value_at_path(
                                    &mut merged_value,
                                    &key_path,
                                    staged_value,
                                );
                            }

                            if let Err(e) =
                                encoder::encode_file(&merged_value, &structure, &file_path)
                            {
                                return RegistryErrorCode::from(&e) as i32;
                            }
                        }
                    }
                }
            }
        }
    }

    let _ = fs::remove_dir_all(&staging_dir);
    RegistryErrorCode::Success as i32
}

#[no_mangle]
pub extern "C" fn registry_get_pending_changes_json() -> *mut c_char {
    let staging_dir = get_staging_dir();
    if !staging_dir.exists() {
        return cstring_to_ptr("[]");
    }

    let mut changes: Vec<HashMap<String, String>> = Vec::new();

    if let Ok(entries) = fs::read_dir(&staging_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().map_or(false, |e| e == "json") {
                let mut change = HashMap::new();
                if let Some(filename) = path.file_stem().and_then(|s| s.to_str()) {
                    change.insert("file".to_string(), filename.to_string());
                }
                if let Ok(content) = fs::read_to_string(&path) {
                    change.insert("value".to_string(), content);
                }
                changes.push(change);
            }
        }
    }

    match serde_json::to_string(&changes) {
        Ok(json) => cstring_to_ptr(&json),
        Err(_) => null_ptr(),
    }
}
