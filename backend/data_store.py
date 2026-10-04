"""
In-memory application state for the currently loaded dataset.

This is a small single-user local application (per the project brief it
runs locally in VS Code), so a process-wide store is sufficient - no
multi-user session handling is required. All dataframes and the trained
model results live here for the lifetime of the Flask process.
"""
import threading


class DataStore:
    """Holds the raw dataframe, the cleaned dataframe, and cached results."""

    def __init__(self):
        self.lock = threading.Lock()
        self.raw_df = None          # pandas.DataFrame as uploaded
        self.clean_df = None        # pandas.DataFrame after cleaning pipeline
        self.source_name = None     # original filename
        self.cleaning_log = []      # list of str describing cleaning steps
        self.model_results = None   # dict of last model training run

    def reset(self):
        with self.lock:
            self.raw_df = None
            self.clean_df = None
            self.source_name = None
            self.cleaning_log = []
            self.model_results = None

    def has_data(self):
        return self.raw_df is not None

    def has_clean_data(self):
        return self.clean_df is not None

    def active_df(self):
        """The dataframe analysis endpoints should operate on: cleaned if
        available, otherwise the raw upload."""
        return self.clean_df if self.clean_df is not None else self.raw_df


# Single process-wide instance imported by routes.py
store = DataStore()
