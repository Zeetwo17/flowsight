"""Canonical event stream consumed by detection.

Every disruption signal — synthetic, GDELT news, weather alert, traffic
slowdown — is mapped into this schema before the model sees it. The
detection layer never touches raw upstream data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Literal, Tuple, Union

EventTarget = Union[int, Tuple[int, int]]
EventKind = Literal["delay", "congestion", "closure", "weather", "demand_spike"]


@dataclass(frozen=True)
class Event:
    timestamp: float
    target: EventTarget
    kind: EventKind
    severity: float = 1.0
    source: str = "synthetic"
    metadata: dict = field(default_factory=dict)

    @property
    def is_node_event(self) -> bool:
        return isinstance(self.target, int)

    @property
    def is_edge_event(self) -> bool:
        return isinstance(self.target, tuple)

    @property
    def origin_node(self) -> int:
        """The node where the disruption originates (for edge events,
        the upstream endpoint)."""
        if self.is_node_event:
            return int(self.target)  # type: ignore[arg-type]
        return int(self.target[0])  # type: ignore[index]


class EventStream:
    """In-memory, time-ordered event store.

    For the cloud build we'll swap this for a Pub/Sub-backed
    implementation with the same interface — detection code is unchanged.
    """

    def __init__(self) -> None:
        self._events: List[Event] = []

    def push(self, event: Event) -> None:
        self._events.append(event)
        self._events.sort(key=lambda e: e.timestamp)

    def extend(self, events: List[Event]) -> None:
        self._events.extend(events)
        self._events.sort(key=lambda e: e.timestamp)

    def window(self, t_start: float, t_end: float) -> List[Event]:
        return [e for e in self._events if t_start <= e.timestamp < t_end]

    def all(self) -> List[Event]:
        return list(self._events)

    def __iter__(self) -> Iterator[Event]:
        return iter(self._events)

    def __len__(self) -> int:
        return len(self._events)
