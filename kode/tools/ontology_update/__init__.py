"""
Ontology Update Module

提供本体增量更新和反思功能。
"""

from .impact_graph import ChangeImpactGraph
from .update_manager import OntologyUpdateManager
from .update_tool import OntologyUpdateTool
from .reflect_tool import OntologyReflectTool

__all__ = [
    "ChangeImpactGraph",
    "OntologyUpdateManager",
    "OntologyUpdateTool",
    "OntologyReflectTool",
]
