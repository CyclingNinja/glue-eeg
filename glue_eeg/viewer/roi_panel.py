import weakref

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt

__all__ = ['ROIPanel']


def _fmt_time(seconds: float) -> str:
    mins, secs = divmod(seconds, 60)
    return f'{int(mins):02d}:{secs:05.2f}'


class ROIItem(QtWidgets.QListWidgetItem):
    """A single annotated time-range entry in the ROI list."""

    def __init__(self, t_start: float, t_end: float, label: str, color: str):
        display = f'{label}  [{_fmt_time(t_start)} – {_fmt_time(t_end)}]'
        super().__init__(display)
        self.t_start = t_start
        self.t_end = t_end
        self.label = label
        self.color = color
        self._span_patch = None  # matplotlib Polygon (axvspan)

        pix = QtGui.QPixmap(12, 16)
        pix.fill(QtGui.QColor(color))
        self.setIcon(QtGui.QIcon(pix))
        self.setToolTip(
            f'<b>{label}</b><br>'
            f'Start: {_fmt_time(t_start)}<br>'
            f'End: {_fmt_time(t_end)}<br>'
            f'Duration: {_fmt_time(t_end - t_start)}'
        )


class ROIPanel(QtWidgets.QWidget):
    """
    Side panel listing annotated regions of interest.

    External services populate it via :meth:`load_roi_annotations`.
    Users can also add regions interactively through the viewer's
    range-select tool, then clicking *Add ROI*.  Double-clicking any
    item scrolls the viewer to that region.

    Signals
    -------
    roi_added(t_start, t_end, label, color)
    roi_removed(index)
    """

    roi_added = QtCore.Signal(float, float, str, str)
    roi_removed = QtCore.Signal(int)

    def __init__(self, viewer):
        super().__init__()
        self._viewer = weakref.ref(viewer)
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        header = QtWidgets.QLabel('<b>Regions of Interest</b>')
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        self._list = QtWidgets.QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._list)

        layout.addLayout(self._build_button_row())
        self.setMinimumWidth(220)

    def _build_button_row(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()

        self._btn_add = QtWidgets.QPushButton('Add ROI')
        self._btn_add.setToolTip('Add current x-range selection as a region of interest')
        self._btn_add.clicked.connect(self._on_add_roi)
        row.addWidget(self._btn_add)

        self._btn_goto = QtWidgets.QPushButton('Go To')
        self._btn_goto.setToolTip('Navigate to selected region')
        self._btn_goto.clicked.connect(self._on_goto)
        row.addWidget(self._btn_goto)

        self._btn_remove = QtWidgets.QPushButton('Remove')
        self._btn_remove.setToolTip('Remove selected regions')
        self._btn_remove.clicked.connect(self._on_remove)
        row.addWidget(self._btn_remove)

        btn_clear = QtWidgets.QPushButton('Clear All')
        btn_clear.clicked.connect(self.clear)
        row.addWidget(btn_clear)

        return row

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_roi(self, t_start: float, t_end: float,
                label: str = 'Region', color: str = '#e74c3c') -> ROIItem:
        """
        Add a single region of interest.

        Parameters
        ----------
        t_start, t_end : float
            Timestamps in seconds from recording start.
        label : str
            Human-readable name shown in the list.
        color : str
            Hex colour string used for the swatch icon and plot span.
        """
        item = ROIItem(t_start, t_end, label, color)
        self._list.addItem(item)
        item._span_patch = self._draw_span(t_start, t_end, color)
        self.roi_added.emit(t_start, t_end, label, color)
        return item

    def load_roi_annotations(self, regions) -> None:
        """
        Bulk-load regions from an external service.

        Parameters
        ----------
        regions : iterable of tuple
            Each entry may be:

            * ``(t_start, t_end)``
            * ``(t_start, t_end, label)``
            * ``(t_start, t_end, label, color)``
        """
        for region in regions:
            t_start = float(region[0])
            t_end = float(region[1])
            label = region[2] if len(region) > 2 else _fmt_time(t_start)
            color = region[3] if len(region) > 3 else '#e74c3c'
            self.add_roi(t_start, t_end, label, color)

    def clear(self) -> None:
        """Remove all regions of interest."""
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item:
                self._remove_span(item)
        self._list.clear()
        self._redraw_canvas()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate_to(self, item: ROIItem) -> None:
        """Centre the viewer's time window on *item*."""
        viewer = self._viewer()
        if viewer is None:
            return

        duration = viewer.state.window_duration
        center = (item.t_start + item.t_end) / 2.0
        t_min = center - duration / 2.0
        t_max = t_min + duration

        if viewer.state.reference_data is not None:
            total = float(viewer.state.reference_data['time'][-1])
            if t_min < 0.0:
                t_min, t_max = 0.0, duration
            elif t_max > total:
                t_max = total
                t_min = max(0.0, total - duration)

        from echo import delay_callback
        with delay_callback(viewer.state, 'x_min', 'x_max'):
            viewer.state.x_min = t_min
            viewer.state.x_max = t_max

        viewer._sync_scrollbar_to_state()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_add_roi(self) -> None:
        viewer = self._viewer()
        if viewer is None:
            return
        roi_range = getattr(viewer, '_last_roi_range', None)
        if roi_range is None:
            return
        t_start, t_end = roi_range
        default_label = f'ROI {self._list.count() + 1}'
        label, ok = QtWidgets.QInputDialog.getText(
            self, 'Add Region of Interest', 'Label:', text=default_label
        )
        if ok and label.strip():
            self.add_roi(t_start, t_end, label.strip())

    def _on_item_double_clicked(self, item: ROIItem) -> None:
        self.navigate_to(item)

    def _on_goto(self) -> None:
        selected = self._list.selectedItems()
        if selected:
            self.navigate_to(selected[0])

    def _on_remove(self) -> None:
        for item in self._list.selectedItems():
            row = self._list.row(item)
            self._remove_span(item)
            self._list.takeItem(row)
            self.roi_removed.emit(row)
        self._redraw_canvas()

    # ------------------------------------------------------------------
    # Plot helpers
    # ------------------------------------------------------------------

    def _draw_span(self, t_start: float, t_end: float, color: str):
        viewer = self._viewer()
        if viewer is None:
            return None
        span = viewer.axes.axvspan(t_start, t_end, alpha=0.15,
                                   color=color, zorder=0)
        self._redraw_canvas()
        return span

    def _remove_span(self, item: ROIItem) -> None:
        if item._span_patch is not None:
            try:
                item._span_patch.remove()
            except Exception:
                pass
            item._span_patch = None

    def _redraw_canvas(self) -> None:
        viewer = self._viewer()
        if viewer is not None:
            viewer.axes.figure.canvas.draw_idle()
