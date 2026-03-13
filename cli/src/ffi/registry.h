#ifndef REGISTRY_H
#define REGISTRY_H

#include <stddef.h>

struct RegistrySessionWrapper;

struct CStringArray {
    char** data;
    size_t len;
};

struct RegistrySessionWrapper* registry_init();
void registry_free(struct RegistrySessionWrapper* session);
int registry_get_error_code(const char* err);
char* registry_get_main_definition_json();
char* registry_get_package_definition_json(const char* category, const char* package);
char* registry_get_config_structure_json(const char* category, const char* package, const char* config_path);
char* registry_decode_file_json(const char* file_path, const char* structure_json);
int registry_encode_file(const char* data_json, const char* structure_json, const char* file_path);
char* registry_validate_json(const char* data_json, const char* structure_json);
void registry_free_string(char* s);
char* registry_check_packages_installed();

#endif
