""" Validate graph files """
from __future__ import annotations

import json
import os
from typing import Dict

import jsonschema

# Validation schema for graph file
SCHEMA = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "../graph/flowchem-graph-spec.schema"
)


def load_graph_schema():
    """Loads and return the DeviceGraph schema."""
    with open(SCHEMA, "r", encoding="utf-8") as file_handle:
        schema = json.load(file_handle)
        jsonschema.Draft7Validator.check_schema(schema)
        return schema


def validate_graph(graph: Dict):
    """
    Validate a graph file.
    """
    schema = load_graph_schema()
    jsonschema.validate(graph, schema=schema)
    assert graph["version"] == "1.1"
