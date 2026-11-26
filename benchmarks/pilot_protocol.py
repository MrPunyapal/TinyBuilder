"""Validate pilot driver rows before independent PHP scoring."""
ALLOWED = {
    "proposal", "context_retrieval", "protocol", "reasoning", "runtime",
    "timeout", "orchestration", "replacement_match", "output_limit",
}


def index_rows(responses, expected):
    indexed = {}
    ready = 0
    for response in responses:
        if not isinstance(response, dict):
            raise ValueError("Driver row must be an object")
        if "case" not in response:
            ready += 1
            if ready > 1 or set(response) != {"ready_ms"} or type(response["ready_ms"]) is not int:
                raise ValueError("Invalid driver readiness record")
            continue
        key = (response["case"], response.get("arm"))
        category = response.get("category")
        if key not in expected or key in indexed:
            raise ValueError("Unexpected or duplicate driver trial")
        if category not in ALLOWED:
            raise ValueError("Driver cannot assert evaluator success")
        if category == "proposal":
            if not isinstance(response.get("preview"), str) or not response["preview"]:
                raise ValueError("Proposal requires source text")
        elif "preview" in response:
            raise ValueError("Unexpected source text in failed trial")
        indexed[key] = response
    return indexed
