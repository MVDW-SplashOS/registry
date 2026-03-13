use crate::constants::STAGING_DIR_NAME;
use crate::error::RegistryErrorCode;
use crate::ffi::{cstring_to_ptr, null_ptr};
use crate::types::{ConfigStructure, ConfigValue, SchemaProperty};
use crate::{decoder, definitions, encoder};
use std::collections::HashMap;
use std::ffi::CStr;
use std::fs;
use std::os::raw::c_char;
use std::path::PathBuf;

#[derive(serde::Deserialize)]
#[allow(dead_code)]
struct DefinitionFile {
    file: DefinitionFileInfo,
    format: Option<String>,
    syntax: Option<SyntaxInfo>,
    structures: Option<StructuresInfo>,
}

#[derive(serde::Deserialize)]
#[allow(dead_code)]
struct DefinitionFileInfo {
    location: String,
    format: Option<String>,
    encoding: Option<String>,
    permissions: Option<String>,
    owner: Option<String>,
    group: Option<String>,
}

#[derive(serde::Deserialize)]
#[allow(dead_code)]
struct SyntaxInfo {
    comment_char: Option<String>,
    line_continuation: Option<String>,
    case_sensitive: Option<bool>,
    delimiter: Option<String>,
}

#[derive(serde::Deserialize)]
struct StructuresInfo {
    main: Option<MainStructure>,
}

#[derive(serde::Deserialize)]
struct MainStructure {
    options: Option<HashMap<String, OptionField>>,
}

#[derive(serde::Deserialize)]
#[allow(dead_code)]
struct OptionField {
    #[serde(default)]
    r#type: Option<String>,
    #[serde(default)]
    default: Option<String>,
    #[serde(default)]
    description: Option<String>,
}

fn get_staging_dir() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());
    PathBuf::from(home).join(STAGING_DIR_NAME).join("staging")
}

fn convert_to_config_structure(def: &DefinitionFile) -> ConfigStructure {
    let schema = def.structures.as_ref().and_then(|s| {
        s.main.as_ref().and_then(|m| {
            m.options.as_ref().map(|opts| {
                let mut properties = HashMap::new();
                let mut required_fields = Vec::new();

                for (key, field) in opts {
                    if field.default.is_none() {
                        required_fields.push(key.clone());
                    }
                    properties.insert(
                        key.clone(),
                        SchemaProperty {
                            r#type: field.r#type.clone(),
                            format: None,
                        },
                    );
                }

                crate::types::Schema {
                    r#type: None,
                    properties: Some(properties),
                    required: if required_fields.is_empty() {
                        None
                    } else {
                        Some(required_fields)
                    },
                }
            })
        })
    });

    ConfigStructure {
        file: crate::types::FileInfo {
            location: def.file.location.clone(),
        },
        format: def.file.format.clone(),
        schema,
        formatting: None,
        validation: None,
    }
}

fn find_structure_file(
    definitions_dir: &str,
    category: &str,
    package: &str,
    config_key: &str,
    structure: &crate::types::PackageDefinition,
) -> Option<PathBuf> {
    let structure_file = structure
        .structure
        .get(config_key)
        .map(|s| {
            if s.ends_with(".yaml") {
                s.clone()
            } else {
                format!("{}.yaml", s)
            }
        })
        .unwrap_or_else(|| format!("{}.yaml", config_key));

    let struct_path = PathBuf::from(definitions_dir)
        .join(category)
        .join(package)
        .join(&structure_file);

    if struct_path.exists() {
        Some(struct_path)
    } else {
        None
    }
}

fn read_definition_file(path: &PathBuf) -> Option<(DefinitionFile, ConfigStructure)> {
    let content = fs::read_to_string(path).ok()?;
    let def_file: DefinitionFile = serde_yaml::from_str(&content).ok()?;
    let structure = convert_to_config_structure(&def_file);
    Some((def_file, structure))
}

#[allow(dead_code)]
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
pub extern "C" fn registry_decode_file_json(
    file_path: *const c_char,
    structure_json: *const c_char,
) -> *mut c_char {
    if file_path.is_null() || structure_json.is_null() {
        return null_ptr();
    }

    let file_path = unsafe { CStr::from_ptr(file_path).to_string_lossy().into_owned() };
    let structure_json = unsafe {
        CStr::from_ptr(structure_json)
            .to_string_lossy()
            .into_owned()
    };

    let structure: ConfigStructure = match serde_json::from_str(&structure_json) {
        Ok(s) => s,
        Err(_) => return null_ptr(),
    };

    let d = decoder::get_decoder();
    match d.decode_file(&file_path, &structure) {
        Ok(value) => match serde_json::to_string(&value) {
            Ok(json) => cstring_to_ptr(&json),
            Err(_) => null_ptr(),
        },
        Err(_) => null_ptr(),
    }
}

#[no_mangle]
pub extern "C" fn registry_encode_file(
    data_json: *const c_char,
    structure_json: *const c_char,
    file_path: *const c_char,
) -> i32 {
    if data_json.is_null() || structure_json.is_null() || file_path.is_null() {
        return RegistryErrorCode::UnknownError as i32;
    }

    let data_json = unsafe { CStr::from_ptr(data_json).to_string_lossy().into_owned() };
    let structure_json = unsafe {
        CStr::from_ptr(structure_json)
            .to_string_lossy()
            .into_owned()
    };
    let file_path = unsafe { CStr::from_ptr(file_path).to_string_lossy().into_owned() };

    let data: ConfigValue = match serde_json::from_str(&data_json) {
        Ok(d) => d,
        Err(_) => return RegistryErrorCode::JsonError as i32,
    };

    let structure: ConfigStructure = match serde_json::from_str(&structure_json) {
        Ok(s) => s,
        Err(_) => return RegistryErrorCode::JsonError as i32,
    };

    match encoder::encode_file(&data, &structure, &file_path) {
        Ok(_) => RegistryErrorCode::Success as i32,
        Err(e) => RegistryErrorCode::from(&e) as i32,
    }
}

#[no_mangle]
pub extern "C" fn registry_validate_json(
    data_json: *const c_char,
    structure_json: *const c_char,
) -> *mut c_char {
    if data_json.is_null() || structure_json.is_null() {
        return null_ptr();
    }

    let data_json = unsafe { CStr::from_ptr(data_json).to_string_lossy().into_owned() };
    let structure_json = unsafe {
        CStr::from_ptr(structure_json)
            .to_string_lossy()
            .into_owned()
    };

    let data: ConfigValue = match serde_json::from_str(&data_json) {
        Ok(d) => d,
        Err(_) => return null_ptr(),
    };

    let structure: ConfigStructure = match serde_json::from_str(&structure_json) {
        Ok(s) => s,
        Err(_) => return null_ptr(),
    };

    match crate::validation::validate(&data, &structure) {
        Ok(errors) => match serde_json::to_string(&errors) {
            Ok(json) => cstring_to_ptr(&json),
            Err(_) => null_ptr(),
        },
        Err(_) => null_ptr(),
    }
}

#[no_mangle]
pub extern "C" fn registry_get_config(
    category: *const c_char,
    package: *const c_char,
    config_path: *const c_char,
) -> *mut c_char {
    if category.is_null() || package.is_null() || config_path.is_null() {
        return null_ptr();
    }

    let category = unsafe { CStr::from_ptr(category).to_string_lossy().into_owned() };
    let package = unsafe { CStr::from_ptr(package).to_string_lossy().into_owned() };
    let config_key = unsafe { CStr::from_ptr(config_path).to_string_lossy().into_owned() };

    let main_def = definitions::get_main_definition();
    let pkg_def = match definitions::get_package_definition(&main_def, &category, &package) {
        Some(p) => p,
        None => return null_ptr(),
    };

    let definitions_dir = definitions::get_definitions_dir();

    let struct_path =
        match find_structure_file(definitions_dir, &category, &package, &config_key, &pkg_def) {
            Some(p) => p,
            None => return null_ptr(),
        };

    let (_def_file, structure) = match read_definition_file(&struct_path) {
        Some(s) => s,
        None => return null_ptr(),
    };

    let file_path = &structure.file.location;
    if !PathBuf::from(file_path).exists() {
        return null_ptr();
    }

    let d = decoder::get_decoder();
    let decoded = match d.decode_file(file_path, &structure) {
        Ok(v) => v,
        Err(_) => return null_ptr(),
    };

    match serde_json::to_string(&decoded) {
        Ok(json) => cstring_to_ptr(&json),
        Err(_) => null_ptr(),
    }
}

#[no_mangle]
pub extern "C" fn registry_set_config(
    category: *const c_char,
    package: *const c_char,
    config_path: *const c_char,
    value_json: *const c_char,
) -> i32 {
    if category.is_null() || package.is_null() || config_path.is_null() || value_json.is_null() {
        return RegistryErrorCode::UnknownError as i32;
    }

    let category = unsafe { CStr::from_ptr(category).to_string_lossy().into_owned() };
    let package = unsafe { CStr::from_ptr(package).to_string_lossy().into_owned() };
    let config_key = unsafe { CStr::from_ptr(config_path).to_string_lossy().into_owned() };
    let value_json = unsafe { CStr::from_ptr(value_json).to_string_lossy().into_owned() };

    let value: ConfigValue = match serde_json::from_str(&value_json) {
        Ok(v) => v,
        Err(_) => return RegistryErrorCode::JsonError as i32,
    };

    let main_def = definitions::get_main_definition();
    let pkg_def = match definitions::get_package_definition(&main_def, &category, &package) {
        Some(p) => p,
        None => return RegistryErrorCode::DefinitionError as i32,
    };

    let definitions_dir = definitions::get_definitions_dir();

    let struct_path =
        match find_structure_file(definitions_dir, &category, &package, &config_key, &pkg_def) {
            Some(p) => p,
            None => return RegistryErrorCode::StructureError as i32,
        };

    let (_def_file, structure) = match read_definition_file(&struct_path) {
        Some(s) => s,
        None => return RegistryErrorCode::YamlError as i32,
    };

    let file_path = structure.file.location.clone();

    let staging_dir = get_staging_dir();
    if let Err(_e) = fs::create_dir_all(&staging_dir) {
        return RegistryErrorCode::IoError as i32;
    }

    let staging_file = staging_dir.join(format!("{}_{}_{}.json", category, package, config_key));

    let _staged_data = if staging_file.exists() {
        fs::read_to_string(&staging_file).unwrap_or_else(|_| "{}".to_string())
    } else if PathBuf::from(&file_path).exists() {
        let d = decoder::get_decoder();
        match d.decode_file(&file_path, &structure) {
            Ok(v) => serde_json::to_string(&v).unwrap_or_else(|_| "{}".to_string()),
            Err(_) => "{}".to_string(),
        }
    } else {
        "{}".to_string()
    };

    let current_value = value;

    match serde_json::to_string_pretty(&current_value) {
        Ok(json) => {
            if let Err(_e) = fs::write(&staging_file, json) {
                return RegistryErrorCode::IoError as i32;
            }
            RegistryErrorCode::Success as i32
        }
        Err(_) => RegistryErrorCode::JsonError as i32,
    }
}

#[no_mangle]
pub extern "C" fn registry_free_string(s: *mut c_char) {
    if !s.is_null() {
        unsafe {
            let _ = std::ffi::CString::from_raw(s);
        }
    }
}
