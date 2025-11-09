from state import ProductCO2State

def update_state_from_product_data(state: ProductCO2State, product_data: dict) -> ProductCO2State:
    state["product_name"] = product_data.get("name") or state.get("product_name") or None
    state["product_url"] = product_data.get("url") or state.get("product_url") or None
    state["raw_description"] = product_data.get("description") or state.get("raw_description") or None
    state["materials"] = product_data.get("materials") or state.get("materials") or None
    state["weight_kg"] = product_data.get("weight") or state.get("weight_kg") or None
    state["manufacturing_location"] = (
        product_data.get("shippingFrom")
        or product_data.get("shipper")
        or product_data.get("manufacturing_location")
        or state.get("manufacturing_location")
        or None
    )
    state["packaging_type"] = product_data.get("packaging") or state.get("packaging_type") or None
    state["brand"] = product_data.get("brand") or state.get("brand") or None
    state["price"] = product_data.get("price") or None
    state["rating"] = product_data.get("rating") or None
    state["availability"] = product_data.get("availability") or None
    state["seller"] = product_data.get("seller") or None
    state["platform"] = product_data.get("platform") or None
    state["image"] = product_data.get("image") or None
    state["reviews"] = product_data.get("reviews") or []
    if state.get("data_sources") is None:
        state["data_sources"] = []
    if url := product_data.get("url"):
        if url not in state["data_sources"]:
            state["data_sources"].append(url)
    required = ["materials", "weight_kg", "manufacturing_location"]
    state["missing_fields"] = [f for f in required if state.get(f) in (None, [], "")]
    state["stage"] = "ready_to_calculate" if not state["missing_fields"] else "fetching"
    return state


if __name__ == "__main__":
    initial_state: ProductCO2State = {
        "product_name": None,
        "product_url": None,
        "raw_description": None,
        "materials": None,
        "weight_kg": None,
        "manufacturing_location": None,
        "packaging_type": None,
        "brand": None,
        "price": None,
        "rating": None,
        "availability": None,
        "seller": None,
        "platform": None,
        "image": None,
        "reviews": [],
        "data_sources": [],
        "missing_fields": [],
        "stage": "init",
        "error": None
    }

    productData = {
        "platform": "Amazon",
        "url": "https://www.amazon.com/Sweetcrispy-Ergonomic-Adjustable-Mid-Back-Computer/dp/B0FGY4KVCV/",
        "image": None,
        "name": "Sweetcrispy Ergonomic Office Desk Chair Mesh Adjustable Swivel Mid-Back Computer Chair with Lumbar Support",
        "price": 56.92,
        "rating": None,
        "shipper": None,
        "seller": None,
        "reviews": [],
        "shippingFrom": None,
        "availability": None,
        "brand": "Sweetcrispy"
    }

    updated_state = update_state_from_product_data(initial_state, productData)
    print(updated_state)