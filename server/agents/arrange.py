from typing import Any, Dict, List, Optional
import json
import re
import logging
from pathlib import Path

from server.services.llm import call_llm

CATEGORIES_PATH = Path("server/configs/categories.json")


def _load_flat_categories(path: Path = CATEGORIES_PATH) -> List[str]:
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
        flat = []
        for arr in data.values():
            if isinstance(arr, list):
                flat.extend(arr)
        return flat
    except Exception:
        logging.exception("Failed to load categories.json")
        return []


def _tokenize(s: Optional[str]) -> List[str]:
    if not s:
        return []
    s2 = s.lower().replace("_", " ").replace("-", " ")
    tokens = re.findall(r"[a-z0-9]+", s2)
    return tokens


def _fallback_match_category(product_json: Dict[str, Any], transformed: Dict[str, Any], categories: List[str]) -> Optional[str]:
    """
    Simple token-based fallback matching if LLM fails.
    """
    name = product_json.get("name") or ""
    brand = product_json.get("brand") or ""
    orig_cat = product_json.get("category") or ""
    search_text = " ".join([name, brand, str(orig_cat)]).lower()
    source_tokens = _tokenize(search_text)

    material_tokens = []
    for m in (transformed.get("materials") or []):
        if isinstance(m, dict) and m.get("name"):
            material_tokens.extend(_tokenize(m.get("name")))

    candidates = []
    for cat in categories:
        cat_tokens = [t for t in _tokenize(cat) if t not in ("and", "the", "of")]
        if not cat_tokens:
            continue
        if all((t in source_tokens) or (t in material_tokens) for t in cat_tokens):
            candidates.append((cat, len(cat_tokens)))
    if candidates:
        candidates.sort(key=lambda x: -x[1])
        return candidates[0][0]

    # partial
    for cat in categories:
        cat_tokens = [t for t in _tokenize(cat) if t not in ("and", "the", "of")]
        if any(t in source_tokens or t in material_tokens for t in cat_tokens):
            return cat
    return None


def _construct_category_prompt(product_json: Dict[str, Any], transformed: Dict[str, Any], categories: List[str]) -> str:
    """
    Build a prompt asking the LLM to choose exactly one of the provided categories (or null)
    and provide chain-of-thought reasoning in plain text. Ask to output a single JSON object only.
    """
    product_summary = {
        "name": product_json.get("name"),
        "brand": product_json.get("brand"),
        "original_category": product_json.get("category"),
        "short_description": product_json.get("short_description") or product_json.get("description"),
        "materials": [
            {"name": m.get("name"), "weight": m.get("weight"), "weight_source": m.get("weight_source")}
            for m in (transformed.get("materials") or [])
        ],
    }
    categories_list_text = ", ".join(categories)
    prompt = f"""
You are given a product and a fixed set of EXACT category names (these are canonical labels).
Choose exactly ONE of the provided category names that best fits the product, or return null if none apply.

Categories (choose one of these exact strings): [{categories_list_text}]

Product (JSON):
{json.dumps(product_summary, ensure_ascii=False)}

Output requirement (READ CAREFULLY):
1) Output ONLY a single JSON object (no other text). The JSON must have two keys:
   - "category": one of the exact category strings above OR null
   - "reasoning": a plaintext string containing your chain-of-thought style step-by-step reasoning about
                  why you chose that category. This should be human-readable plaintext and can contain
                  uncertainty statements, token matches, and references to material names. Include explicit
                  notes if you're unsure and why.
2) The "category" field must be exactly one of the category strings (match case and underscores), or null.
3) Keep the "reasoning" as plain text (not markdown). Full chain-of-thought is requested and should be included.

Return only the JSON object. Example (for format only — do NOT emulate content):
{{"category":"tshirts","reasoning":"I saw 'tee' in the title, material cotton, ..."}}
"""
    return prompt.strip()


def _extract_first_json_block(text: str) -> Optional[str]:
    if not text:
        return None
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, flags=re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None


def _safe_load_json(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        pass
    block = _extract_first_json_block(text)
    if block:
        try:
            return json.loads(block)
        except Exception:
            pass
    # very brittle single->double quote
    if "'" in text and '"' not in text:
        try:
            fixed = text.replace("'", '"')
            return json.loads(fixed)
        except Exception:
            pass
    raise ValueError("Unable to parse JSON from LLM output.")


def _parse_price(price_val: Any) -> Optional[float]:
    if price_val is None:
        return None
    if isinstance(price_val, (int, float)):
        return float(price_val)
    s = str(price_val)
    m = re.search(r"(\d+(?:[.,]\d{1,2})?)", s.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None


def _build_carbon_cot(transformed: Dict[str, Any], carbon_result: Dict[str, Any]) -> str:
    """
    Build a plaintext chain-of-thought that shows explicit calculations for the CF breakdown,
    citing the numeric inputs and sources.
    """
    lines: List[str] = []
    lines.append("Carbon calculation chain-of-thought and step-by-step math:")
    mats = transformed.get("materials") or []
    mat_total = 0.0
    lines.append("1) Material emissions:")
    if mats:
        for i, m in enumerate(mats):
            name = m.get("name") or "UNKNOWN"
            w = m.get("weight")
            ef = m.get("emission_factor")
            w_src = m.get("weight_source")
            ef_src = m.get("emission_factor_source")
            if w is None or ef is None:
                lines.append(f" - #{i+1} {name}: missing weight or emission factor -> contribution unknown (weight={w}, ef={ef}) (sources: {w_src}; {ef_src})")
                continue
            contrib = float(w) * float(ef)
            mat_total += contrib
            lines.append(f" - #{i+1} {name}: weight={w} kg (source={w_src}), ef={ef} kgCO2e/kg (source={ef_src}) -> {w} * {ef} = {contrib:.4f} kgCO2e")
    else:
        lines.append(" - No materials provided (treated as null).")

    # manufacturing
    mf = transformed.get("manufacturing_factor") or {}
    mf_value = mf.get("value")
    mf_src = mf.get("source")
    if mf_value is None:
        manuf_contrib = None
        lines.append("2) Manufacturing: manufacturing factor missing -> contribution unknown")
    else:
        manuf_contrib = mat_total * float(mf_value)
        lines.append(f"2) Manufacturing: manufacturing factor={mf_value} (source={mf_src}) -> manufacturing = material_total({mat_total:.4f}) * {mf_value} = {manuf_contrib:.4f} kgCO2e")

    # transport
    tr = transformed.get("transport") or {}
    pw = transformed.get("product_weight") or {}
    pw_val = pw.get("value")
    tr_dist = tr.get("distance_km")
    tr_ef = tr.get("emission_factor_ton_km")
    tr_src = tr.get("source")
    if pw_val is None or tr_dist is None or tr_ef is None:
        tr_contrib = None
        lines.append("3) Transport: missing product_weight/distance/emission_factor -> contribution unknown")
        lines.append(f"   provided product_weight={pw_val} (source={pw.get('source')}), distance_km={tr_dist}, ef_ton_km={tr_ef} (source={tr_src})")
    else:
        # transport formula in carbon_calc: product_weight(kg) * distance_km * ef_ton_km / 1000
        tr_contrib = float(pw_val) * float(tr_dist) * float(tr_ef) / 1000.0
        lines.append(f"3) Transport: product_weight={pw_val} kg (source={pw.get('source')}), distance={tr_dist} km, ef={tr_ef} kgCO2e per ton-km (source={tr_src})")
        lines.append(f"   -> transport = {pw_val} * {tr_dist} * {tr_ef} / 1000 = {tr_contrib:.4f} kgCO2e")

    # packaging
    pk = transformed.get("packaging") or {}
    pk_w = pk.get("weight")
    pk_ef = pk.get("emission_factor")
    pk_src = pk.get("source")
    if pk_w is None or pk_ef is None:
        pk_contrib = None
        lines.append("4) Packaging: missing weight or emission factor -> contribution unknown")
    else:
        pk_contrib = float(pk_w) * float(pk_ef)
        lines.append(f"4) Packaging: weight={pk_w} kg (source={pk_src}), ef={pk_ef} kgCO2e/kg -> {pk_w} * {pk_ef} = {pk_contrib:.4f} kgCO2e")

    # Summation and compare to carbon_result
    lines.append("5) Summation of components (computed here):")
    comp_vals = []
    comp_names = []
    if mats:
        lines.append(f" - material_total (sum of materials, computed) = {mat_total:.4f} kgCO2e")
        comp_vals.append(mat_total); comp_names.append("material")
    if manuf_contrib is not None:
        lines.append(f" - manufacturing = {manuf_contrib:.4f} kgCO2e")
        comp_vals.append(manuf_contrib); comp_names.append("manufacturing")
    if tr_contrib is not None:
        lines.append(f" - transport = {tr_contrib:.4f} kgCO2e")
        comp_vals.append(tr_contrib); comp_names.append("transport")
    if pk_contrib is not None:
        lines.append(f" - packaging = {pk_contrib:.4f} kgCO2e")
        comp_vals.append(pk_contrib); comp_names.append("packaging")

    computed_sum = sum(comp_vals) if comp_vals else None
    if computed_sum is not None:
        lines.append(f" -> computed_total = sum({', '.join(comp_names)}) = {computed_sum:.4f} kgCO2e")
    else:
        lines.append(" -> computed_total = unknown (components missing)")

    # Compare to provided carbon_result
    cr_total = carbon_result.get("cf_total")
    cr_break = carbon_result.get("breakdown") or {}
    lines.append("6) Carbon result provided by carbon_calc (for cross-check):")
    lines.append(f"  - cf_total: {cr_total}")
    for k, v in cr_break.items():
        lines.append(f"  - {k}: {v}")

    if computed_sum is not None and cr_total is not None:
        diff = cr_total - computed_sum
        lines.append(f"7) Difference between computed_total and provided cf_total: {diff:.4f} kgCO2e")
        if abs(diff) > max(0.01, 0.01 * max(abs(cr_total), 1.0)):
            lines.append(" - NOTE: difference is non-trivial; check inputs sources or rounding assumptions.")
        else:
            lines.append(" - Difference within small rounding tolerance.")
    else:
        lines.append("7) Cannot compute difference due to missing values.")

    return "\n".join(lines)


def arrange_product(product_json: Dict[str, Any],
                    transformed: Dict[str, Any],
                    carbon_result: Dict[str, Any],
                    model: Optional[str] = "gemini-2.5-flash-lite",
                    temperature: float = 0.0,
                    max_tokens: int = 512) -> Dict[str, Any]:
    """
    Use LLM to choose one of the canonical categories and produce cf_detail containing:
      - LLM category reasoning (chain-of-thought plaintext)
      - Deterministic carbon calculation chain-of-thought (plaintext)
    Return dict suitable for database.insert_product(...)
    """
    categories = _load_flat_categories(CATEGORIES_PATH)
    category_choice = None
    llm_reasoning = None

    if categories:
        prompt = _construct_category_prompt(product_json, transformed, categories)
        try:
            raw = call_llm(prompt, model=model, temperature=temperature, max_tokens=max_tokens)
            parsed = _safe_load_json(raw)
            if isinstance(parsed, dict):
                cat = parsed.get("category")
                reasoning = parsed.get("reasoning")
                if cat in categories:
                    category_choice = cat
                else:
                    # allow explicit null
                    if cat is None:
                        category_choice = None
                    else:
                        # Not an exact match -> fallback to None
                        category_choice = None
                llm_reasoning = reasoning if isinstance(reasoning, str) else None
        except Exception:
            logging.exception("LLM category classification failed - will fallback to heuristic.")
            category_choice = None

    if category_choice is None:
        category_choice = _fallback_match_category(product_json, transformed, categories)

    # Build cf_detail: include LLM reasoning (if any) then deterministic carbon COT
    parts: List[str] = []
    parts.append("=== Category decision (LLM) ===")
    if llm_reasoning:
        parts.append(llm_reasoning)
    else:
        parts.append("LLM reasoning not available or not parsed. Used fallback heuristic.")
        # if fallback produced a match, explain simple token-based match
        if category_choice:
            parts.append(f"Fallback heuristic chose category '{category_choice}' based on token matching from product name/brand/materials.")
        else:
            parts.append("Fallback heuristic could not find a match; category set to null.")

    parts.append("\n=== Deterministic carbon calculation chain-of-thought ===")
    parts.append(_build_carbon_cot(transformed, carbon_result))

    cf_detail_text = "\n".join(parts)

    sku = product_json.get("sku") or product_json.get("id") or None
    name = product_json.get("name") or transformed.get("product_name") or None
    brand = product_json.get("brand") or None
    price = _parse_price(product_json.get("price"))
    web_url = product_json.get("url") or product_json.get("web_url") or None
    image_url = product_json.get("image") or product_json.get("image_url") or None

    cf_value = carbon_result.get("cf_total")
    if cf_value is None:
        breakdown = carbon_result.get("breakdown") or {}
        try:
            cf_value = sum(float(v) for v in breakdown.values() if v is not None)
        except Exception:
            cf_value = None

    out = {
        "sku": sku,
        "name": name,
        "category": category_choice,
        "brand": brand,
        "price": price,
        "web_url": web_url,
        "image_url": image_url,
        "cf_value": float(cf_value) if cf_value is not None else None,
        "cf_detail": cf_detail_text,
    }
    return out


if __name__ == "__main__":
    # Quick local test scaffold
    example_raw = {
        "platform": "ExampleShop",
        "url": "https://example.com/product/123",
        "image": "https://cdn.com/product/789.png",
        "name": "Example Running Shoe - Lightweight",
        "price": "79.99 USD",
        "rating": 4.3,
        "brand": "ExampleBrand",
        "sku": "EX-123"
    }

    example_transformed = {
        "materials": [
            {"name": "rubber sole", "weight": 0.25, "weight_source": "model-based estimate", "emission_factor": 2.5, "emission_factor_source": "Ecoinvent v3.9"},
            {"name": "textile upper", "weight": 0.3, "weight_source": "model-based estimate", "emission_factor": 5.0, "emission_factor_source": "model-based estimate"}
        ],
        "manufacturing_factor": {"value": 0.3, "source": "model-based estimate"},
        "transport": {"origin": "China", "distance_km": 20000.0, "mode": "sea", "emission_factor_ton_km": 0.01, "source": "model-based estimate"},
        "packaging": {"weight": 0.05, "emission_factor": 1.5, "source": "model-based estimate"},
        "product_weight": {"value": 0.65, "source": "sum of material weights"}
    }

    example_carbon = {
        "cf_total": 6.5,
        "breakdown": {"material": 3.25, "manufacturing": 0.975, "transport": 1.3, "packaging": 0.075}
    }

    arranged = arrange_product(example_raw, example_transformed, example_carbon)
    print(json.dumps(arranged, indent=2, ensure_ascii=False))
