"""
Timeline model for Qt table view.

Displays parsed events with synthesis status.
"""

from __future__ import annotations

from typing import List, Optional
from enum import Enum

from PySide6 import QtCore
from PySide6.QtCore import Qt

from .parser_rules import TimelineEvent


class SynthesisStatus(Enum):
    """Status of synthesis for each event."""
    PENDING = "⏳ Pending"
    SYNTHESIZING = "🎤 Synthesizing..."
    COMPLETE = "✓ Complete"
    ERROR = "✗ Error"
    SKIPPED = "— Skipped"  # For non-speech events


class TimelineModel(QtCore.QAbstractTableModel):
    """
    Qt model for timeline events.

    Columns: Line#, Type, Speaker, Text/Info, Duration, Status
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.events: List[TimelineEvent] = []
        self.statuses: List[SynthesisStatus] = []
        self.durations_ms: List[Optional[int]] = []  # Actual durations after synthesis
        self.error_messages: List[Optional[str]] = []

        self.headers = ["Line", "Type", "Speaker", "Content", "Duration", "Status"]

    def set_events(self, events: List[TimelineEvent]):
        """Set timeline events."""
        self.beginResetModel()
        self.events = events
        self.statuses = [
            SynthesisStatus.PENDING if e.event_type == 'speech'
            else SynthesisStatus.SKIPPED
            for e in events
        ]
        self.durations_ms = [None] * len(events)
        self.error_messages = [None] * len(events)
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:
        return len(self.events)

    def columnCount(self, parent=QtCore.QModelIndex()) -> int:
        return len(self.headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]
        return None

    def data(self, index: QtCore.QModelIndex, role: int):
        if not index.isValid():
            return None

        event = self.events[index.row()]
        col = index.column()

        if role == Qt.DisplayRole:
            if col == 0:  # Line number
                return str(event.line_number)
            elif col == 1:  # Type
                if event.event_type == 'speech':
                    return "🎤 Speech"
                elif event.event_type == 'silence':
                    return "🔇 Silence"
                elif event.event_type == 'sfx':
                    return "🔊 SFX"
            elif col == 2:  # Speaker
                return event.speaker or "—"
            elif col == 3:  # Content
                if event.event_type == 'speech':
                    text = event.text or ""
                    return text[:50] + "..." if len(text) > 50 else text
                elif event.event_type == 'silence':
                    return f"{event.duration_ms}ms"
                elif event.event_type == 'sfx':
                    return str(event.sfx_path.name) if event.sfx_path else "?"
            elif col == 4:  # Duration
                duration = self.durations_ms[index.row()]
                if duration is not None:
                    return f"{duration}ms"
                elif event.event_type == 'silence':
                    return f"{event.duration_ms}ms"
                return "—"
            elif col == 5:  # Status
                status = self.statuses[index.row()]
                error = self.error_messages[index.row()]
                if error:
                    return f"{status.value}: {error[:30]}"
                return status.value

        elif role == Qt.BackgroundRole:
            # Color-code by status
            status = self.statuses[index.row()]
            if status == SynthesisStatus.ERROR:
                return QtCore.Qt.red
            elif status == SynthesisStatus.COMPLETE:
                return QtCore.Qt.green
            elif status == SynthesisStatus.SYNTHESIZING:
                return QtCore.Qt.yellow

        return None

    def set_status(self, row: int, status: SynthesisStatus, error: Optional[str] = None):
        """Update synthesis status for a row."""
        if 0 <= row < len(self.statuses):
            self.statuses[row] = status
            self.error_messages[row] = error

            # Emit data changed for status column
            idx = self.index(row, 5)
            self.dataChanged.emit(idx, idx)

    def set_duration(self, row: int, duration_ms: int):
        """Set actual duration after synthesis."""
        if 0 <= row < len(self.durations_ms):
            self.durations_ms[row] = duration_ms

            # Emit data changed for duration column
            idx = self.index(row, 4)
            self.dataChanged.emit(idx, idx)

    def get_event(self, row: int) -> Optional[TimelineEvent]:
        """Get event at row."""
        if 0 <= row < len(self.events):
            return self.events[row]
        return None

    def clear(self):
        """Clear all events."""
        self.beginResetModel()
        self.events = []
        self.statuses = []
        self.durations_ms = []
        self.error_messages = []
        self.endResetModel()
