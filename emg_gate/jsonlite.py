"""Tiny JSON Schema subset validator (numpy-only policy: no jsonschema at runtime).

Covers the keywords the commons schemas use: type, enum, const, pattern,
required, properties, additionalProperties (bool or schema), items,
minItems, uniqueItems, contains, minimum, maximum, exclusiveMinimum,
minLength. Unknown keywords are ignored, so keep the commons schemas inside
this subset; tests cross-check against `jsonschema` when it is installed.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
}


def errors(schema: Dict[str, Any], value: Any, path: str = "$") -> List[str]:
    """All violations of `schema` by `value`, as `path: message` strings."""
    out: List[str] = []
    t = schema.get("type")
    if t is not None and not _TYPES[t](value):
        return [f"{path}: expected {t}"]
    if "const" in schema and value != schema["const"]:
        out.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: {value!r} not in {schema['enum']}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if len(value) < schema.get("minLength", 0):
            out.append(f"{path}: shorter than {schema['minLength']}")
    if _TYPES["number"](value):
        if "minimum" in schema and value < schema["minimum"]:
            out.append(f"{path}: {value} < {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            out.append(f"{path}: {value} > {schema['maximum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            out.append(f"{path}: {value} <= {schema['exclusiveMinimum']}")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                out.append(f"{path}: missing {key}")
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in props:
                out.extend(errors(props[key], item, f"{path}.{key}"))
            elif extra is False:
                out.append(f"{path}: field not allowed: {key}")
            elif isinstance(extra, dict):
                out.extend(errors(extra, item, f"{path}.{key}"))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            out.append(f"{path}: fewer than {schema['minItems']} items")
        if schema.get("uniqueItems") and len({repr(v) for v in value}) != len(value):
            out.append(f"{path}: items not unique")
        if "items" in schema:
            for i, item in enumerate(value):
                out.extend(errors(schema["items"], item, f"{path}[{i}]"))
        if "contains" in schema and not any(not errors(schema["contains"], v) for v in value):
            out.append(f"{path}: contains no item matching {schema['contains']}")
    return out


def compile_check(schema: Dict[str, Any]):
    """A fast yes/no validator for the same subset. Use errors() only when it says no."""
    checks = []
    t = schema.get("type")
    if t is not None:
        tf = _TYPES[t]
        checks.append(tf)
    if "const" in schema:
        c = schema["const"]
        checks.append(lambda v, c=c: v == c)
    if "enum" in schema:
        e = schema["enum"]
        checks.append(lambda v, e=e: v in e)
    if "pattern" in schema:
        rx = re.compile(schema["pattern"])
        checks.append(lambda v, rx=rx: not isinstance(v, str) or rx.search(v) is not None)
    if "minLength" in schema:
        n = schema["minLength"]
        checks.append(lambda v, n=n: not isinstance(v, str) or len(v) >= n)
    num = _TYPES["number"]
    for key, op in (("minimum", lambda v, b: v >= b), ("maximum", lambda v, b: v <= b),
                    ("exclusiveMinimum", lambda v, b: v > b)):
        if key in schema:
            b = schema[key]
            checks.append(lambda v, b=b, op=op: not num(v) or op(v, b))
    if schema.get("type") == "object" or "properties" in schema or "required" in schema:
        props = {k: compile_check(s) for k, s in schema.get("properties", {}).items()}
        req = tuple(schema.get("required", ()))
        extra = schema.get("additionalProperties", True)
        extra_check = compile_check(extra) if isinstance(extra, dict) else None

        def obj(v, props=props, req=req, extra=extra, extra_check=extra_check):
            if not isinstance(v, dict):
                return True  # type check above decides
            for k in req:
                if k not in v:
                    return False
            for k, item in v.items():
                sub = props.get(k)
                if sub is not None:
                    if not sub(item):
                        return False
                elif extra is False:
                    return False
                elif extra_check is not None and not extra_check(item):
                    return False
            return True
        checks.append(obj)
    if schema.get("type") == "array" or "items" in schema:
        item_check = compile_check(schema["items"]) if "items" in schema else None
        contains = compile_check(schema["contains"]) if "contains" in schema else None
        min_items, unique = schema.get("minItems", 0), schema.get("uniqueItems", False)

        def arr(v, item_check=item_check, contains=contains, min_items=min_items, unique=unique):
            if not isinstance(v, list):
                return True
            if len(v) < min_items:
                return False
            if unique and len({repr(x) for x in v}) != len(v):
                return False
            if item_check is not None and not all(item_check(x) for x in v):
                return False
            if contains is not None and not any(contains(x) for x in v):
                return False
            return True
        checks.append(arr)

    checks = tuple(checks)  # the type check, when present, is first and guards the others

    def run(v, checks=checks):
        for c in checks:
            if not c(v):
                return False
        return True
    return run
