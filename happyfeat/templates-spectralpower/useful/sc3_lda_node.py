import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import cross_val_score, StratifiedKFold,cross_validate
from joblib import load
from timeflux.core.exceptions import WorkerInterrupt, WorkerLoadError
import os
import sys


class Prefitted_LDA(BaseEstimator, ClassifierMixin):
    def __init__(self, path):

        self.path = self._find_path(path)
        try:
            self.model= load(self.path)
        except IOError as e:
            raise WorkerInterrupt(e)

          
    def fit(self, X, y=None):
    # No fitting needed, as this is a pre-fitted model
        return self
    def fit_predict(self, X,y=None):
        return self.model.predict(X[0])


    def _find_path(self, path):
        path = os.path.normpath(path)
        if os.path.isabs(path):
            if os.path.isfile(path):
                return path
        else:
            for base in sys.path:
                full_path = os.path.join(base, path)
                if os.path.isfile(full_path):
                    return full_path
        raise WorkerLoadError(f"File `{path}` could not be found in the search path.")

