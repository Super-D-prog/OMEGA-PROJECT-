"""Permission boundary for future robots, smart-home devices, and sensors."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class Risk(str, Enum):
    READ_ONLY = "read_only"
    REVERSIBLE = "reversible"
    CONSEQUENTIAL = "consequential"
    PROHIBITED = "prohibited"


@dataclass(frozen=True)
class ActionRequest:
    adapter: str
    action: str
    target: str
    risk: Risk
    parameters: dict[str, object]


class DeviceAdapter(Protocol):
    name: str

    def execute(self, request: ActionRequest) -> str:
        ...


class IntegrationHub:
    """Routes explicitly approved actions; unknown adapters are denied."""

    def __init__(self) -> None:
        self._adapters: dict[str, DeviceAdapter] = {}

    def register(self, adapter: DeviceAdapter) -> None:
        if adapter.name in self._adapters:
            raise ValueError(f"Adapter already registered: {adapter.name}")
        self._adapters[adapter.name] = adapter

    def execute(self, request: ActionRequest, confirmed: bool = False) -> str:
        if request.risk is Risk.PROHIBITED:
            raise PermissionError("This action is prohibited.")
        if request.risk is Risk.CONSEQUENTIAL and not confirmed:
            raise PermissionError("Explicit user confirmation is required.")
        adapter = self._adapters.get(request.adapter)
        if adapter is None:
            raise LookupError(f"No approved adapter named {request.adapter!r}.")
        return adapter.execute(request)
