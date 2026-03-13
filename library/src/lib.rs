pub mod constants;
pub mod decoder;
pub mod definitions;
pub mod encoder;
pub mod error;
pub mod ffi;
pub mod session;
pub mod types;
pub mod utils;
pub mod validation;

pub use constants::DEFINITIONS_DIR;
pub use definitions::{get_main_definition, get_package_definition};
pub use error::{RegistryError, Result};
pub use session::RegistrySession;
pub use types::ConfigValue;

#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
        assert_eq!(2 + 2, 4);
    }
}
