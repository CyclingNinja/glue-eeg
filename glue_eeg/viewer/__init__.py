from .data_viewer import EDFViewer

__all__ = ['EDFViewer']


def setup():
    from glue_qt.config import qt_client
    qt_client.add(EDFViewer)
