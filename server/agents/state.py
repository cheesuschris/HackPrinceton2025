from typing import Annotated, Sequence, TypedDict, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class CarbonState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    product_brand: str
    product_name: str
    carbon_input: Dict[str, Any]
    search_attempts: int
    complete: bool



