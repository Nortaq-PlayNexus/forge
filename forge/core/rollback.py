"""Rollback manager.

Creates and manages deployment snapshots for rollback capability.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

SNAPSHOTS_DIR = ".forge/snapshots"


def _snapshots_path(base: Path | None = None) -> Path:
    p = (base or Path.cwd()) / SNAPSHOTS_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def _snapshot_id(state: dict) -> str:
    raw = json.dumps(state, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


class RollbackManager:
    """Manages deployment snapshots for rollback."""

    def __init__(self, base_path: Path | None = None):
        self.base = base_path or Path.cwd()
        self.dir = _snapshots_path(self.base)

    def create_snapshot(self, deployment_state: dict) -> str:
        """Save current state before deploy. Returns snapshot ID."""
        snap_id = _snapshot_id(deployment_state)
        snapshot = {
            "id": snap_id,
            "timestamp": datetime.now().isoformat(),
            "state": deployment_state,
        }
        snap_file = self.dir / f"{snap_id}.json"
        snap_file.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")
        return snap_id

    def rollback(self, snapshot_id: str) -> dict:
        """Revert to a previous snapshot. Returns the restored state."""
        snap_file = self.dir / f"{snapshot_id}.json"
        if not snap_file.exists():
            raise FileNotFoundError(f"Snapshot {snapshot_id} not found")
        data = json.loads(snap_file.read_text(encoding="utf-8"))
        return data["state"]

    def list_snapshots(self) -> list[dict]:
        """List all saved snapshots."""
        snapshots = []
        for f in sorted(self.dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                snapshots.append({
                    "id": data["id"],
                    "timestamp": data["timestamp"],
                    "keys": list(data.get("state", {}).keys()),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return snapshots

    def diff_snapshots(self, a_id: str, b_id: str) -> dict:
        """Show differences between two snapshots."""
        a_file = self.dir / f"{a_id}.json"
        b_file = self.dir / f"{b_id}.json"

        if not a_file.exists():
            raise FileNotFoundError(f"Snapshot {a_id} not found")
        if not b_file.exists():
            raise FileNotFoundError(f"Snapshot {b_id} not found")

        a_data = json.loads(a_file.read_text(encoding="utf-8"))
        b_data = json.loads(b_file.read_text(encoding="utf-8"))

        a_state = a_data.get("state", {})
        b_state = b_data.get("state", {})

        diff = {
            "added": {k: v for k, v in b_state.items() if k not in a_state},
            "removed": {k: v for k, v in a_state.items() if k not in b_state},
            "changed": {},
        }

        for key in a_state:
            if key in b_state and a_state[key] != b_state[key]:
                diff["changed"][key] = {"from": a_state[key], "to": b_state[key]}

        return diff

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot."""
        snap_file = self.dir / f"{snapshot_id}.json"
        if snap_file.exists():
            snap_file.unlink()
            return True
        return False
