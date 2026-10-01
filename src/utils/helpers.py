"""Configuration and atomic JSON output shared by the command-line tools."""
import json
import math
import os
from pathlib import Path
import tempfile
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STRATEGIES = ("fifo", "importance", "compression", "core_safety")


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, encoding="utf-8",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate experiment settings instead of silently keeping the last."""
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or key in result:
                raise ValueError(f"Configuration key must be unique text: {key!r}.")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def load_config(path=None):
    path = Path(path) if path else PROJECT_ROOT / "configs/default.yaml"
    with path.open(encoding="utf-8") as stream:
        config = yaml.load(stream, Loader=UniqueKeyLoader)
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a YAML mapping.")
    allowed = {"events_path", "output_dir", "capacity", "top_k", "strategy", "planner", "model", "similarity_window"}
    if set(config) - allowed:
        raise ValueError(f"Unknown configuration keys: {sorted(set(config) - allowed)}.")
    window = config.get("similarity_window", 10.0)
    if isinstance(window, bool) or not isinstance(window, (int, float)) or not math.isfinite(window) or window < 0:
        raise ValueError("similarity_window must be finite and nonnegative.")
    if config.get("planner") == "openai" and (not isinstance(config.get("model"), str) or not config["model"].strip()):
        raise ValueError("An explicit model is required for the optional OpenAI planner.")
    for key in ("capacity", "top_k"):
        if type(config.get(key)) is not int or config[key] <= 0:
            raise ValueError(f"{key} must be a positive integer.")
    if config.get("strategy") not in STRATEGIES + ("no_memory", "unlimited"):
        raise ValueError(f"strategy must be one of {STRATEGIES}.")
    if config.get("planner") not in ("rule_based", "openai"):
        raise ValueError("planner must be rule_based or openai.")
    # Data/output paths are project-relative, independent of the launch directory.
    for key in ("events_path", "output_dir"):
        value = config.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a nonempty path.")
        config[key] = str((PROJECT_ROOT / value).resolve())
    return config


def loads_json(text):
    """Reject duplicate keys/nonstandard numbers in datasets and research labels."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key!r}.")
            result[key] = value
        return result
    def invalid_number(value):
        raise ValueError(f"Nonfinite JSON number: {value}.")
    return json.loads(text, object_pairs_hook=unique_object, parse_constant=invalid_number)


def read_json(path):
    return loads_json(Path(path).read_text(encoding="utf-8"))
