class RuntimeStateManager:
    """Maintains runtime cognitive state."""

    def __init__(self):
        self.state = {
            'active_agents': [],
            'cycles': 0
        }

    def register_agent(self, agent_name):
        self.state['active_agents'].append(agent_name)

    def increment_cycle(self):
        self.state['cycles'] += 1

    def get_state(self):
        return self.state
