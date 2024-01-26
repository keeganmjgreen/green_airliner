"""
Notes:
    Emulators are stateful.
"""

import dataclasses
import datetime as dt
from copy import deepcopy
from typing import Optional, Union


@dataclasses.dataclass(kw_only=True)
class BaseEmulator:
    START_TIMESTAMP: Union[dt.datetime, None] = None
    """If the ``START_TIMESTAMP`` is None, it may be automatically determined from the
    ``BaseEmulator`` subclass from its data.
    """
    END_TIMESTAMP: Optional[dt.datetime] = None
    """If the ``END_TIMESTAMP`` is None, there is no end timestamp."""

    current_timestamp: dt.datetime = dataclasses.field(init=False)

    def __post_init__(self):
        if self.END_TIMESTAMP is not None:
            assert self.END_TIMESTAMP >= self.START_TIMESTAMP
        self.current_timestamp = deepcopy(self.START_TIMESTAMP)
        self.current_state = deepcopy(self.START_STATE)

    def update_state(self, timestamp: dt.datetime) -> None:
        assert timestamp >= self.current_timestamp
        if self.END_TIMESTAMP is not None:
            assert timestamp < self.END_TIMESTAMP
        self.current_timestamp = timestamp
