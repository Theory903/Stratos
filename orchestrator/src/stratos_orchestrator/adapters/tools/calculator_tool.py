"""Safe calculator tool for deterministic arithmetic."""

from __future__ import annotations

import ast
import operator as op


_OPS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
    ast.USub: op.neg,
    ast.UAdd: op.pos,
}


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_evaluate(node.operand))
    raise ValueError("Unsupported expression")


class CalculatorTool:
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Evaluate arithmetic expressions exactly for quick calculations. Use this for percentages, "
            "position sizing, unit conversions, and deterministic math."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression using numbers and + - * / % ** parentheses.",
                }
            },
            "required": ["expression"],
        }

    async def execute(self, arguments: dict) -> dict:
        expression = str(arguments["expression"]).strip()
        tree = ast.parse(expression, mode="eval")
        value = _evaluate(tree)
        return {"expression": expression, "result": value}
