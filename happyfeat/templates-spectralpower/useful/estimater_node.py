import numpy as np
import xarray as xr
from timeflux.core.node import Node
from sklearn.utils.validation import check_array

class Features(Node):
    def __init__(self):
        super().__init__()
    def transform(self, X):
        X = check_array(X, allow_nd=True)
        shapeX = X.shape
        print(shapeX)
        if len(shapeX) == 3:
            Nt, Ns, Ne = shapeX
        else:
            raise ValueError("X.shape should be (n_trials, n_samples, n_electrodes).")
        
        features = X.reshape(Nt, Ne)
        return(features)


    def update(self):
        if self.i.ready():
            if self.i.data is not None:
                data = self.i.data
                #data_values = data.values  # Assuming data is an xarray DataArray with shape (n_trials, n_samples, n_channels)
                features = self.transform(data)

                getattr(self, "o").data = features
                getattr(self,"o").meta = self.i.meta



