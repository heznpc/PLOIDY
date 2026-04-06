"""Shared Task dataclass for experiment runners and task sets."""

from dataclasses import dataclass


@dataclass
class Task:
    """A single evaluation task with misleading context and ground truth."""

    id: str
    name: str
    context: str
    prompt: str
    ground_truth: list[str]
    domain: str
