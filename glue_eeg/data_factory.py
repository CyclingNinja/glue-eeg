import os

import numpy as np

from glue.config import data_factory
from glue.core import Data

__all__ = ['edf_reader']


def is_edf(filename, **kwargs):
    return filename.lower().endswith(('.edf', '.edf+'))


@data_factory(label='EDF file', identifier=is_edf, priority=100)
def edf_reader(filename):
    """
    Read an EDF / EDF+ file into a Glue Data object.

    Each signal channel becomes a 1-D Component.  A ``time`` Component
    (in seconds from recording start) is added as the shared coordinate.
    Channels with a different sample rate than the majority are resampled
    via linear interpolation to a common length.

    Requires ``pyedflib`` (``pip install pyedflib``).
    """
    try:
        import pyedflib
    except ImportError as exc:
        raise ImportError(
            "pyedflib is required to read EDF files. "
            "Install it with:  pip install pyedflib"
        ) from exc

    with pyedflib.EdfReader(filename) as f:
        n_channels = f.signals_in_file
        labels = f.getSignalLabels()
        sample_freqs = f.getSampleFrequencies()
        n_samples_per_channel = f.getNSamples()

        # Reference: channel with the most samples (usually the EEG channels)
        ref_n = int(max(n_samples_per_channel))
        ref_freq = float(sample_freqs[np.argmax(n_samples_per_channel)])
        total_duration = ref_n / ref_freq

        signals: dict[str, np.ndarray] = {}
        for i in range(n_channels):
            raw = f.readSignal(i).astype(np.float32)
            n_ch = len(raw)
            if n_ch != ref_n:
                raw = np.interp(
                    np.linspace(0.0, n_ch - 1, ref_n),
                    np.arange(n_ch),
                    raw,
                ).astype(np.float32)
            # Deduplicate label if the file contains repeated channel names
            label = labels[i]
            if label in signals:
                label = f'{label}_{i}'
            signals[label] = raw

        meta = {
            'sample_rate': ref_freq,
            'total_duration': total_duration,
            'channel_labels': list(signals.keys()),
            'patient_id': f.getPatientCode(),
            'recording_info': f.getRecordingAdditional(),
            'start_datetime': str(f.getStartdatetime()),
        }

    data = Data(label=os.path.basename(filename))
    data['time'] = np.linspace(0.0, total_duration, ref_n, endpoint=False,
                               dtype=np.float64)
    for label, signal in signals.items():
        data[label] = signal

    data.meta.update(meta)
    return [data]
