import pandas as pd
import numpy as np
import os
import xarray
from timeflux.core.node import Node
from timeflux.core.exceptions import WorkerInterrupt
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.model_selection import cross_val_score
import joblib
from sklearn import svm
from sklearn.preprocessing import StandardScaler
from sklearn.utils import shuffle
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, accuracy_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
class LDA_NODE(Node):
    def __init__(self,path, cv=3):
        """
        Initialize the LDA node.

        Parameters
        ----------
        cv : int
            Number of cross-validation folds.
        """
        self.cv = cv
        self.model = LDA(solver="eigen", shrinkage="auto")
        self.trained = False
        self.data = []
        self.labels = []
        self.path=path


    def update(self):
        print("le cv est",self.cv)
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

                # Convert text labels to numeric values
                labels = np.where(labels == 'MI', 0, 1)  # Assuming 'MI' should be 0 and the other class should be 1
                # Convert labels to a pandas Series to use .unique()
                labels_series = pd.Series(labels)
                print("data",data_np)
                if len(labels_series.unique()) == 2:
                    print("Performing cross-validation")
                    data_np, labels = shuffle(data_np, labels, random_state=42)

                    print("Performing manual cross-validation")
                    kfold = KFold(n_splits=self.cv)
                    fold_scores = []
                    specificity_scores=[]
                    sensitivity_scores=[]
                    # Manually perform cross-validation
                    for fold, (train_index, test_index) in enumerate(kfold.split(data_np)):
                        print(f"Fold {fold + 1}")

                        # Split the data into training and test sets for this fold
                        X_train, X_test = data_np[train_index], data_np[test_index]
                        y_train, y_test = labels[train_index], labels[test_index]
                        self.plot_eigenvalues_and_variance(X_train, y_train)
                        print("x_train",type(X_train),np.shape(X_train))
                        # Train the model on the training set
                        # self.model.fit(X_train, y_train)
                        sc = StandardScaler()
                        X_train = sc.fit_transform(X_train)
                        X_test = sc.transform(X_test)
                        X_train = self.model.fit_transform(X_train, y_train)
                        X_test = self.model.transform(X_test)
                        classifier=LogisticRegression(random_state=0)
                        #classifier = svm.SVC(kernel = 'rbf')
                        # classifier= RandomForestClassifier(max_depth=2,random_state=0)
                        classifier.fit(X_train, y_train)
                        y_pred = classifier.predict(X_test)
                        cm = confusion_matrix(y_test, y_pred)
                        roc_auc=roc_auc_score(y_test, y_pred, average=None)

                        if len(cm.shape) > 1:
                            if ((cm[0,0]+cm[1,0])>0):
                                sensitivity_scores.append(cm[0,0]/(cm[1,0]+cm[0,0]))
                        
                            if ((cm[1,0]+cm[1,1])>0):
                                specificity_scores.append( cm[1,1]/(cm[1,0]+cm[1,1]))
                        else:
                            sensitivity_scores.append(cm[1])
                            specificity_scores.append(cm[1])




                        print("confusion matrix",cm)
                        print("roc_AUC",roc_auc)
                        # Evaluate the model on the test set
                        score = classifier.score(X_test, y_test)
                        fold_scores.append(score)
                        print(f"Fold {fold + 1} accuracy: {score:.4f}")

                    # Calculate mean accuracy across all folds
                    mean_accuracy = np.mean(fold_scores)
                    mean_sensitivity=np.mean(sensitivity_scores)
                    mean_specificity=np.mean(specificity_scores)


                    # # Perform cross-validation
                    # scores = cross_val_score(self.model, data_np, labels, cv=self.cv)
                    # mean_accuracy = scores.mean()

                    # print("Training the model")
                    # print('data',data_np,'labels',labels)
                    # self.model.fit(data_np, labels)


                    ## TESTING

                    # Test the model on the same entire dataset (train accuracy)
                    print("""
                          ###################################
                          Testing on the entire dataset to check if accuracy is 1""")
                    lda=LDA()
                    sc = StandardScaler()
                    data_np = sc.fit_transform(data_np)
                    data_np = lda.fit_transform(data_np, labels)
                    classifier = LogisticRegression(random_state = 0)
                    classifier.fit(data_np, labels)
                    y_pred_train = classifier.predict(data_np)
                    train_accuracy = accuracy_score(labels, y_pred_train)
                    print ("Number of mislabeled points : %d"%(labels != y_pred_train).sum())
                    print(f"Train accuracy on the entire dataset: {train_accuracy:.4f}")
                    if train_accuracy == 1:
                        print("The model perfectly fits the training data (accuracy = 1)")

                    self.visualize_lda(data_np,labels)


                    self.trained = True
                    # Output the model weights
                    weights = pd.DataFrame(self.model.coef_)
                    joblib.dump(self.model, self.path)
                    self.o.data = weights
                    self.o.meta['weights'] = weights.values.tolist()

                    # Output the model metrics
                    self.o.meta['metrics'] = {
                        'cv_scores': fold_scores,
                        'mean_accuracy': mean_accuracy,
                        'specificity_score': mean_specificity,
                        'sensitivity_score': mean_sensitivity

                    }
                    print('the mean accuracy',mean_accuracy)
                    print('the mean sensitivity', mean_sensitivity)
                    print('the mean specificity', mean_specificity)
                    print('the cv scores are',fold_scores)
                    raise WorkerInterrupt("Training end and saving model")
    def visualize_lda(self, data, labels):

        lda = LDA(n_components=1)  # Request only 1 component, since there are 2 classes
        X_r_lda = lda.fit_transform(data, labels)

        target_names = ['MI', 'REST']  
        colors = ["navy", "turquoise"]

        plt.figure()
        if X_r_lda.shape[1] == 1:
            # If LDA only has 1 component, plot it as a line or scatter plot against samples
            for color, i, target_name in zip(colors, [0, 1], target_names):
                plt.scatter(np.arange(X_r_lda[labels == i].shape[0]), X_r_lda[labels == i, 0], alpha=0.8, color=color, label=target_name)
            plt.xlabel('Sample Index')
            plt.ylabel('LDA Component 1')
        else:
            # Standard 2D LDA plot
            for color, i, target_name in zip(colors, [0, 1], target_names):
                plt.scatter(X_r_lda[labels == i, 0], X_r_lda[labels == i, 1], alpha=0.8, color=color, label=target_name)
            plt.xlabel('LDA Component 1')
            plt.ylabel('LDA Component 2')
        
        plt.legend(loc="best", shadow=False, scatterpoints=1)
        plt.title("LDA Projection of Data")
        plt.show()

    def plot_eigenvalues_and_variance(self, X, y):
        """
        Plot eigenvalues and explained variance after fitting the LDA.
        """
        np.set_printoptions(precision=4)
        # Calculate within-class scatter matrix
        mean_vectors = []
        for cl in np.unique(y):
            mean_vectors.append(np.mean(X[y == cl], axis=0))

        S_W = np.zeros((X.shape[1], X.shape[1]))
        for cl, mv in zip(np.unique(y), mean_vectors):
            class_sc_mat = np.zeros((X.shape[1], X.shape[1]))  # scatter matrix for every class
            for row in X[y == cl]:
                row, mv = row.reshape(X.shape[1], 1), mv.reshape(X.shape[1], 1)
                class_sc_mat += (row - mv).dot((row - mv).T)
            S_W += class_sc_mat

        # Calculate between-class scatter matrix
        overall_mean = np.mean(X, axis=0)
        S_B = np.zeros((X.shape[1], X.shape[1]))
        for i, mean_vec in enumerate(mean_vectors):
            n = X[y == i].shape[0]
            mean_vec = mean_vec.reshape(X.shape[1], 1)
            overall_mean = overall_mean.reshape(X.shape[1], 1)
            S_B += n * (mean_vec - overall_mean).dot((mean_vec - overall_mean).T)
        # Solve the eigenvalue problem
        eig_vals, eig_vecs = np.linalg.eig(np.linalg.inv(S_W).dot(S_B))
        print("valuers propres",eig_vals,"vecteurs propres",eig_vecs)
        # Sort the eigenvalues in descending order
        eig_pairs = [(np.abs(eig_vals[i]), eig_vecs[:, i]) for i in range(len(eig_vals))]
        eig_pairs = sorted(eig_pairs, key=lambda k: k[0], reverse=True)

        # Plotting the eigenvalues
        plt.figure(figsize=(8, 6))
        plt.bar(range(1, len(eig_vals) + 1), [np.real(val) for val in eig_vals], alpha=0.7, align='center')
        plt.title('Eigenvalues for LDA')
        plt.xlabel('Eigenvalue index')
        plt.ylabel('Eigenvalue magnitude')
        plt.show()

        # Calculate and plot the explained variance
        total = sum(eig_vals.real)
        explained_variance = [(i.real / total) * 100 for i in eig_vals]
        cumulative_variance = np.cumsum(explained_variance)

        plt.figure(figsize=(8, 6))
        plt.plot(range(1, len(eig_vals) + 1), cumulative_variance, marker='o', linestyle='--', color='b')
        plt.title('Cumulative Explained Variance for LDA')
        plt.xlabel('Number of Components')
        plt.ylabel('Cumulative Explained Variance (%)')
        plt.grid(True)
        plt.show()

        print("Eigenvalues in decreasing order:")
        for i, pair in enumerate(eig_pairs):
            print(f'Eigenvalue {i + 1}: {pair[0]}')

        print("Explained Variance per Component:")
        for i, var in enumerate(explained_variance):
            print(f'Component {i + 1}: {var:.2f}%')