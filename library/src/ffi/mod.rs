pub mod changes;
pub mod config;
pub mod definitions;
pub mod session;

use std::os::raw::c_char;
use std::ptr;

pub use changes::*;
pub use config::*;
pub use definitions::*;
pub use session::*;

#[repr(C)]
pub struct RegistrySessionWrapper {
    _private: [u8; 0],
}

#[repr(C)]
pub struct CStringArray {
    pub data: *mut *mut c_char,
    pub len: usize,
}

pub fn cstring_to_ptr(s: &str) -> *mut c_char {
    std::ffi::CString::new(s)
        .unwrap_or_else(|_| std::ffi::CString::new("").unwrap())
        .into_raw()
}

pub fn null_ptr() -> *mut c_char {
    ptr::null_mut()
}
