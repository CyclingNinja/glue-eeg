import numpy as np
from echo import delay_callback
from glue.core.data_combo_helper import ManualDataComboHelper
from glue.viewers.matplotlib.state import (
    DeferredDrawCallbackProperty as DDCProperty,
    DeferredDrawSelectionCallbackProperty as DDSCProperty,
    MatplotlibDataViewerState,
    MatplotlibLayerState,
)

__all__ = ['EDFViewerState', 'EDFLayerState']


class EDFViewerState(MatplotlibDataViewerState):

    reference_data = DDSCProperty(docstring='EDF dataset being displayed')
    window_duration = DDCProperty(30.0, docstring='Visible time window in seconds')
    channel_spacing = DDCProperty(5.0, docstring='Vertical spacing between channels (normalised units)')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ref_data_helper = ManualDataComboHelper(self, 'reference_data')
        self.add_callback('reference_data', self._on_reference_data_changed, priority=1000)
        self.add_callback('window_duration', self._on_window_duration_changed)

    def _on_reference_data_changed(self, *args):
        if self.reference_data is None:
            return
        self._update_limits()

    def _on_window_duration_changed(self, *args):
        if self.reference_data is None:
            return
        t_min = self.x_min or 0.0
        time = self.reference_data['time']
        total_duration = float(time[-1])
        t_max = min(t_min + self.window_duration, total_duration)
        with delay_callback(self, 'x_min', 'x_max'):
            self.x_min = t_min
            self.x_max = t_max

    def _channel_ids(self):
        if self.reference_data is None:
            return []
        return [cid for cid in self.reference_data.main_components
                if cid.label != 'time']

    def _update_limits(self):
        if self.reference_data is None:
            return
        time = self.reference_data['time']
        total_duration = float(time[-1])
        n_channels = len(self._channel_ids())
        with delay_callback(self, 'x_min', 'x_max', 'y_min', 'y_max'):
            self.x_min = 0.0
            self.x_max = min(self.window_duration, total_duration)
            self.y_min = -(n_channels - 0.5) * self.channel_spacing
            self.y_max = 0.5 * self.channel_spacing

    def reset_limits(self):
        self._update_limits()


class EDFLayerState(MatplotlibLayerState):

    amplitude_scale = DDCProperty(1.0, docstring='Per-layer amplitude scaling')
