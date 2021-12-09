""" Validate graph files """
from __future__ import annotations
from typing import Dict

import os
import json
import jsonschema

# Validation schema for graph file
SCHEMA = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "../graph/flowchem-graph-spec.schema"
)


def load_graph_schema():
    """loads the schema defining valid config file."""
    with open(SCHEMA, "r") as fp:
        schema = json.load(fp)
        jsonschema.Draft7Validator.check_schema(schema)
        return schema


def validate_graph(graph: Dict):
    schema = load_graph_schema()
    jsonschema.validate(graph, schema=schema)
    assert graph["version"] == "1.0"
