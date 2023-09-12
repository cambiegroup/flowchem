#!/usr/bin/env python
import json
import sys

import yaml

print(
    yaml.dump(json.load(open(sys.argv[1])), default_flow_style=False, sort_keys=False),
)
