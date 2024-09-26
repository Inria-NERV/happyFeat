import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.model_selection import cross_val_score, StratifiedKFold,cross_validate

class CustomLDA(BaseEstimator, ClassifierMixin):
    def __init__(self, cv_splits=2):
        self.lda = LinearDiscriminantAnalysis()
        self.cv_splits = cv_splits
        self.cv_scores = None
        self.output= None

    def fit(self, X, y):
        # Perform cross-validation
        cv = StratifiedKFold(n_splits=self.cv_splits)
        #self.cv_scores = cross_val_score(self.lda, X, y, cv=cv)
        self.output = cross_validate(self.lda, X, y, cv=cv,return_estimator=True)
        self.cv_scores=self.output['test_score']
        print(self.cv_scores)
        self.lda=self.output['estimator'][0]
        print(self.lda)
        # Fit the LDA model on the whole dataset
        self.lda.fit(X, y)
        return self
    
    def predict(self, X):

        return self.lda.predict(X)
    
    def get_cv_scores(self):
        return self.cv_scores
