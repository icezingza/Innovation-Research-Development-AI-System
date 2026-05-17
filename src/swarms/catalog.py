from pathlib import Path
from typing import Dict, List, Optional
import yaml


class SwarmTemplate:
    def __init__(self, id: str, data: dict):
        self.id = id
        self.name = data["name"]
        self.domain = data["domain"]
        self.system_prompt = data.get("system_prompt", "")
        self.recommended_agents = data.get("agents", [])
        self.knowledge_graph_seed = data.get("kg_seed", {})
        self.description = data.get("description", "")
        self.default_chain = data.get("chain", "default")
        self.regulatory_tags: list = data.get("regulatory_tags", [])


class SwarmCatalog:
    def __init__(self, catalog_path: str = None):
        if catalog_path is None:
            catalog_path = Path(__file__).parent / "templates"
        self.catalog_path = Path(catalog_path)
        self.templates: Dict[str, SwarmTemplate] = {}
        self._load_all()

    def _load_all(self):
        for yaml_file in self.catalog_path.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and "id" in data:
                    tmpl = SwarmTemplate(data["id"], data)
                    self.templates[tmpl.id] = tmpl

    def list(self) -> List[SwarmTemplate]:
        return list(self.templates.values())

    def get(self, template_id: str) -> Optional[SwarmTemplate]:
        return self.templates.get(template_id)


_catalog = None


def get_swarm_catalog() -> SwarmCatalog:
    global _catalog
    if _catalog is None:
        _catalog = SwarmCatalog()
    return _catalog
