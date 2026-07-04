"""Limited native evaluation for small NetLogo metric expressions.

This module is not a NetLogo interpreter. It evaluates the first useful
monitor/plot expression family needed by the semantic coverage map: turtle
counts, simple turtle-state predicates, link counts, and arithmetic over those
counts.
"""
from __future__ import annotations

import ast
import math
import re
from collections.abc import Callable

from abm_auto.netlogo_semantics import NetLogoTurtle, NetLogoWorld


_COUNT_WITH_RE = re.compile(r"\bcount\s+turtles\s+with\s+\[([^\]]+)\]")
_COUNT_LINK_NEIGHBORS_WITH_RE = re.compile(r"\bcount\s+link-neighbors\s+with\s+\[([^\]]+)\]")
_COUNT_LINK_NEIGHBORS_RE = re.compile(r"\bcount\s+link-neighbors\b")
_COUNT_LINKS_RE = re.compile(r"\bcount\s+links\b")
_COUNT_TURTLES_RE = re.compile(r"\bcount\s+turtles\b")
_VARIABLE_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_\-?]*")


def evaluate_netlogo_metric(
    world: NetLogoWorld,
    expression: str,
    *,
    context: NetLogoTurtle | None = None,
) -> int | float:
    """Evaluate a small, explicit NetLogo metric expression family."""

    if not isinstance(world, NetLogoWorld):
        raise ValueError("world must be a NetLogoWorld")

    original = expression
    expr = str(expression).strip()
    if expr.startswith("plot "):
        expr = expr[len("plot ") :].strip()
    if not expr:
        raise ValueError(f"Unsupported NetLogo metric expression: {original}")

    try:
        expr = _COUNT_LINK_NEIGHBORS_WITH_RE.sub(
            lambda match: str(_count_link_neighbors_with(world, context, match.group(1))),
            expr,
        )
        expr = _COUNT_LINK_NEIGHBORS_RE.sub(
            lambda match: str(_count_link_neighbors(world, context)),
            expr,
        )
        expr = _COUNT_WITH_RE.sub(lambda match: str(_count_with(world, match.group(1))), expr)
        expr = _COUNT_LINKS_RE.sub(str(len(world.links)), expr)
        expr = _COUNT_TURTLES_RE.sub(str(len(world.turtles)), expr)
        return _safe_eval_arithmetic(expr)
    except (SyntaxError, ValueError, TypeError, ZeroDivisionError) as exc:
        raise ValueError(f"Unsupported NetLogo metric expression: {original}") from exc


def netlogo_metric_expression_gate() -> tuple[bool, str]:
    """Gate the supported Virus-style count and percentage expression family."""

    world = NetLogoWorld(seed=0, schedule="sequential")
    world.create_turtles(3, **{"infected?": False, "resistant?": False})
    world.create_turtles(2, **{"infected?": True, "resistant?": False})
    world.create_turtles(1, **{"infected?": False, "resistant?": True})

    expected = {
        "count turtles with [not infected? and not resistant?]": 3,
        "count turtles with [infected?]": 2,
        "count turtles with [resistant?]": 1,
        "plot (count turtles with [not infected? and not resistant?]) / (count turtles) * 100": 50.0,
        "plot (count turtles with [infected?]) / (count turtles) * 100": 100.0 / 3.0,
        "plot (count turtles with [resistant?]) / (count turtles) * 100": 100.0 / 6.0,
    }

    try:
        for expression, target in expected.items():
            value = evaluate_netlogo_metric(world, expression)
            if not math.isclose(float(value), float(target)):
                return (
                    False,
                    f"metric expression mismatch for {expression!r}: {value!r} != {target!r}",
                )
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo limited metric expression family gate passed; this is not general NetLogo execution.",
    )


def netlogo_link_metric_gate() -> tuple[bool, str]:
    """Gate the supported link count expression family."""

    world = NetLogoWorld(seed=0, schedule="sequential")
    turtles = world.create_turtles(4).snapshot()
    world.create_link(turtles[0], turtles[1])
    world.create_link(turtles[0], turtles[2])
    world.create_link(turtles[0], turtles[3], directed=True)

    expected = {
        "count links": 3,
        "count link-neighbors": 2,
        "(count links) + (count link-neighbors)": 5,
    }

    try:
        for expression, target in expected.items():
            value = evaluate_netlogo_metric(world, expression, context=turtles[0])
            if value != target:
                return (
                    False,
                    f"link metric mismatch for {expression!r}: {value!r} != {target!r}",
                )
        if evaluate_netlogo_metric(world, "count link-neighbors", context=turtles[3]) != 0:
            return False, "directed links leaked into undirected link-neighbors"
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo limited link metric family gate passed; this is not general NetLogo execution.",
    )


def netlogo_link_predicate_gate() -> tuple[bool, str]:
    """Gate the supported filtered link-neighbor count expression family."""

    world = NetLogoWorld(seed=0, schedule="sequential")
    turtles = world.create_turtles(4).snapshot()
    turtles[1].set("infected?", True).set("resistant?", False)
    turtles[2].set("infected?", False).set("resistant?", False)
    turtles[3].set("infected?", True).set("resistant?", True)
    world.create_link(turtles[0], turtles[1])
    world.create_link(turtles[0], turtles[2])
    world.create_link(turtles[0], turtles[3], directed=True)

    expected = {
        "count link-neighbors with [infected?]": 1,
        "count link-neighbors with [not infected?]": 1,
        "count link-neighbors with [not infected? and not resistant?]": 1,
        "(count link-neighbors with [infected?]) * 10": 10,
    }

    try:
        for expression, target in expected.items():
            value = evaluate_netlogo_metric(world, expression, context=turtles[0])
            if value != target:
                return (
                    False,
                    f"link predicate mismatch for {expression!r}: {value!r} != {target!r}",
                )
        if (
            evaluate_netlogo_metric(
                world,
                "count link-neighbors with [infected?]",
                context=turtles[3],
            )
            != 0
        ):
            return False, "directed links leaked into filtered link-neighbors"
    except ValueError as exc:
        return False, str(exc)

    return (
        True,
        "NetLogo limited link predicate family gate passed; this is not general NetLogo execution.",
    )


def _count_with(world: NetLogoWorld, predicate_text: str) -> int:
    predicate = _compile_predicate(predicate_text)
    return sum(1 for turtle in world.turtles if predicate(turtle))


def _count_link_neighbors_with(
    world: NetLogoWorld,
    context: NetLogoTurtle | None,
    predicate_text: str,
) -> int:
    predicate = _compile_predicate(predicate_text)
    return sum(1 for turtle in _link_neighbors(world, context) if predicate(turtle))


def _count_link_neighbors(world: NetLogoWorld, context: NetLogoTurtle | None) -> int:
    return len(_link_neighbors(world, context))


def _link_neighbors(world: NetLogoWorld, context: NetLogoTurtle | None) -> list[NetLogoTurtle]:
    if not isinstance(context, NetLogoTurtle):
        raise ValueError("link-neighbors requires a NetLogoTurtle context")
    return world.link_neighbors(context)


def _compile_predicate(predicate_text: str) -> Callable[[NetLogoTurtle], bool]:
    terms = [part.strip() for part in predicate_text.strip().split(" and ")]
    if not terms or any(not term for term in terms):
        raise ValueError("unsupported predicate")

    compiled = [_compile_predicate_term(term) for term in terms]
    return lambda turtle: all(fn(turtle) for fn in compiled)


def _compile_predicate_term(term: str) -> Callable[[NetLogoTurtle], bool]:
    negate = term.startswith("not ")
    name = term[4:].strip() if negate else term
    if not _VARIABLE_RE.fullmatch(name):
        raise ValueError("unsupported predicate term")

    def check(turtle: NetLogoTurtle) -> bool:
        value = bool(turtle.get(name, False))
        return not value if negate else value

    return check


def _safe_eval_arithmetic(expr: str) -> int | float:
    node = ast.parse(expr, mode="eval")
    value = _eval_node(node.body)
    if isinstance(value, bool):
        raise ValueError("unsupported boolean arithmetic")
    return value


def _eval_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("unsupported constant")
        return node.value

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval_node(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right

    raise ValueError("unsupported arithmetic")
