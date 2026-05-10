class BaseAgent:
    """Base abstraction for cognitive agents."""

    async def perceive(self, context):
        return context

    async def reason(self):
        return None

    async def act(self):
        return None
