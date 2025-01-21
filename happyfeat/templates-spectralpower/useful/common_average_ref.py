from timeflux.core.node import Node
import pandas as pd
import numpy as np

class CommonAvgRefNode(Node):
    def __init__(self):
        super().__init__()

    def update(self):
        # When we have not received data, there is nothing to do
        if not self.i.ready():
            return

        # copy the meta
        self.o = self.i

        # For each sample (=row), substract the average to all channels
        self.o.data = self.i.data.sub(self.i.data.mean(axis=1), axis=0)

        return True
