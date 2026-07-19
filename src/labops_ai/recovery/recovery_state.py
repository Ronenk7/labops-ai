"""Persist recovery cooldown state using atomic JSON writes."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from labops_ai.config.utils import PROJECT_ROOT
from labops_ai.recovery.recovery_models import (
    RecoveryActionState,
    RecoveryState,
)


_RECOVERY_STATE_SCHEMA_VERSION = 1


class RecoveryStateError(RuntimeError):
    """Represent recovery state storage failures."""


class RecoveryStateDataError(RecoveryStateError):
    """Represent invalid persisted recovery state."""


@dataclass(frozen=True, slots=True)
class JsonRecoveryStateStore:
    """Atomically read and write recovery cooldown state."""

    configured_path: str | Path = (
        "runtime/recovery_state.json"
    )

    @property
    def path(self) -> Path:
        """Return the resolved state path."""
        configured_path = Path(
            self.configured_path
        ).expanduser()

        if configured_path.is_absolute():
            return configured_path

        return PROJECT_ROOT / configured_path

    def load(self) -> RecoveryState:
        """Load persisted state or return empty state."""
        try:
            raw_content = self.path.read_text(
                encoding="utf-8"
            )
        except FileNotFoundError:
            return RecoveryState()
        except OSError as error:
            raise RecoveryStateError(
                "Recovery state could not be read."
            ) from error

        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError as error:
            raise RecoveryStateDataError(
                "Recovery state contains invalid JSON."
            ) from error

        return self._deserialize(payload)

    def save(self, state: RecoveryState) -> None:
        """Persist state using atomic replacement."""
        if not isinstance(state, RecoveryState):
            raise TypeError(
                "state must be a RecoveryState."
            )

        payload = {
            "schema_version": (
                _RECOVERY_STATE_SCHEMA_VERSION
            ),
            "actions": [
                {
                    "action_id": action.action_id,
                    "last_attempted_at": (
                        action.last_attempted_at.isoformat()
                    ),
                }
                for action in state.actions
            ],
        }
        serialized = (
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )

        temporary_path: Path | None = None

        try:
            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            descriptor, temporary_name = (
                tempfile.mkstemp(
                    dir=self.path.parent,
                    prefix=f".{self.path.name}.",
                    suffix=".tmp",
                )
            )
            temporary_path = Path(temporary_name)

            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
            ) as file:
                file.write(serialized)
                file.flush()
                os.fsync(file.fileno())

            os.replace(temporary_path, self.path)
        except OSError as error:
            raise RecoveryStateError(
                "Recovery state could not be saved."
            ) from error
        finally:
            if (
                temporary_path is not None
                and temporary_path.exists()
            ):
                temporary_path.unlink()

    @staticmethod
    def _deserialize(payload: object) -> RecoveryState:
        """Convert persisted JSON into validated state."""
        if not isinstance(payload, dict):
            raise RecoveryStateDataError(
                "Recovery state root must be an object."
            )

        if payload.get("schema_version") != (
            _RECOVERY_STATE_SCHEMA_VERSION
        ):
            raise RecoveryStateDataError(
                "Unsupported recovery state schema."
            )

        actions = payload.get("actions")

        if not isinstance(actions, list):
            raise RecoveryStateDataError(
                "Recovery state actions must be an array."
            )

        try:
            return RecoveryState(
                actions=tuple(
                    JsonRecoveryStateStore._parse_action(
                        action
                    )
                    for action in actions
                )
            )
        except (
            TypeError,
            ValueError,
            KeyError,
        ) as error:
            raise RecoveryStateDataError(
                "Recovery state data is invalid."
            ) from error

    @staticmethod
    def _parse_action(
        payload: Any,
    ) -> RecoveryActionState:
        """Parse one persisted action state."""
        if not isinstance(payload, dict):
            raise TypeError(
                "Recovery action state must be an object."
            )

        if set(payload) != {
            "action_id",
            "last_attempted_at",
        }:
            raise ValueError(
                "Recovery action state keys are invalid."
            )

        return RecoveryActionState(
            action_id=payload["action_id"],
            last_attempted_at=datetime.fromisoformat(
                payload["last_attempted_at"]
            ),
        )
