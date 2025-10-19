from libregistry.api import RegistrySession


def main():
    registry_session = RegistrySession()
    pkg = registry_session.check_packages_installed()
    # print(pkg)


if __name__ == "__main__":
    main()
