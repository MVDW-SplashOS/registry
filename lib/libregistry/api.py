from . import definitions

import os


class RegistrySession:
    def __init__(self):
        self.main_definition = definitions.get_main_definition()

        self.categories = {}

    def check_packages_installed(self):
        for category in self.main_definition["packages"]:
            tmp_category = self.main_definition["packages"][category].copy()
            for package in self.main_definition["packages"][category]:
                pkg_definition = definitions.get_package_definition(
                    self.main_definition, category, package
                )
                does_exist = False

                if pkg_definition is not None:
                    for check_path in pkg_definition["detect_installed"]:
                        if os.path.exists(check_path):
                            does_exist = True
                if not does_exist:
                    tmp_category.remove(package)
            self.main_definition["packages"][category] = tmp_category
        return self.main_definition["packages"]
