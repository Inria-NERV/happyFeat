import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_array

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_array

class EEGFeatures(BaseEstimator, TransformerMixin):

    def fit(self, X, y=None):
        return self

    def transform(self, X,y):
        print(X)
        print(y)
        # X = check_array(X, allow_nd=True)
        # shapeX = X.shape

        # if len(shapeX) == 3:
        #     Nt, Ns, Ne = shapeX
        # else:
        #     raise ValueError("X.shape should be (n_trials, n_samples, n_electrodes).")
        
        # features = X.reshape(Nt,Ne)
        features= np.vstack(X)
        labels=np.hstack(y)
        return features,labels

    def fit_transform(self, X, y=None):
        """
        Parameters
        ----------
        X : ndarray, shape (n_trials,  n_samples, n_channels)
            Data to extract features from
        y : ndarray, shape (n_trials,) | None, optional
            labels corresponding to each trial, not used (mentioned for sklearn comp)
        Returns
        -------
        X : ndarray, shape (n_trials, n_features)
            Temporal features
        """
        self.fit(X, y)
        return self.transform(X,y)
    @staticmethod
    def _zero_crossing_rate(x):
        return len(np.where(np.diff(np.sign(x)))[0]) / len(x)
