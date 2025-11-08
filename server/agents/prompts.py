"""Prompts for the research agent."""


def system_prompt(product_brand: str, product_name: str, search_history: list) -> str:
    """Generate system prompt for the research agent."""
    searches_count = len(search_history)
    
    prompt = f"""You are researching: {product_brand} {product_name}

    Goal: Figure out how good this product is environmentally and ethically.

    What to research:
    - Carbon footprint and CO2 emissions
    - Manufacturing location
    - Materials and environmental impact
    - Brand sustainability reputation
    - Environmental controversies
    - Shipping methods

    You can search for information. Make ONE specific search at a time.
    After each search, analyze what you found and decide if you need more information.

    Searches made: {searches_count}/5
    """
    return prompt

