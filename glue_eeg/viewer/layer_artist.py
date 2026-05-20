import numpy as np
from glue.core import Subset
from glue.utils import defer_draw
from glue.viewers.matplotlib.layer_artist import MatplotlibLayerArtist

from .state import EDFLayerState

__all__ = ['EDFLayerArtist']

# Downsample if more than this many points would be rendered per channel.
_MAX_POINTS_PER_CHANNEL = 20_000


class EDFLayerArtist(MatplotlibLayerArtist):

    _layer_state_cls = EDFLayerState

    def __init__(self, axes, viewer_state, layer_state=None, layer=None):
        super().__init__(axes, viewer_state, layer_state=layer_state, layer=layer)
        self._channel_lines: dict[str, object] = {}  # label -> Line2D

        self._viewer_state.add_global_callback(self._update_data)
        self.state.add_global_callback(self._update_data)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _data_obj(self):
        """Return the underlying Data (unwrapping a Subset if needed)."""
        layer = self.state.layer
        if layer is None:
            return None
        return layer.data if isinstance(layer, Subset) else layer

    def _channel_ids(self):
        data = self._data_obj()
        if data is None:
            return []
        return [cid for cid in data.main_components if cid.label != 'time']

    def _visible_slice(self, time: np.ndarray):
        """Return an index array for the currently visible time window."""
        t_min = self._viewer_state.x_min
        t_max = self._viewer_state.x_max
        if t_min is None or t_max is None:
            idx = np.arange(len(time))
        else:
            idx = np.where((time >= t_min) & (time <= t_max))[0]

        # Decimate to avoid over-rendering very long windows
        if len(idx) > _MAX_POINTS_PER_CHANNEL:
            step = int(np.ceil(len(idx) / _MAX_POINTS_PER_CHANNEL))
            idx = idx[::step]
        return idx

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    @defer_draw
    def _update_data(self, **kwargs):
        if not self.enabled or self.state.layer is None:
            return

        data = self._data_obj()
        if data is None:
            self.clear()
            return

        try:
            time = data['time']
        except Exception:
            self.clear()
            return

        idx = self._visible_slice(time)
        if len(idx) == 0:
            self.clear()
            return

        t_visible = time[idx]
        channel_ids = self._channel_ids()
        spacing = self._viewer_state.channel_spacing
        scale = self.state.amplitude_scale
        color = self.state.color
        alpha = self.state.alpha
        visible = self.state.visible

        self._remove_stale_lines(channel_ids)

        for i, cid in enumerate(channel_ids):
            try:
                signal_full = self.state.layer[cid]
            except Exception:
                continue

            signal = signal_full[idx]
            rms = float(np.nanstd(signal))
            if rms < 1e-10:
                rms = 1.0
            y = (signal / rms) * scale + (-i * spacing)

            if cid.label not in self._channel_lines:
                (line,) = self.axes.plot([], [], lw=0.7, color=color,
                                         alpha=alpha, rasterized=True)
                self._channel_lines[cid.label] = line
                self.mpl_artists.append(line)

            line = self._channel_lines[cid.label]
            line.set_data(t_visible, y)
            line.set_color(color)
            line.set_alpha(alpha)
            line.set_visible(visible)

        self._refresh_y_axis(channel_ids, spacing)
        self.redraw()

    def _remove_stale_lines(self, channel_ids):
        """Remove line artists for channels no longer present in the data."""
        current_labels = {cid.label for cid in channel_ids}
        for label in list(self._channel_lines):
            if label not in current_labels:
                line = self._channel_lines.pop(label)
                try:
                    line.remove()
                except Exception:
                    pass
                if line in self.mpl_artists:
                    self.mpl_artists.remove(line)

    def _refresh_y_axis(self, channel_ids, spacing):
        """Keep y-tick labels aligned with channel offsets."""
        positions = [-i * spacing for i in range(len(channel_ids))]
        labels = [cid.label for cid in channel_ids]
        self.axes.set_yticks(positions)
        self.axes.set_yticklabels(labels, fontsize=7)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @defer_draw
    def clear(self):
        for line in self._channel_lines.values():
            line.set_visible(False)
        super().clear()

    def remove(self):
        for line in self._channel_lines.values():
            try:
                line.remove()
            except Exception:
                pass
        self._channel_lines.clear()
        super().remove()

    @defer_draw
    def update(self):
        self._update_data(force=True)
