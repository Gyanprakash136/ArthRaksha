"""
ArthRaksha — Event Bus
=========================
Implements IEventBus.
Decoupled event pub/sub system for routing DomainEvents to handlers.
"""
import logging
from typing import Callable
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from interfaces import IEventBus, DomainEvent, EventType

logger = logging.getLogger(__name__)

class EventBus(IEventBus):
    """
    In-memory synchronous event bus.
    For production, this would be replaced with Kafka/RabbitMQ/Redis PubSub.
    """
    def __init__(self):
        self._subscribers: dict[EventType, list[Callable]] = {
            event_type: [] for event_type in EventType
        }

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__name__} to {event_type.value}")

    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers synchronously."""
        logger.info(f"[EVENT BUS] Publishing {event.event_type.value} ({event.event_id}) from {event.source}")
        
        handlers = self._subscribers.get(event.event_type, [])
        if not handlers:
            logger.debug(f"No handlers registered for {event.event_type.value}")
            return
            
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__} for event {event.event_id}: {e}", exc_info=True)

# Global singleton for easy import
event_bus = EventBus()
