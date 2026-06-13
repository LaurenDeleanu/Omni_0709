from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class WorkflowNode(BaseModel):
    id: str
    type: str = Field(..., description="e.g., 'llm', 'tool', 'condition', 'end'")
    data: Dict[str, Any] = Field(default_factory=dict)
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})

class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None
    condition: Optional[str] = None

class WorkflowGraph(BaseModel):
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    
class WorkflowValidationResponse(BaseModel):
    is_valid: bool
    errors: List[str]
    warnings: List[str]
