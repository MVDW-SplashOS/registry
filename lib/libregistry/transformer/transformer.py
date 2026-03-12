import json
import logging
import yaml
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DataTransformer(ABC):
    """Abstract base class for data transformers"""

    @abstractmethod
    def transform(self, data: Any, transformation: Dict[str, Any]) -> Any:
        """Transform data according to transformation rules"""
        pass

    @abstractmethod
    def can_transform(self, source_format: str, target_format: str) -> bool:
        """Check if this transformer can handle the given format conversion"""
        pass


class FormatTransformer(DataTransformer):
    """Transformer for format conversions (JSON, YAML, etc.)"""

    def transform(self, data: Any, transformation: Dict[str, Any]) -> Any:
        """Transform data between different formats"""
        source_format = transformation.get("source_format", "auto")
        target_format = transformation.get("target_format")

        if not target_format:
            raise ValueError("Target format must be specified")

        # Auto-detect source format if not specified
        if source_format == "auto":
            source_format = self._detect_format(data)

        # Convert to intermediate representation (dict)
        if source_format == "json":
            if isinstance(data, str):
                intermediate = json.loads(data)
            else:
                intermediate = data
        elif source_format == "yaml":
            if isinstance(data, str):
                intermediate = yaml.safe_load(data)
            else:
                intermediate = data
        elif source_format == "dict":
            intermediate = data
        else:
            raise ValueError(f"Unsupported source format: {source_format}")

        # Apply any data transformations
        if "transformations" in transformation:
            intermediate = self._apply_data_transformations(
                intermediate, transformation["transformations"]
            )

        # Convert to target format
        if target_format == "json":
            indent = transformation.get("indent", 2)
            return json.dumps(intermediate, indent=indent, ensure_ascii=False)
        elif target_format == "yaml":
            return yaml.dump(intermediate, default_flow_style=False)
        elif target_format == "dict":
            return intermediate
        else:
            raise ValueError(f"Unsupported target format: {target_format}")

    def can_transform(self, source_format: str, target_format: str) -> bool:
        """Check if this transformer can handle the format conversion"""
        supported_formats = {"json", "yaml", "dict"}
        return source_format in supported_formats and target_format in supported_formats

    def _detect_format(self, data: Any) -> str:
        """Auto-detect the format of the input data"""
        if isinstance(data, dict):
            return "dict"
        elif isinstance(data, str):
            try:
                json.loads(data)
                return "json"
            except json.JSONDecodeError:
                try:
                    yaml.safe_load(data)
                    return "yaml"
                except yaml.YAMLError:
                    return "string"
        return "unknown"

    def _apply_data_transformations(
        self, data: Dict[str, Any], transformations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply data transformation rules"""
        result = data.copy()

        for transform in transformations:
            transform_type = transform.get("type")

            if transform_type == "rename_key":
                old_key = transform["old_key"]
                new_key = transform["new_key"]
                if old_key in result:
                    result[new_key] = result.pop(old_key)

            elif transform_type == "delete_key":
                key = transform["key"]
                if key in result:
                    del result[key]

            elif transform_type == "add_key":
                key = transform["key"]
                value = transform["value"]
                result[key] = value

            elif transform_type == "transform_value":
                key = transform["key"]
                if key in result:
                    transform_func = self._get_transform_function(transform["function"])
                    result[key] = transform_func(result[key])

            elif transform_type == "nested_transform":
                key = transform["key"]
                if key in result and isinstance(result[key], dict):
                    result[key] = self._apply_data_transformations(
                        result[key], transform["transformations"]
                    )

        return result

    def _get_transform_function(self, function_name: str) -> Callable[[Any], Any]:
        """Get transformation function by name"""
        functions = {
            "to_lower": lambda x: x.lower() if isinstance(x, str) else x,
            "to_upper": lambda x: x.upper() if isinstance(x, str) else x,
            "to_int": lambda x: int(x) if str(x).isdigit() else x,
            "to_float": lambda x: float(x) if self._is_float(x) else x,
            "to_boolean": lambda x: str(x).lower() in ["true", "yes", "1", "on"],
            "trim": lambda x: x.strip() if isinstance(x, str) else x,
        }

        return functions.get(function_name, lambda x: x)

    def _is_float(self, value: Any) -> bool:
        """Check if value can be converted to float"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False


class StructureTransformer(DataTransformer):
    """Transformer for structural changes (flattening, nesting, etc.)"""

    def transform(self, data: Any, transformation: Dict[str, Any]) -> Any:
        """Transform data structure"""
        transform_type = transformation.get("type")

        if transform_type == "flatten":
            return self._flatten(data, transformation)
        elif transform_type == "nest":
            return self._nest(data, transformation)
        elif transform_type == "filter":
            return self._filter(data, transformation)
        elif transform_type == "map":
            return self._map(data, transformation)
        else:
            raise ValueError(f"Unknown transformation type: {transform_type}")

    def can_transform(self, source_format: str, target_format: str) -> bool:
        """Structure transformer works with any dict/list data"""
        return True

    def _flatten(
        self, data: Dict[str, Any], transformation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Flatten nested dictionary structure"""
        separator = transformation.get("separator", ".")
        result = {}

        def _flatten_recursive(current_dict, current_key=""):
            for key, value in current_dict.items():
                new_key = f"{current_key}{separator}{key}" if current_key else key

                if isinstance(value, dict):
                    _flatten_recursive(value, new_key)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            _flatten_recursive(item, f"{new_key}[{i}]")
                        else:
                            result[f"{new_key}[{i}]"] = item
                else:
                    result[new_key] = value

        _flatten_recursive(data)
        return result

    def _nest(
        self, data: Dict[str, Any], transformation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create nested structure from flat dictionary"""
        separator = transformation.get("separator", ".")
        result = {}

        for flat_key, value in data.items():
            keys = flat_key.split(separator)
            current_dict = result

            for i, key in enumerate(keys[:-1]):
                # Handle array indices
                if "[" in key and "]" in key:
                    base_key = key.split("[")[0]
                    index = int(key.split("[")[1].split("]")[0])

                    if base_key not in current_dict:
                        current_dict[base_key] = []

                    # Ensure list is large enough
                    while len(current_dict[base_key]) <= index:
                        current_dict[base_key].append({})

                    current_dict = current_dict[base_key][index]
                else:
                    if key not in current_dict:
                        current_dict[key] = {}
                    current_dict = current_dict[key]

            last_key = keys[-1]
            # Handle array indices in last key
            if "[" in last_key and "]" in last_key:
                base_key = last_key.split("[")[0]
                index = int(last_key.split("[")[1].split("]")[0])

                if base_key not in current_dict:
                    current_dict[base_key] = []

                # Ensure list is large enough
                while len(current_dict[base_key]) <= index:
                    current_dict[base_key].append(None)

                current_dict[base_key][index] = value
            else:
                current_dict[last_key] = value

        return result

    def _filter(self, data: Any, transformation: Dict[str, Any]) -> Any:
        """Filter data based on conditions"""
        if isinstance(data, dict):
            return self._filter_dict(data, transformation)
        elif isinstance(data, list):
            return self._filter_list(data, transformation)
        else:
            return data

    def _filter_dict(
        self, data: Dict[str, Any], transformation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Filter dictionary based on conditions"""
        condition = transformation.get("condition")
        if not condition:
            return data

        result = {}
        for key, value in data.items():
            if self._evaluate_condition(key, value, condition):
                result[key] = value

        return result

    def _filter_list(
        self, data: List[Any], transformation: Dict[str, Any]
    ) -> List[Any]:
        """Filter list based on conditions"""
        condition = transformation.get("condition")
        if not condition:
            return data

        return [
            item for item in data if self._evaluate_condition(None, item, condition)
        ]

    def _map(self, data: Any, transformation: Dict[str, Any]) -> Any:
        """Apply mapping function to data"""
        if isinstance(data, dict):
            return {k: self._map(v, transformation) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._map(item, transformation) for item in data]
        else:
            mapping = transformation.get("mapping", {})
            return mapping.get(str(data), data)

    def _evaluate_condition(
        self, key: Optional[str], value: Any, condition: Dict[str, Any]
    ) -> bool:
        """Evaluate a condition against key/value"""
        condition_type = condition.get("type")

        if condition_type == "key_matches":
            pattern = condition["pattern"]
            import re

            return bool(re.match(pattern, key or ""))

        elif condition_type == "value_equals":
            return value == condition["value"]

        elif condition_type == "value_matches":
            pattern = condition["pattern"]
            import re

            return bool(re.match(pattern, str(value)))

        elif condition_type == "value_in":
            return value in condition["values"]

        elif condition_type == "custom":
            # Custom condition function
            func = condition.get("function")
            if func:
                return func(key, value)

        return True


class Transformer:
    """Main transformer class that coordinates all transformations"""

    def __init__(self):
        self.transformers: List[DataTransformer] = [
            FormatTransformer(),
            StructureTransformer(),
        ]

    def transform(self, data: Any, transformation: Dict[str, Any]) -> Any:
        """Apply transformation to data"""
        # Find appropriate transformer
        transformer = self._find_transformer(transformation)
        if not transformer:
            raise ValueError(
                "No suitable transformer found for the specified transformation"
            )

        return transformer.transform(data, transformation)

    def _find_transformer(
        self, transformation: Dict[str, Any]
    ) -> Optional[DataTransformer]:
        """Find a transformer that can handle the given transformation"""
        for transformer in self.transformers:
            source_format = transformation.get("source_format", "auto")
            target_format = transformation.get("target_format", "auto")

            if transformer.can_transform(source_format, target_format):
                return transformer

        return None

    def register_transformer(self, transformer: DataTransformer):
        """Register a custom transformer"""
        self.transformers.append(transformer)


_default_transformer: Optional[Transformer] = None


def get_transformer() -> Transformer:
    """Get the global transformer instance (factory method for testability)."""
    global _default_transformer
    if _default_transformer is None:
        _default_transformer = Transformer()
    return _default_transformer


def set_transformer(transformer_instance: Transformer) -> None:
    """Set a custom transformer instance (useful for testing)."""
    global _default_transformer
    _default_transformer = transformer_instance


def reset_transformer() -> None:
    """Reset the transformer to create a new instance on next get_transformer() call."""
    global _default_transformer
    _default_transformer = None


class _DefaultTransformerProxy:
    """Proxy to maintain backward compatibility with global transformer usage."""
    def __getattr__(self, name: str):
        return getattr(get_transformer(), name)


transformer = _DefaultTransformerProxy()
