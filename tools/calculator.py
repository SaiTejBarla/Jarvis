"""
tools/calculator.py — Safe math expression evaluator.

Evaluates arithmetic expressions using Python's ast module.
Never calls eval() directly — parses the AST to allow only safe operations.
"""

import ast
import logging
import operator
from .base import BaseTool

logger = logging.getLogger(__name__)

# Allowed operators
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants allowed.")
    if isinstance(node, ast.BinOp):
        op = _OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return op(_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression type: {type(node).__name__}")


class CalculatorTool(BaseTool):
    name = "calculator"
    description = (
        "Evaluate a math expression. Query should be the expression, e.g. '25 * 4 + 10'."
    )

    def run(self, query: str) -> str:
        # Strip common natural language wrappers
        import re
        expr = re.sub(
            r"(what is|calculate|compute|evaluate|how much is|=\?*)", "", query, flags=re.IGNORECASE
        ).strip().rstrip("?")

        try:
            tree = ast.parse(expr, mode="eval")
            result = _safe_eval(tree.body)
            # Format cleanly — avoid floating-point noise
            if isinstance(result, float) and result == int(result):
                result = int(result)
            return f"{expr} = {result}"
        except Exception as exc:
            logger.debug("Calculator failed for %r: %s", expr, exc)
            return f"I couldn't evaluate '{expr}'. Please rephrase the expression."
