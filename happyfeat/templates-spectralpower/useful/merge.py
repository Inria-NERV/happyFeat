"""Illustrates dynamic inputs and outputs."""

import random
from timeflux.core.node import Node
import pandas as pd 




class Merge(Node):

     
    # def update(self):
    #     # self._send()
    #     if self.ports is not None:
    #         for name, port in self.ports.items():
                
    #             if not name.startswith("i"):
    #                 continue
    #             key = name[1:]
    #             if port.data is not None:
    #                 print(key)
    #                 dst_port = getattr(self, "o" + key)
    #                 dst_port.data = port.data
    #                 dst_port.meta = port.meta

    def __init__(self, axis=1, **kwargs):
        self._axis = axis
        self._kwargs = kwargs
    def update(self):
        ports = list(self.iterate("i*"))
        i_data = [port.data for (name, _, port) in ports if port.data is not None]
        i_meta=[pd.DataFrame([port.meta['epoch']['context']])for (name, _, port) in ports if port.data is not None]
        if i_data:
            self.o.data = pd.concat(i_data, axis=self._axis, **self._kwargs)
            self.o.meta = pd.concat(i_meta, axis=self._axis, **self._kwargs)