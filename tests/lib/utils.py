import pytest
import json
import yaml


def assert_roundtrip(encoder, decoder, data, structure):
    """Test that encode followed by decode returns the original data."""
    encoded = encoder.encode(data, structure)
    decoded = decoder.decode(encoded, structure)
    assert decoded == data, "Roundtrip failed: decoded data does not match original"


def assert_validation_errors(validator, data, structure, expect_errors=True):
    """Test that validation returns expected number of errors."""
    errors = validator.validate(data, structure)
    if expect_errors:
        assert len(errors) > 0, "Expected validation errors but got none"
    else:
        assert len(errors) == 0, f"Expected no validation errors but got: {errors}"


def create_test_structure(format_type, **options):
    """Helper to create test structures."""
    structure = {"format": format_type}
    structure.update(options)
    return structure


def compare_dicts(dict1, dict2, path=""):
    """Recursively compare two dicts and return list of differences."""
    differences = []
    for key in dict1:
        new_path = f"{path}.{key}" if path else key
        if key not in dict2:
            differences.append(f"Missing key: {new_path}")
        elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            differences.extend(compare_dicts(dict1[key], dict2[key], new_path))
        elif dict1[key] != dict2[key]:
            differences.append(f"Value at {new_path}: {dict1[key]} != {dict2[key]}")
    for key in dict2:
        if key not in dict1:
            new_path = f"{path}.{key}" if path else key
            differences.append(f"Extra key: {new_path}")
    return differences


def generate_test_data(depth=0, max_depth=3):
    """Generate nested test data for testing."""
    if depth >= max_depth:
        return "value"
    
    return {
        f"level_{depth}_key": generate_test_data(depth + 1, max_depth),
        f"level_{depth}_list": [1, 2, 3] if depth < max_depth - 1 else []
    }


def parse_json_safe(content):
    """Safely parse JSON, return None on error."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def parse_yaml_safe(content):
    """Safely parse YAML, return None on error."""
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError:
        return None
