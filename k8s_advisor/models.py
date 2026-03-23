from dataclasses import dataclass
from typing import Literal

Severity = Literal["CRITICAL", "WARNING", "INFO"]


@dataclass
class Finding:
    severity: Severity
    resource_type: str
    resource_name: str
    namespace: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.resource_type}/{self.resource_name} ({self.namespace}) - {self.message}"
