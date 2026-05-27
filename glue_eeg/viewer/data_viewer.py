from echo import delay_callback
from glue.utils import decorate_all_methods, defer_draw
from glue_qt.viewers.matplotlib.data_viewer import MatplotlibDataViewer
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .layer_artist import EDFLayerArtist
from .options_widget import EDFOptionsWidget
from .roi_panel import ROIPanel
from .state import EDFViewerState

__all__ = ['EDFViewer']

# Scrollbar resolution: ticks per second (gives 10 ms precision)
_SCROLLBAR_SCALE = 100


@decorate_all_methods(defer_draw)
class EDFViewer(MatplotlibDataViewer):

    LABEL = 'EEG / EDF Viewer'

    _state_cls = EDFViewerState
    _options_cls = EDFOptionsWidget
    _data_artist_cls = EDFLayerArtist
    _subset_artist_cls = EDFLayerArtist
    _layer_style_widget_cls = None

    tools = ['mpl:home', 'mpl:pan', 'mpl:zoom', 'select:xrange', 'save']
    subtools = {
        'save': ['mpl:save'],
        'window': ['window:movetab', 'window:title'],
    }
    inherit_tools = False

    def __init__(self, session, parent=None, state=None):
        super().__init__(session, parent=parent, state=state)
        self._last_roi_range = None
        self._setup_layout()
        self._setup_axes_style()
        self._connect_state()

    # ------------------------------------------------------------------
    # Layout: wrap the mpl widget in a splitter + scrollbar
    # ------------------------------------------------------------------

    def _setup_layout(self):
        # Horizontal splitter: plot | ROI panel
        splitter = QtWidgets.QSplitter(Qt.Horizontal)
        splitter.addWidget(self.mpl_widget)
        self._roi_panel = ROIPanel(self)
        splitter.addWidget(self._roi_panel)
        splitter.setSizes([700, 250])
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        # Time scrollbar
        self._time_scrollbar = QtWidgets.QScrollBar(Qt.Horizontal)
        self._time_scrollbar.setMinimum(0)
        self._time_scrollbar.setMaximum(0)
        self._time_scrollbar.setSingleStep(int(0.5 * _SCROLLBAR_SCALE))
        self._time_scrollbar.setPageStep(int(30 * _SCROLLBAR_SCALE))
        self._time_scrollbar.valueChanged.connect(self._on_scrollbar_moved)

        # Vertical wrapper: splitter on top, scrollbar on bottom
        wrapper = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(wrapper)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addWidget(splitter)
        vbox.addWidget(self._time_scrollbar)

        self.setCentralWidget(wrapper)

    def _setup_axes_style(self):
        self.axes.set_xlabel('Time (s)')
        self.axes.tick_params(axis='y', which='both', length=0)
        self.axes.spines['left'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        self.axes.spines['top'].set_visible(False)
        self.axes.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)

    # ------------------------------------------------------------------
    # State callbacks
    # ------------------------------------------------------------------

    def _connect_state(self):
        self.state.add_callback('reference_data', self._on_reference_data_changed)
        self.state.add_callback('window_duration', self._on_window_duration_changed)
        self.state.add_callback('x_min', self._sync_scrollbar_to_state)
        self.state.add_callback('x_max', self._sync_scrollbar_to_state)

    def _on_reference_data_changed(self, *args):
        if self.state.reference_data is None:
            self._time_scrollbar.setMaximum(0)
            return
        self._update_scrollbar_range()

    def _on_window_duration_changed(self, *args):
        self._update_scrollbar_range()

    def _update_scrollbar_range(self):
        if self.state.reference_data is None:
            return
        total = float(self.state.reference_data['time'][-1])
        dur = self.state.window_duration
        maximum = max(0, int((total - dur) * _SCROLLBAR_SCALE))
        page = int(dur * _SCROLLBAR_SCALE)
        self._time_scrollbar.setMaximum(maximum)
        self._time_scrollbar.setPageStep(page)

    # ------------------------------------------------------------------
    # Scrollbar <-> state synchronisation
    # ------------------------------------------------------------------

    def _on_scrollbar_moved(self, value: int):
        """Scrollbar → state: shift the visible window."""
        t_min = value / _SCROLLBAR_SCALE
        t_max = t_min + self.state.window_duration
        with delay_callback(self.state, 'x_min', 'x_max'):
            self.state.x_min = t_min
            self.state.x_max = t_max

    def _sync_scrollbar_to_state(self, *args):
        """State → scrollbar: keep the thumb position consistent."""
        if self.state.x_min is None:
            return
        val = int(self.state.x_min * _SCROLLBAR_SCALE)
        self._time_scrollbar.blockSignals(True)
        self._time_scrollbar.setValue(val)
        self._time_scrollbar.blockSignals(False)

    # ------------------------------------------------------------------
    # Data layer management
    # ------------------------------------------------------------------

    def add_data(self, data):
        result = super().add_data(data)
        if result:
            self.state._ref_data_helper.append_data(data)
        return result

    def remove_data(self, data):
        self.state._ref_data_helper.remove_data(data)
        super().remove_data(data)

    def apply_roi(self, roi, override_mode=None):
        if not self.layers:
            return
        data = self.state.reference_data
        if data is None:
            return
        try:
            time_cid = data.id['time']
        except Exception:
            return
        from glue.core.subset import RangeSubsetState
        subset_state = RangeSubsetState(roi.lo, roi.hi, time_cid)
        self.session.edit_subset_mode.update(self._data, subset_state, focus_data=data)
        self._last_roi_range = (roi.lo, roi.hi)

    # ------------------------------------------------------------------
    # Public API for external services
    # ------------------------------------------------------------------

    def add_roi_annotations(self, regions) -> None:
        """
        Load time-stamped regions of interest from an external service.

        Parameters
        ----------
        regions : iterable of tuple
            Each entry may be:

            * ``(t_start, t_end)``
            * ``(t_start, t_end, label)``
            * ``(t_start, t_end, label, color)``   *color* is a hex string

        Example
        -------
        ::

            viewer.add_roi_annotations([
                (10.5, 14.2, 'Spike cluster', '#e74c3c'),
                (45.0, 48.5, 'Artefact',      '#f39c12'),
            ])
        """
        self._roi_panel.load_roi_annotations(regions)
