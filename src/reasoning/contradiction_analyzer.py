class ContradictionAnalyzer:
    """Analyzes contradictions in reasoning chains."""

    def analyze(self, statements):
        contradictions = []

        for statement in statements:
            if 'not' in statement.lower():
                contradictions.append(statement)

        return contradictions
