""" Validate config files """
from __future__ import annotations

import json
import os
from typing import Dict

import jsonschema

# Validation schema for config file
SCHEMA = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "flowchem-config.schema"
)


def get_config_schema():
    """Loads and return the DeviceGraph schema."""
    with open(SCHEMA, "r", encoding="utf-8") as file_handle:
        schema = json.load(file_handle)
    jsonschema.Draft7Validator.check_schema(schema)
    return schema


def validate_config(config: Dict):
    """
    Validate a config file.
    """
    schema = get_config_schema()
    jsonschema.validate(config, schema=schema)
    assert config["version"] == "1.0"
