from timeflux.core.node import Node
import pandas as pd

class DynamicOutputNode(Node):
    def __init__(self):
        super().__init__()
        self._input_ports_data = []
        self._input_ports_names=[]

    def update(self):
        # Check for new inputs and dynamically add them if not already in _input_ports
        for name, _, port in self.iterate("i_*"):
            if port.ready() and name not in self._input_ports_names:
                self._input_ports_data.append(port.data)
                self._input_ports_names.append(name)
        # Output each input port sequentially until none are left
        if self._input_ports_data:
            port_data = self._input_ports_data.pop(0)  # Get the first port in the list
            getattr(self, "o").data = port_data # Output the data from this port
            if len(self._input_ports_data)==0:
                getattr(self, "o").meta = {"info": "last one"}
            return True  # Indicate that the node should continue executing

        return False  # Indicate that there are no more inputs to process