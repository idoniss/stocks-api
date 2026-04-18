from fastapi import FastAPI, HTTPException, Query

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


def compute(left: float, operator: str, right: float) -> float:
    if operator == "+":
        return left + right
    elif operator == "-":
        return left - right
    elif operator == "*":
        return left * right
    elif operator == "/":
        if right == 0:
            raise HTTPException(status_code=400, detail="Division by zero")
        return left / right
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown operator '{operator}'. Use +, -, *, /",
        )


@app.get("/calculate")
def calculate(
    left: float = Query(description="Left operand"),
    operator: str = Query(description="Operator: +, -, *, /"),
    right: float = Query(description="Right operand"),
):
    result = compute(left, operator, right)
    return {"result": result}
