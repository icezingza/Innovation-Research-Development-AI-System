import asyncio


class ExecutionLoop:
    """Heartbeat loop for cognitive runtime execution."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.running = False

    async def start(self, context):
        self.running = True

        while self.running:
            await self.runtime.execute_cycle(context)
            await asyncio.sleep(1)

    async def stop(self):
        self.running = False
