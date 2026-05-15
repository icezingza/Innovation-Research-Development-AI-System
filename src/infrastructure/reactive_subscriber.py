from abc import ABC, abstractmethod

from src.infrastructure.event_bus import RuntimeEvent, RuntimeEventBus


class ReactiveSubscriber(ABC):
    """Base class for infrastructure components that react to EventBus events.

    Unlike cognitive agents (perceive/reason/act), reactive subscribers are
    infrastructure-level components that respond to bus events autonomously.
    They register their handlers once and operate without direct invocation.
    """

    @abstractmethod
    def register(self, bus: RuntimeEventBus) -> None:
        """Subscribe to relevant topics on the event bus."""
        ...

    @abstractmethod
    async def handle_event(self, event: RuntimeEvent) -> None:
        """Process an incoming event."""
        ...
