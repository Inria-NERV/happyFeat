import numpy as np
from timeflux.core.node import Node


import numpy as np
import pandas as pd
import json
import xarray as xr
from timeflux.core.node import Node
from timeflux.core.exceptions import WorkerInterrupt
from timeflux.helpers.port import match_events



class Epoch(Node):
    """Event-triggered epoching.

    This node continuously buffers a small amount of data (of a duration of ``before`` seconds) from the default input stream.
    When it detects a marker matching the ``event_trigger`` in the ``label`` column of the event input stream, it starts accumulating data for ``after`` seconds.
    It then sends the epoched data to an output stream, and sets the metadata to a dictionary containing the triggering marker and optional event data.
    Multiple, overlapping epochs are authorized. Each concurrent epoch is assigned its own `Port`. For convenience, the first epoch is bound to the default output, so you can avoid enumerating all output ports if you expects only one epoch.

    Attributes:
        i (Port): Default data input, expects DataFrame.
        i_events (Port): Event input, expects DataFrame.
        o (Port): Default output, provides DataFrame and meta.
        o_* (Port): Dynamic outputs, provide DataFrame and meta.

    Args:
        event_trigger (string): The marker name.
        before (float): Length before onset, in seconds.
        after (float): Length after onset, in seconds.

    Example:
        .. literalinclude:: /../examples/epoch.yaml
           :language: yaml

    """

    def __init__(self, event_trigger, before=20.0, after=0.6):
        self._event_trigger = event_trigger
        self._before = pd.Timedelta(seconds=before)
        self._after = pd.Timedelta(seconds=after)
        self._buffer = None
        self._epochs = []

    def update(self):
        # Append to main buffer

        if self.i.data is not None:
            if not self.i.data.empty:
                if self._buffer is None:
                    self._buffer = self.i.data
                else:
                    self._buffer = pd.concat([self._buffer, self.i.data])


        # Detect onset
        matches = match_events(self.i_events, self._event_trigger)
        if matches is not None:
            for index, row in matches.iterrows():
                # Start a new epoch
                low = index - self._before
                high = index + self._after

                if self._buffer is not None:
                    if not self._buffer.index.is_monotonic_increasing:
                        self.logger.warning("Index must be monotonic. Skipping epoch.")
                        return
                    try:
                        context = json.loads(row["data"])
                    except json.JSONDecodeError:
                        context = row["data"]
                    except TypeError:
                        context = {}
                    print("buffer",self._buffer)
                    self._epochs.append(
                        {
                            "data": self._buffer[low:high],
                            "meta": {
                                "onset": index,
                                "context": context,
                                "before": self._before.total_seconds(),
                                "after": self._after.total_seconds(),
                            },
                        }
                    )


        # Trim main buffer
        if self._buffer is not None:
            low = self._buffer.index[-1] - self._before
            self._buffer = self._buffer[low:]
        print("epoch",self._epochs)
        # Update epochs
        if self._epochs and self.i.ready():
            complete = 0
            for epoch in self._epochs:
                high = epoch["meta"]["onset"] + self._after
                last = self.i.data.index[-1]
                if epoch["data"].empty:
                    low = epoch["meta"]["onset"] - self._before
                    mask = (self.i.data.index >= low) & (self.i.data.index <= high)
                else:
                    low = epoch["data"].index[-1]
                    mask = (self.i.data.index > low) & (self.i.data.index <= high)
                # Append
                epoch["data"] = pd.concat([epoch["data"], self.i.data[mask]])

                # Send if we have enough data
                if last >= high:
                    o = getattr(self, "o_" + str(complete))
                    o.data = epoch["data"]
                    o.meta = {"epoch": epoch["meta"]}
                    complete += 1
            if complete > 0:
                del self._epochs[:complete]  # Unqueue
                self.o = self.o_0  # Bind default output to the first epoch

