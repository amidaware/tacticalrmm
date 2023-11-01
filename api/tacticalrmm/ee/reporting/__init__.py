"""
Copyright (c) 2023-present Amidaware Inc.
This file is subject to the EE License Agreement.
For details, see: https://license.tacticalrmm.com/ee
"""

import re
from datetime import datetime, timedelta

import yaml
from django.utils import timezone

now_regex = re.compile(
    r"^(weeks|days|hours|minutes|seconds|microseconds)=(-?\d*)$", re.VERBOSE
)


def construct_yaml_now(loader, node):
    loader.construct_scalar(node)
    match = now_regex.match(node.value)
    now = timezone.now()
    if match:
        now = now + timedelta(**{match.group(1): int(match.group(2))})
    return now


def represent_datetime_now(dumper, data):
    value = data.isoformat(" ")
    return dumper.represent_scalar("!now", value)


yaml.SafeLoader.add_constructor("!now", construct_yaml_now)
yaml.SafeDumper.add_representer(datetime, represent_datetime_now)
