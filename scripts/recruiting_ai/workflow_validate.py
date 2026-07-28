"""Validation for exported n8n workflow JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SECRET_MARKERS = [
    "sk-",
    "AIza",
    "xoxb-",
    "ghp_",
    "hunter_",
    "apollo_",
    "rocketreach_",
]


def validate_workflow(path: str | Path) -> list[str]:
    path = Path(path)
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path}: invalid JSON: {exc}"]

    if not isinstance(data, dict):
        return [f"{path}: workflow export must be a JSON object"]
    if not data.get("name"):
        errors.append(f"{path}: missing workflow name")

    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append(f"{path}: workflow must include at least one node")
        nodes = []

    names: set[str] = set()
    ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            errors.append(f"{path}: node must be an object")
            continue
        name = node.get("name")
        node_id = node.get("id")
        if not name:
            errors.append(f"{path}: node missing name")
        if not node_id:
            errors.append(f"{path}: node {name or '<unknown>'} missing id")
        if name in names:
            errors.append(f"{path}: duplicate node name {name}")
        if node_id in ids:
            errors.append(f"{path}: duplicate node id {node_id}")
        names.add(str(name))
        ids.add(str(node_id))
        if "type" not in node:
            errors.append(f"{path}: node {name or '<unknown>'} missing type")
        if "position" not in node:
            errors.append(f"{path}: node {name or '<unknown>'} missing position")

    if not isinstance(data.get("connections", {}), dict):
        errors.append(f"{path}: connections must be an object")

    serialized = json.dumps(data)
    for marker in SECRET_MARKERS:
        if marker in serialized:
            errors.append(f"{path}: possible secret marker found: {marker}")
    return errors


def validate_all(root: str | Path = "n8n/workflows") -> list[str]:
    root = Path(root)
    errors: list[str] = []
    for path in sorted(root.glob("*.json")):
        errors.extend(validate_workflow(path))
    if not list(root.glob("*.json")):
        errors.append(f"{root}: no workflow exports found")
    return errors

