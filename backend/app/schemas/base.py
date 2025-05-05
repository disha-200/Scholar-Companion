from pydantic import BaseModel

def to_camel(s: str) -> str:
    """snake_case → camelCase"""
    parts = s.split("_")
    return parts[0] + "".join(w.title() for w in parts[1:])

class CamelModel(BaseModel):
    """
    • Lets you use snake_case in Python code  
    • Still emits/accepts camelCase in JSON
    """
    model_config = {
        "populate_by_name": True,   # accept both snake & camel on input
        "alias_generator": to_camel
    }
