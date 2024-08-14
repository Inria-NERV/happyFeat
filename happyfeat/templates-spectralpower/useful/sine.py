import numpy as np
import time
from timeflux.core.node import Node

import numpy as np
import time
import pandas as pd
from timeflux.core.node import Node

class Additive(Node):
    """Generate multiple sinusoidal signals across multiple channels and sum them together.

    Attributes:
        o (Port): Final signal output, provides DataFrame and meta.
        o_signals (Port): Individual signals output, provides DataFrame and meta.

    Args:
        channels (int): Number of channels.
        frequencies (list of list): Cycles per second for each wave in each channel.
        amplitudes (list of list): Signal amplitude for each wave in each channel.
        resolution (int): Points per second. Default: ``200``.
        names (list): Signal names for each channel. Default: ``None``.

    Example:
        .. literalinclude:: /../examples/additive.yaml
           :language: yaml
    """

    def __init__(self, channels=5, frequencies=[[1, 2]] * 5, amplitudes=[[1, 1]] * 5, resolution=200, names=None):
        if any(len(f) != len(a) for f, a in zip(frequencies, amplitudes)):
            raise ValueError("The frequencies and amplitudes arrays must be of equal length for each channel")
        self._channels = channels
        self._frequencies = frequencies
        self._amplitudes = amplitudes
        self._resolution = int(resolution)
        self._names = names if names else [f"signal_{i}" for i in range(channels)]
        self._meta = {"rate": self._resolution}
        self._radians = [[0] * len(f) for f in frequencies]
        self._now = time.time()

    def update(self):
        now = time.time()
        elapsed = now - self._now
        points = int(elapsed * self._resolution) + 1
        timestamps = np.linspace(int(self._now * 1e6), int(now * 1e6), points, False, dtype="datetime64[us]")[1:]
        final_signals = np.zeros((len(timestamps), self._channels))
        individual_signals = []

        for channel in range(self._channels):
            signals = np.zeros((len(timestamps), len(self._frequencies[channel])))
            for index in range(len(self._frequencies[channel])):
                cycles = self._frequencies[channel][index] * elapsed
                values = np.linspace(self._radians[channel][index], np.pi * 2 * cycles + self._radians[channel][index], points)
                signals[:, index] = np.sin(values[:-1]) * self._amplitudes[channel][index]
                self._radians[channel][index] = values[-1]
            final_signals[:, channel] = signals.sum(axis=1) / len(self._frequencies[channel])
            individual_signals.append(signals)

        self._now = now

        # Reshape individual_signals to 2D
        individual_signals = np.concatenate(individual_signals, axis=1)

        self.o.set(final_signals, timestamps, names=self._names)
        self.o_signals.set(individual_signals, timestamps, meta=self._meta)

# Example usage
# additive = Additive(channels=3, frequencies=[[1, 2], [2, 3], [3, 4]], amplitudes=[[1, 0.5], [0.8, 0.3], [0.6, 0.2]])

