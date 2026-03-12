import pytest
import sys
import json
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))

from libregistry.transformer.transformer import (
    DataTransformer,
    FormatTransformer,
    StructureTransformer,
    Transformer,
)


class TestFormatTransformer:
    def setup_method(self):
        self.transformer = FormatTransformer()

    def test_transform_json_to_yaml(self):
        data = {"key": "value"}
        transformation = {
            "source_format": "json",
            "target_format": "yaml"
        }
        result = self.transformer.transform(data, transformation)
        assert "key" in result
        assert "value" in result

    def test_transform_yaml_to_json(self):
        data = {"key": "value"}
        transformation = {
            "source_format": "yaml",
            "target_format": "json"
        }
        result = self.transformer.transform(data, transformation)
        assert '"key"' in result

    def test_transform_json_to_dict(self):
        data = {"key": "value"}
        transformation = {
            "source_format": "json",
            "target_format": "dict"
        }
        result = self.transformer.transform(data, transformation)
        assert result == {"key": "value"}

    def test_transform_dict_to_json(self):
        data = {"key": "value"}
        transformation = {
            "source_format": "dict",
            "target_format": "json"
        }
        result = self.transformer.transform(data, transformation)
        assert '"key"' in result

    def test_transform_auto_detect_json_string(self):
        data = '{"key": "value"}'
        transformation = {
            "source_format": "auto",
            "target_format": "dict"
        }
        result = self.transformer.transform(data, transformation)
        assert result == {"key": "value"}

    def test_transform_auto_detect_yaml_string(self):
        data = "key: value"
        transformation = {
            "source_format": "auto",
            "target_format": "dict"
        }
        result = self.transformer.transform(data, transformation)
        assert result == {"key": "value"}

    def test_transform_with_custom_indent(self):
        data = {"key": {"nested": "value"}}
        transformation = {
            "source_format": "dict",
            "target_format": "json",
            "indent": 4
        }
        result = self.transformer.transform(data, transformation)
        assert "    " in result

    def test_transform_unsupported_source_format(self):
        data = {"key": "value"}
        transformation = {
            "source_format": "xml",
            "target_format": "json"
        }
        with pytest.raises(ValueError) as exc_info:
            self.transformer.transform(data, transformation)
        assert "Unsupported source format" in str(exc_info.value)

    def test_transform_unsupported_target_format(self):
        data = {"key": "value"}
        transformation = {
            "source_format": "json",
            "target_format": "xml"
        }
        with pytest.raises(ValueError) as exc_info:
            self.transformer.transform(data, transformation)
        assert "Unsupported target format" in str(exc_info.value)

    def test_transform_target_format_required(self):
        data = {"key": "value"}
        transformation = {
            "source_format": "json"
        }
        with pytest.raises(ValueError) as exc_info:
            self.transformer.transform(data, transformation)
        assert "Target format must be specified" in str(exc_info.value)

    def test_can_transform_supported_formats(self):
        assert self.transformer.can_transform("json", "yaml")
        assert self.transformer.can_transform("yaml", "json")
        assert self.transformer.can_transform("json", "dict")
        assert self.transformer.can_transform("dict", "json")

    def test_can_transform_unsupported(self):
        assert not self.transformer.can_transform("json", "xml")
        assert not self.transformer.can_transform("csv", "json")

    def test_transform_rename_key(self):
        data = {"old_key": "value"}
        transformation = {
            "source_format": "dict",
            "target_format": "dict",
            "transformations": [
                {"type": "rename_key", "old_key": "old_key", "new_key": "new_key"}
            ]
        }
        result = self.transformer.transform(data, transformation)
        assert "new_key" in result
        assert result["new_key"] == "value"
        assert "old_key" not in result

    def test_transform_delete_key(self):
        data = {"key1": "value1", "key2": "value2"}
        transformation = {
            "source_format": "dict",
            "target_format": "dict",
            "transformations": [
                {"type": "delete_key", "key": "key1"}
            ]
        }
        result = self.transformer.transform(data, transformation)
        assert "key1" not in result
        assert "key2" in result

    def test_transform_add_key(self):
        data = {"key1": "value1"}
        transformation = {
            "source_format": "dict",
            "target_format": "dict",
            "transformations": [
                {"type": "add_key", "key": "key2", "value": "value2"}
            ]
        }
        result = self.transformer.transform(data, transformation)
        assert "key2" in result
        assert result["key2"] == "value2"

    def test_transform_value_to_lower(self):
        data = {"key": "HELLO"}
        transformation = {
            "source_format": "dict",
            "target_format": "dict",
            "transformations": [
                {"type": "transform_value", "key": "key", "function": "to_lower"}
            ]
        }
        result = self.transformer.transform(data, transformation)
        assert result["key"] == "hello"

    def test_transform_value_to_upper(self):
        data = {"key": "hello"}
        transformation = {
            "source_format": "dict",
            "target_format": "dict",
            "transformations": [
                {"type": "transform_value", "key": "key", "function": "to_upper"}
            ]
        }
        result = self.transformer.transform(data, transformation)
        assert result["key"] == "HELLO"

    def test_transform_value_to_int(self):
        data = {"key": "42"}
        transformation = {
            "source_format": "dict",
            "target_format": "dict",
            "transformations": [
                {"type": "transform_value", "key": "key", "function": "to_int"}
            ]
        }
        result = self.transformer.transform(data, transformation)
        assert result["key"] == 42

    def test_transform_value_to_float(self):
        data = {"key": "3.14"}
        transformation = {
            "source_format": "dict",
            "target_format": "dict",
            "transformations": [
                {"type": "transform_value", "key": "key", "function": "to_float"}
            ]
        }
        result = self.transformer.transform(data, transformation)
        assert result["key"] == 3.14

    def test_transform_value_to_boolean(self):
        data = {"key": "true"}
        transformation = {
            "source_format": "dict",
            "target_format": "dict",
            "transformations": [
                {"type": "transform_value", "key": "key", "function": "to_boolean"}
            ]
        }
        result = self.transformer.transform(data, transformation)
        assert result["key"] is True

    def test_transform_value_trim(self):
        data = {"key": "  hello  "}
        transformation = {
            "source_format": "dict",
            "target_format": "dict",
            "transformations": [
                {"type": "transform_value", "key": "key", "function": "trim"}
            ]
        }
        result = self.transformer.transform(data, transformation)
        assert result["key"] == "hello"

    def test_transform_nested(self):
        data = {"outer": {"inner": "value"}}
        transformation = {
            "source_format": "dict",
            "target_format": "dict",
            "transformations": [
                {
                    "type": "nested_transform",
                    "key": "outer",
                    "transformations": [
                        {"type": "rename_key", "old_key": "inner", "new_key": "renamed"}
                    ]
                }
            ]
        }
        result = self.transformer.transform(data, transformation)
        assert "renamed" in result["outer"]


class TestStructureTransformer:
    def setup_method(self):
        self.transformer = StructureTransformer()

    def test_flatten_simple_dict(self):
        data = {"a": 1, "b": 2}
        transformation = {"type": "flatten"}
        result = self.transformer.transform(data, transformation)
        assert result == {"a": 1, "b": 2}

    def test_flatten_nested_dict(self):
        data = {"a": {"b": 1, "c": 2}}
        transformation = {"type": "flatten"}
        result = self.transformer.transform(data, transformation)
        assert "a.b" in result
        assert result["a.b"] == 1

    def test_flatten_with_lists(self):
        data = {"items": [{"name": "a"}, {"name": "b"}]}
        transformation = {"type": "flatten"}
        result = self.transformer.transform(data, transformation)
        assert "items[0].name" in result

    def test_flatten_custom_separator(self):
        data = {"a": {"b": 1}}
        transformation = {"type": "flatten", "separator": "/"}
        result = self.transformer.transform(data, transformation)
        assert "a/b" in result

    def test_nest_simple_flat(self):
        data = {"a.b": 1, "a.c": 2}
        transformation = {"type": "nest"}
        result = self.transformer.transform(data, transformation)
        assert result["a"]["b"] == 1

    def test_nest_custom_separator(self):
        data = {"a/b": 1}
        transformation = {"type": "nest", "separator": "/"}
        result = self.transformer.transform(data, transformation)
        assert result["a"]["b"] == 1

    def test_nest_with_array_indices(self):
        data = {"items[0].name": "first", "items[1].name": "second"}
        transformation = {"type": "nest"}
        result = self.transformer.transform(data, transformation)
        assert result["items"][0]["name"] == "first"
        assert result["items"][1]["name"] == "second"

    def test_filter_dict_by_key_matches(self):
        data = {"keep_this": 1, "drop_that": 2}
        transformation = {
            "type": "filter",
            "condition": {"type": "key_matches", "pattern": "^keep_"}
        }
        result = self.transformer.transform(data, transformation)
        assert "keep_this" in result
        assert "drop_that" not in result

    def test_filter_dict_by_value_equals(self):
        data = {"a": 1, "b": 2, "c": 1}
        transformation = {
            "type": "filter",
            "condition": {"type": "value_equals", "value": 1}
        }
        result = self.transformer.transform(data, transformation)
        assert len(result) == 2
        assert result["a"] == 1
        assert result["c"] == 1

    def test_filter_dict_by_value_matches(self):
        data = {"email": "test@example.com", "name": "John"}
        transformation = {
            "type": "filter",
            "condition": {"type": "value_matches", "pattern": r".*@.*"}
        }
        result = self.transformer.transform(data, transformation)
        assert "email" in result
        assert "name" not in result

    def test_filter_dict_by_value_in(self):
        data = {"a": "x", "b": "y", "c": "x"}
        transformation = {
            "type": "filter",
            "condition": {"type": "value_in", "values": ["x"]}
        }
        result = self.transformer.transform(data, transformation)
        assert len(result) == 2

    def test_filter_list(self):
        data = [1, 2, 3, 4, 5]
        transformation = {
            "type": "filter",
            "condition": {"type": "value_equals", "value": 2}
        }
        result = self.transformer.transform(data, transformation)
        assert result == [2]

    def test_map_dict(self):
        data = {"a": 1, "b": 2}
        transformation = {
            "type": "map",
            "mapping": {"1": "one", "2": "two"}
        }
        result = self.transformer.transform(data, transformation)
        assert result["a"] == "one"
        assert result["b"] == "two"

    def test_can_transform_any(self):
        assert self.transformer.can_transform("any", "any")
        assert self.transformer.can_transform("json", "yaml")


class TestTransformer:
    def setup_method(self):
        self.transformer = Transformer()

    def test_transform_chooses_format_transformer(self):
        data = {"key": "value"}
        transformation = {
            "source_format": "dict",
            "target_format": "json"
        }
        result = self.transformer.transform(data, transformation)
        assert '"key"' in result

    def test_transform_chooses_structure_transformer(self):
        data = {"a": {"b": 1}}
        transformation = {"type": "flatten"}
        result = self.transformer.transform(data, transformation)
        assert "a.b" in result

    def test_transform_no_suitable_transformer(self):
        data = {"key": "value"}
        transformation = {"type": "unknown_type"}

        with pytest.raises(ValueError) as exc_info:
            self.transformer.transform(data, transformation)
        assert "Unknown transformation type" in str(exc_info.value)

    def test_register_custom_transformer(self):
        class CustomTransformer(DataTransformer):
            def transform(self, data, transformation):
                return "custom_result"

            def can_transform(self, source_format, target_format):
                return source_format == "custom" and target_format == "custom"

        custom = CustomTransformer()
        self.transformer.register_transformer(custom)

        assert len(self.transformer.transformers) == 3


class TestDataTransformerAbstract:
    def test_data_transformer_is_abstract(self):
        with pytest.raises(TypeError):
            DataTransformer()

    def test_data_transformer_abstract_methods(self):
        assert hasattr(DataTransformer, 'transform')
        assert hasattr(DataTransformer, 'can_transform')
