from abc import ABC, abstractmethod
from typing import Any


class Command(ABC):
    name: str = ""
    help: str = ""

    def __init__(self, registry_core: Any):
        self.core = registry_core
        self.verbose = registry_core.verbose

    @abstractmethod
    def execute(self, args: Any) -> None:
        pass

    @classmethod
    def add_parser(cls, subparsers: Any) -> Any:
        parser = subparsers.add_parser(cls.name, help=cls.help)
        cls._add_arguments(parser)
        return parser

    @classmethod
    def _add_arguments(cls, parser: Any) -> None:
        pass
