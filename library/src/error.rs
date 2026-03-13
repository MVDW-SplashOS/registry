use thiserror::Error;

#[derive(Error, Debug)]
pub enum RegistryError {
    #[error("Configuration not found: {0}")]
    ConfigurationNotFound(String),

    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    #[error("Validation error: {0}")]
    ValidationError(String),

    #[error("Encoding error: {0}")]
    EncodingError(String),

    #[error("Decoding error: {0}")]
    DecodingError(String),

    #[error("Definition error: {0}")]
    DefinitionError(String),

    #[error("Structure error: {0}")]
    StructureError(String),

    #[error("Backup error: {0}")]
    BackupError(String),

    #[error("Dependency error: {0}")]
    DependencyError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("JSON error: {0}")]
    JsonError(#[from] serde_json::Error),

    #[error("YAML error: {0}")]
    YamlError(#[from] serde_yaml::Error),

    #[error("TOML error: {0}")]
    TomlError(#[from] toml::de::Error),

    #[error("XML error: {0}")]
    XmlError(String),
}

pub type Result<T> = std::result::Result<T, RegistryError>;

#[repr(i32)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RegistryErrorCode {
    Success = 0,
    ConfigurationNotFound = 1,
    PermissionDenied = 2,
    ValidationError = 3,
    EncodingError = 4,
    DecodingError = 5,
    DefinitionError = 6,
    StructureError = 7,
    BackupError = 8,
    DependencyError = 9,
    IoError = 10,
    JsonError = 11,
    YamlError = 12,
    TomlError = 13,
    XmlError = 14,
    UnknownError = 99,
}

impl From<&RegistryError> for RegistryErrorCode {
    fn from(err: &RegistryError) -> Self {
        match err {
            RegistryError::ConfigurationNotFound(_) => RegistryErrorCode::ConfigurationNotFound,
            RegistryError::PermissionDenied(_) => RegistryErrorCode::PermissionDenied,
            RegistryError::ValidationError(_) => RegistryErrorCode::ValidationError,
            RegistryError::EncodingError(_) => RegistryErrorCode::EncodingError,
            RegistryError::DecodingError(_) => RegistryErrorCode::DecodingError,
            RegistryError::DefinitionError(_) => RegistryErrorCode::DefinitionError,
            RegistryError::StructureError(_) => RegistryErrorCode::StructureError,
            RegistryError::BackupError(_) => RegistryErrorCode::BackupError,
            RegistryError::DependencyError(_) => RegistryErrorCode::DependencyError,
            RegistryError::IoError(_) => RegistryErrorCode::IoError,
            RegistryError::JsonError(_) => RegistryErrorCode::JsonError,
            RegistryError::YamlError(_) => RegistryErrorCode::YamlError,
            RegistryError::TomlError(_) => RegistryErrorCode::TomlError,
            RegistryError::XmlError(_) => RegistryErrorCode::XmlError,
        }
    }
}
