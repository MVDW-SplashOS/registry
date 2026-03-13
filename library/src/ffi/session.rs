use crate::error::RegistryErrorCode;
use crate::ffi::RegistrySessionWrapper;
use crate::session;
use std::os::raw::c_char;

#[no_mangle]
pub extern "C" fn registry_init() -> *mut RegistrySessionWrapper {
    let session = session::RegistrySession::new();
    Box::into_raw(Box::new(session)) as *mut RegistrySessionWrapper
}

#[no_mangle]
pub extern "C" fn registry_free(session: *mut RegistrySessionWrapper) {
    if !session.is_null() {
        unsafe {
            let _ = Box::from_raw(session as *mut session::RegistrySession);
        }
    }
}

#[no_mangle]
pub extern "C" fn registry_get_error_code(_err: *const c_char) -> i32 {
    RegistryErrorCode::Success as i32
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
}
