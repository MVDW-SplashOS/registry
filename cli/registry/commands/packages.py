import sys
import yaml
from pathlib import Path
from typing import Any

from .base import Command


class ListCommand(Command):
    name = "list"
    help = "List available packages"

    @classmethod
    def _add_arguments(cls, parser):
        parser.add_argument("category", nargs="?", help="Category to list (optional)")
        parser.add_argument(
            "--detected", "-d", action="store_true", help="Show only detected packages"
        )

    def execute(self, args: Any) -> None:
        try:
            category = args.category
            detected_only = args.detected

            definitions_dir = self.core.get_definitions_dir()

            categories = []
            packages = {}

            if definitions_dir.exists():
                for cat_dir in sorted(definitions_dir.iterdir()):
                    if cat_dir.is_dir() and not cat_dir.name.startswith("."):
                        if category and cat_dir.name != category:
                            continue

                        cat_packages = []
                        for pkg_dir in sorted(cat_dir.iterdir()):
                            if (
                                pkg_dir.is_dir()
                                and (pkg_dir / "manifest.yaml").exists()
                            ):
                                manifest_path = pkg_dir / "manifest.yaml"
                                with open(manifest_path) as f:
                                    manifest = yaml.safe_load(f)

                                pkg_info = {
                                    "name": pkg_dir.name,
                                    "version": manifest.get("application", {}).get(
                                        "version", "unknown"
                                    ),
                                    "detected": False,
                                }

                                if not detected_only:
                                    cat_packages.append(pkg_info)
                                else:
                                    detect_paths = manifest.get("detect_installed", [])
                                    is_installed = any(
                                        Path(p).exists() for p in detect_paths
                                    )
                                    if is_installed:
                                        pkg_info["detected"] = True
                                        cat_packages.append(pkg_info)

                        if cat_packages:
                            categories.append(cat_dir.name)
                            packages[cat_dir.name] = cat_packages

            if category:
                print(f"Packages in '{category}':")
                if category in packages:
                    for pkg in packages[category]:
                        status = (
                            " [installed]" if detected_only and pkg["detected"] else ""
                        )
                        print(f"  - {pkg['name']} (v{pkg['version']}){status}")
                else:
                    print("  No packages found")
            else:
                print("Available packages:")
                print("=" * 50)
                for cat in categories:
                    print(f"\n{cat}:")
                    for pkg in packages[cat]:
                        status = " [installed]" if pkg["detected"] else ""
                        print(f"  - {pkg['name']} (v{pkg['version']}){status}")
                print("\n" + "=" * 50)

        except Exception as e:
            print(f"Error listing packages: {e}")
            if self.verbose:
                import traceback

                traceback.print_exc()
            sys.exit(1)


class SearchCommand(Command):
    name = "search"
    help = "Search for packages"

    @classmethod
    def _add_arguments(cls, parser):
        parser.add_argument("query", help="Search query")

    def execute(self, args: Any) -> None:
        try:
            query = args.query
            definitions_dir = self.core.get_definitions_dir()

            results = []

            if definitions_dir.exists():
                for cat_dir in definitions_dir.iterdir():
                    if cat_dir.is_dir() and not cat_dir.name.startswith("."):
                        for pkg_dir in cat_dir.iterdir():
                            if (
                                pkg_dir.is_dir()
                                and (pkg_dir / "manifest.yaml").exists()
                            ):
                                manifest_path = pkg_dir / "manifest.yaml"
                                with open(manifest_path) as f:
                                    manifest = yaml.safe_load(f)

                                pkg_name = pkg_dir.name
                                app_name = (
                                    manifest.get("application", {})
                                    .get("name", "")
                                    .lower()
                                )
                                query_lower = query.lower()

                                if query_lower in pkg_name or query_lower in app_name:
                                    results.append(
                                        {
                                            "category": cat_dir.name,
                                            "name": pkg_name,
                                            "version": manifest.get(
                                                "application", {}
                                            ).get("version", "unknown"),
                                        }
                                    )

            if results:
                print(f"Search results for '{query}':")
                print("=" * 50)
                for result in results:
                    print(
                        f"  {result['category']}/{result['name']} (v{result['version']})"
                    )
                print("=" * 50)
            else:
                print(f"No results found for '{query}'")

        except Exception as e:
            print(f"Error searching: {e}")
            sys.exit(1)


class InfoCommand(Command):
    name = "info"
    help = "Show package information"

    @classmethod
    def _add_arguments(cls, parser):
        parser.add_argument("package", help="Package (category/name)")

    def execute(self, args: Any) -> None:
        try:
            package = args.package
            parts = package.split("/")
            if len(parts) != 2:
                print("Invalid package format. Use: category/package")
                sys.exit(1)

            category, pkg_name = parts

            definitions_dir = self.core.get_definitions_dir()
            pkg_dir = definitions_dir / category / pkg_name
            if not pkg_dir.exists():
                print(f"Package not found: {category}/{pkg_name}")
                sys.exit(1)

            manifest_path = pkg_dir / "manifest.yaml"
            if not manifest_path.exists():
                print(f"No manifest found for {category}/{pkg_name}")
                sys.exit(1)

            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)

            print(f"Package: {pkg_name}")
            print("=" * 50)
            print(f"Category: {category}")
            print(
                f"Version: {manifest.get('application', {}).get('version', 'unknown')}"
            )
            print(
                f"Definition version: {manifest.get('definition', {}).get('libregistry_minimum_version', 'unknown')}"
            )

            structures = manifest.get("structure", {})
            if structures:
                print("\nConfiguration files:")
                for struct_name, struct_file in structures.items():
                    struct_path = pkg_dir / f"{struct_file}.yaml"
                    if not struct_path.exists():
                        struct_path = pkg_dir / struct_file

                    if struct_path.exists():
                        with open(struct_path) as f:
                            struct_def = yaml.safe_load(f)

                        file_info = struct_def.get("file", {})
                        location = file_info.get("location", "unknown")
                        format_type = file_info.get("format", "unknown")
                        print(f"  - {struct_name}: {location} (format: {format_type})")

            detect_paths = manifest.get("detect_installed", [])
            if detect_paths:
                print("\nDetection paths:")
                for path in detect_paths:
                    exists = Path(path).exists()
                    status = "[installed]" if exists else "[not found]"
                    print(f"  - {path} {status}")

        except Exception as e:
            print(f"Error getting info: {e}")
            sys.exit(1)


class DetectCommand(Command):
    name = "detect"
    help = "Detect installed packages"

    @classmethod
    def _add_arguments(cls, parser):
        parser.add_argument("package", nargs="?", help="Package to check (optional)")

    def execute(self, args: Any) -> None:
        list_cmd = ListCommand(self.core)
        list_cmd.execute(
            type("Args", (), {"category": args.package, "detected": True})()
        )
