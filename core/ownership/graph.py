import ast
from enum import Enum
from typing import List, Dict, Set, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from core.common.models import Diagnostic, Classification, Span, SourceLocation, ResourceState
from core.resources.state import AbstractStore
from core.resources.semantics import ResourceOwnership


class EdgeRelationship(str, Enum):
    OWNS = "OWNS"
    CREATES = "CREATES"
    DERIVES = "DERIVES"
    TRANSFERS = "TRANSFERS"
    ESCAPES = "ESCAPES"
    RELEASES = "RELEASES"
    DEPENDS_ON = "DEPENDS_ON"


class OwnershipNode(BaseModel):
    resource_id: str
    resource_type: str
    variable: str
    function: str = "global"
    acquisition_location: Optional[Dict[str, int]] = None
    release_location: Optional[Dict[str, int]] = None
    owner: str = "function"
    parent_id: Optional[str] = None
    state: str = "OPEN_MUST_CLOSE"
    escape: bool = False
    transfer: bool = False
    leak_status: str = "DEFINITE_LEAK"

    model_config = ConfigDict(arbitrary_types_allowed=True)


class OwnershipEdge(BaseModel):
    source_id: str
    target_id: str
    relationship: EdgeRelationship
    label: str = ""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ResourceOwnershipGraph(BaseModel):
    nodes: List[OwnershipNode] = Field(default_factory=list)
    edges: List[OwnershipEdge] = Field(default_factory=list)
    leak_paths: List[List[str]] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def from_diagnostic(cls, diagnostic: Diagnostic, source_code: str = "") -> "ResourceOwnershipGraph":
        """Constructs a serializable Resource Ownership Graph from a Diagnostic finding and AST semantics."""
        res_id = diagnostic.finding_id or "res_001"
        res_var = diagnostic.resource_variable or "handle"
        res_type = str(diagnostic.resource_type)
        func_name = getattr(diagnostic, "function_name", None) or "function"
        acq_line = diagnostic.location.start.line if diagnostic.location else 1

        rel_line = diagnostic.release_location.start.line if diagnostic.release_location else None

        # Build Owner Function Node
        func_node_id = f"func_{func_name}"
        func_node = OwnershipNode(
            resource_id=func_node_id,
            resource_type="FUNCTION_SCOPE",
            variable=func_name,
            function=func_name,
            owner="scope",
            state="ACTIVE",
            leak_status="SAFE",
        )

        # Build Target Resource Node
        res_node = OwnershipNode(
            resource_id=res_id,
            resource_type=res_type,
            variable=res_var,
            function=func_name,
            acquisition_location={"line": acq_line, "column": 1},
            release_location={"line": rel_line, "column": 1} if rel_line else None,
            owner=func_name,
            parent_id=None,
            state="OPEN_MUST_CLOSE" if diagnostic.classification != Classification.SAFE else "CLOSED",
            escape=False,
            transfer=False,
            leak_status=diagnostic.classification.value,
        )

        nodes = [func_node, res_node]
        edges = [
            OwnershipEdge(
                source_id=func_node_id,
                target_id=res_id,
                relationship=EdgeRelationship.CREATES,
                label=f"Acquires {res_var} at L{acq_line}",
            ),
            OwnershipEdge(
                source_id=func_node_id,
                target_id=res_id,
                relationship=EdgeRelationship.OWNS,
                label=f"Scope Ownership ({func_name})",
            ),
        ]

        # Check for derived parent-child resources (e.g. database conn -> cursor)
        if "cursor" in res_var.lower() or "cursor" in res_type.lower():
            parent_id = f"res_parent_{res_id}"
            parent_node = OwnershipNode(
                resource_id=parent_id,
                resource_type="DATABASE_CONNECTION",
                variable="conn",
                function=func_name,
                acquisition_location={"line": max(1, acq_line - 1), "column": 1},
                owner=func_name,
                state="OPEN_MUST_CLOSE",
                leak_status="SAFE",
            )
            nodes.append(parent_node)
            res_node.parent_id = parent_id

            edges.append(
                OwnershipEdge(
                    source_id=parent_id,
                    target_id=res_id,
                    relationship=EdgeRelationship.DERIVES,
                    label="Derives cursor from connection",
                )
            )
            edges.append(
                OwnershipEdge(
                    source_id=res_id,
                    target_id=parent_id,
                    relationship=EdgeRelationship.DEPENDS_ON,
                    label="Depends on active connection",
                )
            )

        leak_paths = []
        if diagnostic.classification != Classification.SAFE:
            leak_paths.append([func_node_id, res_id])

        return cls(nodes=nodes, edges=edges, leak_paths=leak_paths)
