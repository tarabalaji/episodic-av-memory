"""Validate scenario groups and train/validation/test assignments before evaluation."""


def validate_protocol(events, payload=None, split=None):
    episode_ids = {event.episode_id for event in events}
    if payload is None:
        if split is not None:
            raise ValueError("--split requires a protocol file.")
        return episode_ids, {identity: identity for identity in episode_ids}
    if not isinstance(payload, dict) or (type(payload.get("schema_version")) is not int or payload["schema_version"] != 1):
        raise ValueError("Protocol requires schema_version: 1.")
    episodes = payload.get("episodes")
    if not isinstance(episodes, dict) or set(episodes) != episode_ids:
        raise ValueError("Protocol must assign every dataset episode exactly once.")
    if split not in ("train", "validation", "test"):
        raise ValueError("Choose an explicit train, validation, or test split.")
    groups, group_splits = {}, {}
    for identity, assignment in episodes.items():
        if not isinstance(assignment, dict) or set(assignment) != {"group_id", "split"}:
            raise ValueError("Episode assignments require group_id and split.")
        group, part = assignment["group_id"], assignment["split"]
        if not isinstance(group, str) or not group.strip() or part not in ("train", "validation", "test"):
            raise ValueError("Invalid scenario group or split.")
        if group in group_splits and group_splits[group] != part:
            raise ValueError(f"Scenario group {group!r} crosses dataset splits.")
        group_splits[group] = part
        groups[identity] = group
    selected = {identity for identity, value in episodes.items() if value["split"] == split}
    if not selected:
        raise ValueError(f"The {split} split is empty.")
    return selected, {identity: groups[identity] for identity in selected}
