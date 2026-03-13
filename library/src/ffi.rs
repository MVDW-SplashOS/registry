use crate::error::{RegistryError, RegistryErrorCode};
use crate::types::ConfigValue;
use crate::{decoder, definitions, encoder, session, validation};
use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::ptr;

#[repr(C)]
pub struct RegistrySessionWrapper {
    _private: [u8; 0],
}

#[repr(C)]
pub struct CStringArray {
    pub data: *mut *mut c_char,
    pub len: usize,
}

#[no_mangle]
pub extern "C" fn registry_init() -> *mut RegistrySessionWrapper {
    let session = session::RegistrySession::new();
    Box::into_raw(Box::new(session)) as *mut RegistrySessionWrapper
}

#[no_mangle]
pub extern "C" fn registry_free(session: *mut RegistrySessionWrapper) {
    if !session.is_null() {
        unsafe {
            Box::from_raw(session as *mut session::RegistrySession);
        }
    }
}

#[no_mangle]
pub extern "C" fn registry_get_error_code(err: *const c_char) -> i32 {
    if err.is_null() {
        return RegistryErrorCode::Success as i32;
    }
    RegistryErrorCode::UnknownError as i32
}

#[no_mangle]
pub extern "C" fn registry_get_main_definition_json() -> *mut c_char {
    let main_def = definitions::get_main_definition();
    match serde_json::to_string(&main_def) {
        Ok(json) => CString::new(json).unwrap_or_default().into_raw(),
        Err(_) => ptr::null_mut(),
    }
}

#[no_mangle]
pub extern "C" fn registry_get_package_definition_json(
    category: *const c_char,
    package: *const c_char,
) -> *mut c_char {
    if category.is_null() || package.is_null() {
        return ptr::null_mut();
    }

    let category = unsafe { CStr::from_ptr(category).to_string_lossy().into_owned() };
    let package = unsafe { CStr::from_ptr(package).to_string_lossy().into_owned() };

    let main_def = definitions::get_main_definition();
    match definitions::get_package_definition(&main_def, &category, &package) {
        Some(pkg_def) => match serde_json::to_string(&pkg_def) {
            Ok(json) => CString::new(json).unwrap_or_default().into_raw(),
            Err(_) => ptr::null_mut(),
        },
        None => ptr::null_mut(),
    }
}

#[no_mangle]
pub extern "C" fn registry_get_config_structure_json(
    category: *const c_char,
    package: *const c_char,
    config_path: *const c_char,
) -> *mut c_char {
    if category.is_null() || package.is_null() || config_path.is_null() {
        return ptr::null_mut();
    }

    let category = unsafe { CStr::from_ptr(category).to_string_lossy().into_owned() };
    let package = unsafe { CStr::from_ptr(package).to_string_lossy().into_owned() };
    let config_path = unsafe { CStr::from_ptr(config_path).to_string_lossy().into_owned() };

    match definitions::get_config_structure(&category, &package, &config_path) {
        Ok(structure) => match serde_json::to_string(&structure) {
            Ok(json) => CString::new(json).unwrap_or_default().into_raw(),
            Err(_) => ptr::null_mut(),
        },
        Err(_) => ptr::null_mut(),
    }
}

#[no_mangle]
pub extern "C" fn registry_decode_file_json(
    file_path: *const c_char,
    structure_json: *const c_char,
) -> *mut c_char {
    if file_path.is_null() || structure_json.is_null() {
        return ptr::null_mut();
    }

    let file_path = unsafe { CStr::from_ptr(file_path).to_string_lossy().into_owned() };
    let structure_json = unsafe {
        CStr::from_ptr(structure_json)
            .to_string_lossy()
            .into_owned()
    };

    let structure: crate::types::ConfigStructure = match serde_json::from_str(&structure_json) {
        Ok(s) => s,
        Err(_) => return ptr::null_mut(),
    };

    let d = decoder::get_decoder();
    match d.decode_file(&file_path, &structure) {
        Ok(value) => match serde_json::to_string(&value) {
            Ok(json) => CString::new(json).unwrap_or_default().into_raw(),
            Err(_) => ptr::null_mut(),
        },
        Err(_) => ptr::null_mut(),
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

    let structure: crate::types::ConfigStructure = match serde_json::from_str(&structure_json) {
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
        return ptr::null_mut();
    }

    let data_json = unsafe { CStr::from_ptr(data_json).to_string_lossy().into_owned() };
    let structure_json = unsafe {
        CStr::from_ptr(structure_json)
            .to_string_lossy()
            .into_owned()
    };

    let data: ConfigValue = match serde_json::from_str(&data_json) {
        Ok(d) => d,
        Err(_) => return ptr::null_mut(),
    };

    let structure: crate::types::ConfigStructure = match serde_json::from_str(&structure_json) {
        Ok(s) => s,
        Err(_) => return ptr::null_mut(),
    };

    match validation::validate(&data, &structure) {
        Ok(errors) => match serde_json::to_string(&errors) {
            Ok(json) => CString::new(json).unwrap_or_default().into_raw(),
            Err(_) => ptr::null_mut(),
        },
        Err(_) => ptr::null_mut(),
    }
}

#[no_mangle]
pub extern "C" fn registry_free_string(s: *mut c_char) {
    if !s.is_null() {
        unsafe {
            CString::from_raw(s);
        }
    }
}

#[no_mangle]
pub extern "C" fn registry_check_packages_installed() -> *mut c_char {
    let session = session::RegistrySession::new();
    let installed = session.check_packages_installed();

    match serde_json::to_string(&installed) {
        Ok(json) => CString::new(json).unwrap_or_default().into_raw(),
        Err(_) => ptr::null_mut(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_init() {
        let session = registry_init();
        assert!(!session.is_null());
        registry_free(session);
    }

    #[test]
    fn test_get_main_definition() {
        let json = registry_get_main_definition_json();
        assert!(!json.is_null());
        registry_free_string(json);
    }
}
