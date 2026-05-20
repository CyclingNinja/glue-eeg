def setup():
    from .data_factory import edf_reader  # noqa: F401 — registers @data_factory
    from .viewer import setup as viewer_setup
    viewer_setup()
