import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import cross_val_score, StratifiedKFold,cross_validate
from joblib import load
from timeflux.core.exceptions import WorkerInterrupt, WorkerLoadError
import os
import sys
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
import joblib
class ML_LDA(BaseEstimator, ClassifierMixin):
    def __init__(self):
        self.model = LDA()

          
    def fit(self, X, y=None):
        print(X)
        print(X[0].shape)
        print(X[1].shape)
        self.model.fit(X[0],X[1])
        joblib.dump(self.model, 'fitted_model.pkl')
        return self

    def fit_predict(self, X, y=None):
        self.fit(X)
        return self



