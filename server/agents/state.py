from typing import TypedDict, Optional, List, Literal

class ProductCO2State(TypedDict):
    product_name: str                     
    product_url: Optional[str]            
    raw_description: Optional[str]        
    materials: Optional[List[str]]        
    weight_kg: Optional[float]           
    manufacturing_location: Optional[str] 
    shipping_distance_km: Optional[float] 
    packaging_type: Optional[str]
    co2_score: Optional[float]
    data_sources: List[str]             
    missing_fields: List[str]             
    stage: Literal[
        "init",          
        "fetching",     
        "ready_to_calculate", 
        "calculating", 
        "done"
    ]
    error: Optional[str]                  
