const std = @import("std");
const ffi = @import("ffi");

const Command = enum {
    set,
    get,
    reset,
    apply,
    discard,
    view_changes,
    diff,
    validate,
    validate_config,
    list,
    search,
    info,
    detect,
    backup,
    export_data,
    import_data,
    help,
};

pub fn main() void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    var args = std.process.args();
    _ = args.next();

    var verbose = false;
    var command: ?Command = null;
    var remaining_args: std.ArrayList([]const u8) = .empty;
    defer remaining_args.deinit(allocator);

    while (args.next()) |arg| {
        if (std.mem.eql(u8, arg, "-v") or std.mem.eql(u8, arg, "--verbose")) {
            verbose = true;
        } else if (command == null) {
            command = parseCommand(arg);
        } else {
            remaining_args.append(allocator, arg) catch {};
        }
    }

    if (command) |cmd| {
        executeCommand(cmd, remaining_args) catch |err| {
            std.debug.print("Error: {}\n", .{err});
            std.process.exit(1);
        };
    } else {
        printHelp();
    }
}

fn parseCommand(name: []const u8) ?Command {
    if (std.mem.eql(u8, name, "set")) return .set;
    if (std.mem.eql(u8, name, "get")) return .get;
    if (std.mem.eql(u8, name, "reset")) return .reset;
    if (std.mem.eql(u8, name, "apply")) return .apply;
    if (std.mem.eql(u8, name, "discard")) return .discard;
    if (std.mem.eql(u8, name, "view-changes")) return .view_changes;
    if (std.mem.eql(u8, name, "diff")) return .diff;
    if (std.mem.eql(u8, name, "validate")) return .validate;
    if (std.mem.eql(u8, name, "validate-config")) return .validate_config;
    if (std.mem.eql(u8, name, "list")) return .list;
    if (std.mem.eql(u8, name, "search")) return .search;
    if (std.mem.eql(u8, name, "info")) return .info;
    if (std.mem.eql(u8, name, "detect")) return .detect;
    if (std.mem.eql(u8, name, "backup")) return .backup;
    if (std.mem.eql(u8, name, "export")) return .export_data;
    if (std.mem.eql(u8, name, "import")) return .import_data;
    if (std.mem.eql(u8, name, "help") or std.mem.eql(u8, name, "--help") or std.mem.eql(u8, name, "-h")) return .help;
    return null;
}

fn getArg(args: std.ArrayList([]const u8), index: usize) ?[]const u8 {
    if (index < args.items.len) return args.items[index];
    return null;
}

fn executeCommand(cmd: Command, args: std.ArrayList([]const u8)) !void {
    switch (cmd) {
        .set => {
            const path = getArg(args, 0) orelse {
                std.debug.print("Error: path required\n", .{});
                std.process.exit(1);
            };
            const value = getArg(args, 1) orelse {
                std.debug.print("Error: value required\n", .{});
                std.process.exit(1);
            };
            std.debug.print("Set {s} = {s}\n", .{ path, value });
        },
        .get => {
            const path = getArg(args, 0) orelse {
                std.debug.print("Error: path required\n", .{});
                std.process.exit(1);
            };
            std.debug.print("Getting {s}\n", .{ path });
        },
        .reset => {
            const path = getArg(args, 0) orelse {
                std.debug.print("Error: path required\n", .{});
                std.process.exit(1);
            };
            std.debug.print("Resetting {s}\n", .{ path });
        },
        .apply => std.debug.print("Applying changes...\n", .{}),
        .discard => std.debug.print("Discarding changes...\n", .{}),
        .view_changes => std.debug.print("Viewing changes...\n", .{}),
        .diff => std.debug.print("Showing diff...\n", .{}),
        .validate => std.debug.print("Validating configurations...\n", .{}),
        .validate_config => {
            const path = getArg(args, 0) orelse {
                std.debug.print("Error: path required\n", .{});
                std.process.exit(1);
            };
            std.debug.print("Validating config: {s}\n", .{ path });
        },
        .list => {
            const installed_ptr = ffi.checkPackagesInstalled() orelse {
                std.debug.print("Installed packages: {{}}\n", .{});
                return;
            };
            defer ffi.freeString(installed_ptr);
            const installed = std.mem.sliceTo(installed_ptr, 0);
            std.debug.print("Installed packages: {s}\n", .{ installed });
        },
        .search => {
            const query = getArg(args, 0) orelse {
                std.debug.print("Error: query required\n", .{});
                std.process.exit(1);
            };
            std.debug.print("Searching for: {s}\n", .{ query });
        },
        .info => {
            const pkg = getArg(args, 0) orelse {
                std.debug.print("Error: package required\n", .{});
                std.process.exit(1);
            };
            std.debug.print("Info for: {s}\n", .{ pkg });
        },
        .detect => std.debug.print("Detecting packages...\n", .{}),
        .backup => {
            const action = getArg(args, 0) orelse "list";
            if (std.mem.eql(u8, action, "list")) {
                std.debug.print("Listing backups...\n", .{});
            } else if (std.mem.eql(u8, action, "restore")) {
                const name = getArg(args, 1) orelse {
                    std.debug.print("Error: backup name required\n", .{});
                    std.process.exit(1);
                };
                std.debug.print("Restoring: {s}\n", .{ name });
            } else if (std.mem.eql(u8, action, "delete")) {
                const name = getArg(args, 1) orelse {
                    std.debug.print("Error: backup name required\n", .{});
                    std.process.exit(1);
                };
                std.debug.print("Deleting: {s}\n", .{ name });
            }
        },
        .export_data => std.debug.print("Exporting...\n", .{}),
        .import_data => {
            const file = getArg(args, 0) orelse {
                std.debug.print("Error: file required\n", .{});
                std.process.exit(1);
            };
            std.debug.print("Importing from: {s}\n", .{ file });
        },
        .help => printHelp(),
    }
}

fn printHelp() void {
    std.debug.print("Registry - System configuration management tool\n\n", .{});
    std.debug.print("Usage: registry <command> [options]\n\n", .{});
    std.debug.print("Commands:\n", .{});
    std.debug.print("  set <path> <value>              Set a configuration value\n", .{});
    std.debug.print("  get <path>                      Get a configuration value\n", .{});
    std.debug.print("  reset <path>                    Reset a configuration to default\n", .{});
    std.debug.print("  apply                           Apply pending changes\n", .{});
    std.debug.print("  discard                         Discard pending changes\n", .{});
    std.debug.print("  view-changes                   View pending changes\n", .{});
    std.debug.print("  diff                            Show diff of changes\n", .{});
    std.debug.print("  validate                        Validate all configurations\n", .{});
    std.debug.print("  validate-config <path>         Validate a specific configuration\n", .{});
    std.debug.print("  list                            List all packages\n", .{});
    std.debug.print("  search <query>                  Search for packages\n", .{});
    std.debug.print("  info <package>                  Show package information\n", .{});
    std.debug.print("  detect                          Detect installed packages\n", .{});
    std.debug.print("  backup list                     List backups\n", .{});
    std.debug.print("  backup restore <name>          Restore a backup\n", .{});
    std.debug.print("  backup delete <name>           Delete a backup\n", .{});
    std.debug.print("  export                          Export configuration\n", .{});
    std.debug.print("  import <file>                   Import configuration\n", .{});
    std.debug.print("\nOptions:\n", .{});
    std.debug.print("  -v, --verbose                  Enable verbose output\n", .{});
}
