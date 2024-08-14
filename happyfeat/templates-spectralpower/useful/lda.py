import pandas as pd
import numpy as np
import os
import xarray
from timeflux.core.node import Node
from timeflux.core.exceptions import WorkerInterrupt
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.model_selection import cross_val_score
import joblib
class LDA_NODE(Node):
    def __init__(self,path,filename, cv=3):
        """
        Initialize the LDA node.

        Parameters
        ----------
        cv : int
            Number of cross-validation folds.
        """
        self.cv = cv
        self.model = LDA()
        self.trained = False
        self.data = []
        self.labels = []
        self.path=path
        self.filename=filename

    def update(self):
        if self.ports is not None:
            inputs = []

            # Collect input ports to avoid modifying the dictionary during iteration
            for name, port in self.ports.items():
                if not name.startswith("i"):
                    continue
                inputs.append((name, port))

            for name, port in inputs:
                if port.data is not None and port.meta is not None:
                    try:
                        print(f"Processing port: {name}")
                        # Extract data and labels from input port
                        data = port.data.dropna(dim='time')
                        labels = port.meta['label']

                        # Collect data and labels
                        print(type(data))
                        self.data.append(data)
                        self.labels.append(labels)

                    except Exception as e:
                        self.logger.error(f"Error processing port {name}: {e}")
                        raise WorkerInterrupt(e)

            if self.data and self.labels:
                # Concatenate all collected data and labels
                # data = pd.concat(self.data)
                data= xarray.concat(self.data,dim='time')
                labels = np.concatenate(self.labels)
                data_np=data.values


                # Convert labels to a pandas Series to use .unique()
                labels_series = pd.Series(labels)

                if len(labels_series.unique()) == 2:
                    print("Performing cross-validation")
                    # Perform cross-validation
                    scores = cross_val_score(self.model, data, labels, cv=self.cv)
                    mean_accuracy = scores.mean()

                    print("Training the model")

                    self.model.fit(data_np, labels)
                    self.trained = True
                    model_filename=self.filename+'_fitted_model.pkl'
                    model_path= os.path.join(self.path, model_filename)
                    # Output the model weights
                    weights = pd.DataFrame(self.model.coef_)
                    joblib.dump(self.model, model_path)
                    self.o.data = weights
                    self.o.meta['weights'] = weights.values.tolist()

                    # Output the model metrics
                    self.o.meta['metrics'] = {
                        'cv_scores': scores.tolist(),
                        'mean_accuracy': mean_accuracy
                    }
                    print('the mean accuracy',mean_accuracy)
                    print('the cv scoreis',scores.tolist())
                    raise WorkerInterrupt("Training end and saving model")
