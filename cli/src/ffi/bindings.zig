const std = @import("std");

extern fn registry_init() *RegistrySessionWrapper;
extern fn registry_free(session: *RegistrySessionWrapper) void;
extern fn registry_get_error_code(err: ?[*:0]const u8) c_int;
extern fn registry_get_main_definition_json() ?[*:0]u8;
extern fn registry_get_package_definition_json(category: ?[*:0]const u8, package: ?[*:0]const u8) ?[*:0]u8;
extern fn registry_get_config_structure_json(category: ?[*:0]const u8, package: ?[*:0]const u8, config_path: ?[*:0]const u8) ?[*:0]u8;
extern fn registry_decode_file_json(file_path: ?[*:0]const u8, structure_json: ?[*:0]const u8) ?[*:0]u8;
extern fn registry_encode_file(data_json: ?[*:0]const u8, structure_json: ?[*:0]const u8, file_path: ?[*:0]const u8) c_int;
extern fn registry_validate_json(data_json: ?[*:0]const u8, structure_json: ?[*:0]const u8) ?[*:0]u8;
extern fn registry_free_string(s: ?[*:0]u8) void;
extern fn registry_check_packages_installed() ?[*:0]u8;

pub const ErrorCode = enum(c_int) {
    success = 0,
    configuration_not_found = 1,
    permission_denied = 2,
    validation_error = 3,
    encoding_error = 4,
    decoding_error = 5,
    definition_error = 6,
    structure_error = 7,
    backup_error = 8,
    dependency_error = 9,
    io_error = 10,
    json_error = 11,
    yaml_error = 12,
    toml_error = 13,
    xml_error = 14,
    unknown_error = 99,
};

pub const RegistrySessionWrapper = opaque {};

pub fn freeString(s: ?[*:0]u8) void {
    if (s) |ptr| {
        registry_free_string(ptr);
    }
}

pub fn getMainDefinition() ?[]u8 {
    const result = registry_get_main_definition_json() orelse return null;
    defer freeString(result);
    return std.mem.sliceTo(result, 0);
}

pub fn checkPackagesInstalled() ?[*:0]u8 {
    return registry_check_packages_installed();
}
