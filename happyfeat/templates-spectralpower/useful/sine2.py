import numpy as np
import time
from timeflux.core.node import Node

class AlternatingSignals(Node):
    """Generate alternating sinusoidal signals across multiple channels.

    Attributes:
        o (Port): Final signal output, provides DataFrame and meta.

    Args:
        channels (int): Number of channels.
        frequencies_1 (list of list): Cycles per second for each wave in each channel for the first signal set.
        amplitudes_1 (list of list): Signal amplitude for each wave in each channel for the first signal set.
        frequencies_2 (list of list): Cycles per second for each wave in each channel for the second signal set.
        amplitudes_2 (list of list): Signal amplitude for each wave in each channel for the second signal set.
        resolution (int): Points per second. Default: ``200``.
        names (list): Signal names for each channel. Default: ``None``.
    """

    def __init__(self, channels=5, 
                 frequencies_1=[[1, 2]] * 5, amplitudes_1=[[1, 1]] * 5, 
                 frequencies_2=[[3, 4]] * 5, amplitudes_2=[[0.5, 0.5]] * 5, 
                 resolution=500, names=None):
        self._channels = channels
        self._frequencies_1 = frequencies_1
        self._amplitudes_1 = amplitudes_1
        self._frequencies_2 = frequencies_2
        self._amplitudes_2 = amplitudes_2
        self._resolution = int(resolution)
        self._names = names if names else [f"signal_{i}" for i in range(channels)]
        self._meta = {"rate": self._resolution}
        self._radians_1 = [[0] * len(f) for f in frequencies_1]
        self._radians_2 = [[0] * len(f) for f in frequencies_2]
        self._now = time.time()
        self._toggle = True

    def _generate_signals(self, frequencies, amplitudes, radians, elapsed, points, timestamps):
        final_signals = np.zeros((len(timestamps), self._channels))
        for channel in range(self._channels):
            signals = np.zeros((len(timestamps), len(frequencies[channel])))
            for index in range(len(frequencies[channel])):
                cycles = frequencies[channel][index] * elapsed
                values = np.linspace(radians[channel][index], np.pi * 2 * cycles + radians[channel][index], points)
                signals[:, index] = np.sin(values[:-1]) * amplitudes[channel][index]
                radians[channel][index] = values[-1]
            final_signals[:, channel] = signals.sum(axis=1) / len(frequencies[channel])
        return final_signals

    def update(self):
        now = time.time()
        elapsed = now - self._now
        points = int(elapsed * self._resolution) + 1
        timestamps = np.linspace(int(self._now * 1e6), int(now * 1e6), points, False, dtype="datetime64[us]")[1:]

        if self._toggle:
            final_signals = self._generate_signals(self._frequencies_1, self._amplitudes_1, self._radians_1, elapsed, points, timestamps)
        else:
            final_signals = self._generate_signals(self._frequencies_2, self._amplitudes_2, self._radians_2, elapsed, points, timestamps)

        self._toggle = not self._toggle
        self._now = now

        self.o.set(final_signals, timestamps, names=self._names, meta=self._meta)


