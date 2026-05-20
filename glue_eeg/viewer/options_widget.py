from qtpy import QtWidgets
from qtpy.QtCore import Qt

__all__ = ['EDFOptionsWidget']


class EDFOptionsWidget(QtWidgets.QWidget):
    """
    Options panel shown in the Glue sidebar for the EDF viewer.

    Exposes:
    - Window duration  (how many seconds are visible at once)
    - Channel spacing  (vertical gap between channels, in normalised units)
    """

    def __init__(self, viewer_state, session, parent=None):
        super().__init__(parent=parent)
        self._state = viewer_state
        self._setup_ui()
        self._connect_state()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self._duration_spin = QtWidgets.QDoubleSpinBox()
        self._duration_spin.setRange(1.0, 3600.0)
        self._duration_spin.setSingleStep(5.0)
        self._duration_spin.setDecimals(1)
        self._duration_spin.setSuffix(' s')
        self._duration_spin.setValue(self._state.window_duration)
        self._duration_spin.setToolTip('Length of the visible time window')
        layout.addRow('Window:', self._duration_spin)

        self._spacing_spin = QtWidgets.QDoubleSpinBox()
        self._spacing_spin.setRange(0.1, 10.0)
        self._spacing_spin.setSingleStep(0.1)
        self._spacing_spin.setDecimals(2)
        self._spacing_spin.setValue(self._state.channel_spacing)
        self._spacing_spin.setToolTip(
            'Vertical gap between channels (larger = more spread out)'
        )
        layout.addRow('Spacing:', self._spacing_spin)

    # ------------------------------------------------------------------
    # State <-> widget synchronisation
    # ------------------------------------------------------------------

    def _connect_state(self):
        self._duration_spin.valueChanged.connect(self._on_duration_spin_changed)
        self._spacing_spin.valueChanged.connect(self._on_spacing_spin_changed)

        self._state.add_callback('window_duration', self._on_state_duration_changed)
        self._state.add_callback('channel_spacing', self._on_state_spacing_changed)

    # widget -> state

    def _on_duration_spin_changed(self, value: float):
        if abs(value - self._state.window_duration) > 1e-6:
            self._state.window_duration = value

    def _on_spacing_spin_changed(self, value: float):
        if abs(value - self._state.channel_spacing) > 1e-6:
            self._state.channel_spacing = value

    # state -> widget

    def _on_state_duration_changed(self, value: float):
        if abs(value - self._duration_spin.value()) > 1e-6:
            self._duration_spin.blockSignals(True)
            self._duration_spin.setValue(value)
            self._duration_spin.blockSignals(False)

    def _on_state_spacing_changed(self, value: float):
        if abs(value - self._spacing_spin.value()) > 1e-6:
            self._spacing_spin.blockSignals(True)
            self._spacing_spin.setValue(value)
            self._spacing_spin.blockSignals(False)
