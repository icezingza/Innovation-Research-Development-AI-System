class EventBus:
    """Simple event-driven infrastructure layer."""

    def __init__(self):
        self.subscribers = {}

    def subscribe(self, topic, callback):
        if topic not in self.subscribers:
            self.subscribers[topic] = []

        self.subscribers[topic].append(callback)

    async def publish(self, topic, event):
        callbacks = self.subscribers.get(topic, [])

        for callback in callbacks:
            await callback(event)
