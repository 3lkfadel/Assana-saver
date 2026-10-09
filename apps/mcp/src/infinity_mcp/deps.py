"""What the tools need, injectable in tests: settings, the network transport and the clock."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

import httpx

from .api import InfinityAPI
from .auth import current_token
from .config import Settings


@dataclass
class Deps:
    settings: Settings
    transport: httpx.AsyncBaseTransport | None = None
    clock: Callable[[], date] = field(default=date.today)

    def api(self) -> InfinityAPI:
        """An API client authenticated as the person calling the tool."""
        return InfinityAPI(self.settings, current_token(self.settings), self.transport)

    def today(self) -> date:
        return self.clock()
