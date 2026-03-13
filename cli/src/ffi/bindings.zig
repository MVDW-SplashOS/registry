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
extern fn registry_get_config(category: [*]const u8, package: [*]const u8, config_path: [*]const u8) ?[*:0]const u8;
extern fn registry_set_config(category: [*]const u8, package: [*]const u8, config_path: [*]const u8, value_json: [*]const u8) c_int;
extern fn registry_discard_changes() c_int;
extern fn registry_apply_changes() c_int;
extern fn registry_get_pending_changes_json() ?[*:0]u8;
extern fn registry_get_completions(prefix: [*]const u8) ?[*:0]const u8;

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

pub fn freeString(s: [*]const u8) void {
    // Leak the memory for now to avoid type issues
    _ = s;
}

pub fn freeStringOptional(s: ?[*]const u8) void {
    // Leak the memory for now to avoid type issues
    _ = s;
}

pub fn getMainDefinition() ?[]u8 {
    const result = registry_get_main_definition_json() orelse return null;
    defer freeString(result);
    return std.mem.sliceTo(result, 0);
}

pub fn checkPackagesInstalled() ?[*:0]u8 {
    return registry_check_packages_installed();
}

pub fn getConfig(category: []const u8, package: []const u8, config_path: []const u8, allocator: std.mem.Allocator) ?[]u8 {
    const category_buf = allocator.alloc(u8, category.len + 1) catch return null;
    defer allocator.free(category_buf);
    @memcpy(category_buf[0..category.len], category);
    category_buf[category.len] = 0;

    const package_buf = allocator.alloc(u8, package.len + 1) catch return null;
    defer allocator.free(package_buf);
    @memcpy(package_buf[0..package.len], package);
    package_buf[package.len] = 0;

    const config_path_buf = allocator.alloc(u8, config_path.len + 1) catch return null;
    defer allocator.free(config_path_buf);
    @memcpy(config_path_buf[0..config_path.len], config_path);
    config_path_buf[config_path.len] = 0;

    const result = registry_get_config(category_buf.ptr, package_buf.ptr, config_path_buf.ptr) orelse return null;
    defer freeStringOptional(result);
    const slice = std.mem.sliceTo(result, 0);
    // Copy to owned slice
    const result_copy = allocator.alloc(u8, slice.len) catch return null;
    @memcpy(result_copy, slice);
    return result_copy;
}

pub fn setConfig(category: []const u8, package: []const u8, config_path: []const u8, value_json: []const u8, allocator: std.mem.Allocator) ErrorCode {
    const category_buf = allocator.alloc(u8, category.len + 1) catch return .unknown_error;
    defer allocator.free(category_buf);
    @memcpy(category_buf[0..category.len], category);
    category_buf[category.len] = 0;

    const package_buf = allocator.alloc(u8, package.len + 1) catch return .unknown_error;
    defer allocator.free(package_buf);
    @memcpy(package_buf[0..package.len], package);
    package_buf[package.len] = 0;

    const config_path_buf = allocator.alloc(u8, config_path.len + 1) catch return .unknown_error;
    defer allocator.free(config_path_buf);
    @memcpy(config_path_buf[0..config_path.len], config_path);
    config_path_buf[config_path.len] = 0;

    const value_json_buf = allocator.alloc(u8, value_json.len + 1) catch return .unknown_error;
    defer allocator.free(value_json_buf);
    @memcpy(value_json_buf[0..value_json.len], value_json);
    value_json_buf[value_json.len] = 0;

    const result = registry_set_config(category_buf.ptr, package_buf.ptr, config_path_buf.ptr, value_json_buf.ptr);
    return intToErrorCode(result);
}

pub fn discardChanges() ErrorCode {
    const result = registry_discard_changes();
    return intToErrorCode(result);
}

pub fn applyChanges() ErrorCode {
    const result = registry_apply_changes();
    return intToErrorCode(result);
}

pub fn getPendingChangesJson() ?[]u8 {
    const result = registry_get_pending_changes_json() orelse return null;
    defer freeString(result);
    return std.mem.sliceTo(result, 0);
}

pub fn getCompletions(path: []const u8, current: []const u8, allocator: std.mem.Allocator) ?[][]u8 {
    // Combine path and current into a single prefix string for filtering
    var prefix_for_ffi: []const u8 = undefined;

    if (path.len > 0 and current.len > 0) {
        // Combine as "category/package/partial" or just pass path and let FFI filter
        // Actually, we need to pass path + partial to FFI so it can filter
        // The format should be "path/partial" without trailing /
        const sep = if (path[path.len - 1] == '/') "" else "/";
        prefix_for_ffi = std.fmt.allocPrint(allocator, "{s}{s}{s}", .{ path, sep, current }) catch return null;
    } else if (path.len > 0) {
        prefix_for_ffi = path;
    } else {
        prefix_for_ffi = current;
    }
    defer {
        if (prefix_for_ffi.len > 0 and path.len > 0 and current.len > 0) {
            allocator.free(@constCast(prefix_for_ffi));
        }
    }

    const prefix_buf = allocator.alloc(u8, prefix_for_ffi.len + 1) catch return null;
    defer allocator.free(prefix_buf);
    @memcpy(prefix_buf[0..prefix_for_ffi.len], prefix_for_ffi);
    prefix_buf[prefix_for_ffi.len] = 0;

    const result = registry_get_completions(prefix_buf.ptr) orelse return null;
    defer freeString(result);
    const json_str = std.mem.sliceTo(result, 0);

    // Parse JSON array of strings
    // Simple parser for string array
    if (json_str.len < 2 or json_str[0] != '[' or json_str[json_str.len - 1] != ']') {
        return null;
    }

    var completions: std.ArrayList([]u8) = .empty;
    defer completions.deinit(allocator);

    var i: usize = 1;
    while (i < json_str.len) {
        // Skip whitespace
        while (i < json_str.len and (json_str[i] == ' ' or json_str[i] == ',')) : (i += 1) {}
        if (i >= json_str.len) break;

        // Expect opening quote
        if (json_str[i] != '"') break;
        i += 1;

        // Find closing quote
        var end = i;
        while (end < json_str.len and json_str[end] != '"') : (end += 1) {}

        // Copy the string (without quotes)
        const completion = allocator.alloc(u8, end - i) catch return null;
        @memcpy(completion, json_str[i..end]);
        completions.append(allocator, completion) catch return null;

        i = end + 1;
    }

    // Convert to slice of slices
    const result_completions = allocator.alloc([]u8, completions.items.len) catch return null;
    @memcpy(result_completions, completions.items);
    return result_completions;
}

fn intToErrorCode(value: c_int) ErrorCode {
    return @enumFromInt(value);
}
