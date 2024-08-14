"""Machine Learning"""

import importlib
import numpy as np
import pandas as pd
import json
from sklearn.model_selection import train_test_split
from joblib import load, dump
from jsonschema import validate
from sklearn.pipeline import make_pipeline
from timeflux.core.node import Node
from timeflux.core.exceptions import ValidationError, WorkerInterrupt
from timeflux.helpers.background import Task
from timeflux.helpers.port import make_event, match_events, get_meta
from timeflux.helpers.clock import now, min_time, max_time

# Statuses
IDLE = 0
ACCUMULATING = 1
FITTING = 2
READY = 3
def get_cv_scores(self):
    # Assuming the last step is the CustomLDA
    last_step_name, last_step_estimator = self.steps[-1]
    # print('hole',type(last_step_name), type( last_step_estimator))
    if last_step_name=='customlda' and hasattr(last_step_estimator, 'get_cv_scores'):
        return last_step_estimator.get_cv_scores()
    else:
        raise AttributeError("CustomLDA estimator does not have a 'get_cv_scores' method.")

class Pipeline(Node):
    """Fit, transform and predict.

    Training on continuous data is always unsupervised.
    Training on epoched data can either be supervised or unsupervised.

    If fit is `False`, input events are ignored, and initital training is not performed.
    Automatically set to False if mode is either 'fit_predict' or 'fit_transform'.
    Automatically set to True if mode is either 'predict', 'predict_proba' or 'predict_log_proba'.

    Attributes:
        i (Port): Continuous data input, expects DataFrame.
        i_* (Port): Epoched data input, expects DataFrame.
        i_training (Port): Continuous training data input, expects DataFrame.
        i_training_* (Port): Epoched training data input, expects DataFrame.
        i_events (Port): Event input, expects DataFrame.
        o (Port): Continuous data output, provides DataFrame.
        o_* (Port): Epoched data output, provides DataFrame.
        o_events (Port): Event output, provides DataFrame.

    Args:
        steps (dict): Pipeline steps and settings (ignored if 'model' is set)
        fit (bool):
        mode ('predict'|'predict_proba'|'predict_log_proba'|'transform'|'fit_predict'|'fit_transform'):
        meta_label (str|tuple|None):
        event_start_accumulation (str):
        event_stop_accumulation (str):
        event_start_training (str):
        event_reset (str):
        buffer_size (str):
        passthrough (bool):
        resample (bool):
        resample_direction ('right'|'left'|'both'):
        resample_rate (None|float):
        preprocessing: A list of preprocessing steps
        warmup (str): Load a .npy or .npz file and bootstrap the model with initial data
        model (str): Load a pre-computed model, persisted with joblib
        persist (str): Save the model - NOT IMPLEMENTED
        cv: Cross-validation - NOT IMPLEMENTED

    """

    def __init__(
        self,
        steps=None,
        fit=True,
        mode="predict",
        meta_label=("epoch", "context", "target"),
        event_start_accumulation="accumulation_starts",
        event_stop_accumulation="accumulation_stops",
        event_start_training="training_starts",
        event_reset="reset",
        buffer_size="5s",
        passthrough=False,
        resample=False,
        resample_direction="right",
        resample_rate=None,
        preprocessing=None,
        warmup=None,
        model=None,
        persist=None,
        cv=None,
    ):
        # TODO: validation
        # TODO: save model to file
        # TODO: cross-validation
        # TODO: provide more context for errors
        self.fit = fit
        self.mode = mode
        self.meta_label = meta_label
        self.event_start_accumulation = event_start_accumulation
        self.event_stop_accumulation = event_stop_accumulation
        self.event_start_training = event_start_training
        self.event_reset = event_reset
        self.passthrough = passthrough
        self.resample = resample
        self.resample_direction = resample_direction
        self.resample_rate = resample_rate
        self.warmup = warmup
        self.model = model
        self._buffer_size = pd.Timedelta(buffer_size)
        if model:
            self._load_pipeline(model)
        elif steps:
            self._make_pipeline(steps)
        else:
            raise ValueError("You must pass either a 'steps' or 'model' argument")
        self._make_preprocessing(preprocessing)
        self._reset()

    def update(self):
        # Let's get ready
        self._clear()

        # Reset
        if self.event_reset:
            matches = match_events(self.i_events, self.event_reset)
            if matches is not None:
                self.logger.debug("Reset")
                if self._status == FITTING:
                    self._task.stop()
                self._reset()
                self.o_events.data = make_event("reset")

        # Are we dealing with continuous data or epochs?
        if self._dimensions is None:
            port_name = "i_training" if self.fit else "i"
            if getattr(self, port_name).ready():
                self._dimensions = 2
            elif len(list(self.iterate(port_name + "_*"))) > 0:
                self._dimensions = 3

        # Set the accumulation boundaries
        if self._accumulation_start is None:
            matches = match_events(self.i_events, self.event_start_accumulation)
            if matches is not None:
                self._accumulation_start = matches.index.values[0]
                self._status = ACCUMULATING
                self.logger.debug("Start accumulation")
        if self._accumulation_stop is None:
            matches = match_events(self.i_events, self.event_stop_accumulation)
            if matches is not None:
                self._accumulation_stop = matches.index.values[0]+ pd.Timedelta(hours=2)
                print("the stop index",self._accumulation_stop)
                print("the xtrain index", self._X_train_indices)
                self.logger.debug("Stop accumulation")

        # Always buffer a few seconds, in case the start event is coming late
        if self._status == IDLE:
            start = (now() - self._buffer_size).to_datetime64()
            stop = max_time()
            self._accumulate(start, stop)

        # Accumulate between boundaries
        if self._status == ACCUMULATING:
            start = self._accumulation_start
            stop = self._accumulation_stop if self._accumulation_stop else max_time()
            self._accumulate(start, stop)
            # if not self._X_train is None:
                # print("Iam here",self._X_train)
        # Should we start fitting the model?
        if self._status < FITTING:
            if match_events(self.i_events, self.event_start_training) is not None:
                self._status = FITTING
                self.logger.debug("Start training")
                self._warmup()

                self._run_preprocessing()
                # print("now here",self._X_train)
                self._task = Task(
                    self._pipeline, "fit", self._X_train, self._y_train
                ).start()

        # Is the model ready?
        if self._status == FITTING:
            status = self._task.status()
            # print("shape pf training",self._X_train.shape,type(self._X_train))
            if status:
                if status["success"]:
                    self._pipeline = status["instance"]
                    # Save the LDA model
                    lda_model = self._pipeline.named_steps['customlda']
                    filename = 'lda_model.sav'
                    dump(lda_model, filename)
                    self._status = READY
                    self.logger.debug(f"Model fitted in {status['time']} seconds")
                    self.o_events.data = make_event("ready")
                    try:
                        cv_scores = get_cv_scores(self._pipeline)
                        print(f"Cross-validation scores: {cv_scores}")
                    except AttributeError as e:
                        print(f"Error retrieving CV scores: {e}")
                else:
                    self.logger.error(
                        f"An error occured while fitting: {status['exception'].args[0]}"
                    )
                    self.logger.debug(
                        "\nTraceback (most recent call last):\n"
                        + "".join(status["traceback"])
                    )
                    raise WorkerInterrupt()

        # Run the pipeline
        if self._status == READY:
            self._receive()
            if self._X is not None:
                args = [self._X]

                if self.mode.startswith("fit"):
                    args.append(self._y)  
                self._run_preprocessing()
                self._out = getattr(self._pipeline, self.mode)(*args)


        # Set output streams
        self._send()
    #get scores


    def terminate(self):
        # Kill the fit subprocess
        if self._task is not None:
            self._task.stop()

    def _reset(self):
        self._X_train = None
        self._y_train = None
        self._X_train_indices = np.array([], dtype=np.datetime64)
        self._accumulation_start = None
        self._accumulation_stop = None
        self._dimensions = None
        self._shape = ()
        self._task = None
        if self.mode.startswith("fit"):
            self.fit = False
        elif self.mode.startswith("predict"):
            self.fit = True
        if self.model is not None:
            self.fit = False
            if not self.mode.startswith("fit"):
                self.meta_label = None
        if self.fit:
            self._status = IDLE
        else:
            self._status = READY

    def _clear(self):
        self._X = None
        self._y = None
        self._X_indices = []
        self._X_columns = []
        self._X_meta = None
        self._out = None

    def _instantiate_pipeline(self, steps, param="steps"):
        schema = {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "module": {"type": "string"},
                    "class": {"type": "string"},
                    "args": {"type": "object"},
                },
                "required": ["module", "class"],
            },
        }
        try:
            validate(instance=steps, schema=schema)
        except Exception as error:
            raise ValidationError("steps", error.message)
        pipeline = []
        for step in steps:
            try:
                args = step["args"] if "args" in step else {}
                m = importlib.import_module(step["module"])
                c = getattr(m, step["class"])
                i = c(**args)
                pipeline.append(i)
            except ImportError as error:
                raise ValidationError(param, f"could not import '{step['module']}'")
            except AttributeError as error:
                raise ValidationError(param, f"could not find class '{step['class']}'")
            except TypeError as error:
                raise ValidationError(
                    param,
                    f"could not instantiate class '{step['class']}' with the given params",
                )
        return pipeline

    def _make_pipeline(self, steps):
        # TODO: memory and verbose args
        pipeline = self._instantiate_pipeline(steps)
        self._pipeline = make_pipeline(*pipeline, memory=None, verbose=False)

    def _load_pipeline(self, path):
        try:
            self._pipeline = load(path)
        except:
            self.logger.error("Could not load model")
            raise WorkerInterrupt()

    def _make_preprocessing(self, steps):
        if steps == None:
            self._preprocessing = None
            return
        self._preprocessing = self._instantiate_pipeline(steps, "preprocessing")

    def _run_preprocessing(self):
        if self._preprocessing == None:
            return
        if self._status == READY:
            mapping = {
                "X": "_X",
                "y": "_y",
                "indices": "_X_indices",
                "columns": "_X_columns",
                "meta": "_X_meta",
            }
            fitted = True
        else:
            # TODO: columns and meta are missing during training
            mapping = {
                "X": "_X_train",
                "y": "_y_train",
                "indices": "_X_train_indices",
                "columns": "_X_columns",
                "meta": "_X_meta",
            }
            fitted = False
        data = {key: getattr(self, value) for (key, value) in mapping.items()}
        for step in self._preprocessing:
            data["fitted"] = fitted
            data = getattr(step, "run")(data)
        for key, value in mapping.items():
            setattr(self, value, data[key])

    def _warmup(self):
        if self.warmup:
            try:
                data = np.load(self.warmup)
                if type(data) == np.ndarray:
                    data = {
                        "X": data
                    }  # .npy return an ndarray while .npz return a dict
                if "X" in data:
                    if self._X_train is None:
                        self._X_train = data["X"]
                    else:
                        self._X_train = np.vstack((data["X"], self._X_train))
                else:
                    self.logger.warning("Warmup data is missing")
                if "y" in data:
                    if self._y_train is None:
                        self._y_train = data["y"]
                    else:
                        self._y_train = np.append(data["y"], self._y_train)
                else:
                    self.logger.info("Warmup labels are missing")  # OK if unsupervised
            except OSError:
                self.logger.error("Warmup file does not exist or cannot be read")
                raise WorkerInterrupt()
            except ValueError:
                self.logger.error("Warmup and training data dimensions do not match")
                raise WorkerInterrupt()

    def _accumulate(self, start, stop):
        # Do nothing if no fitting required
        if not self.fit:
            return

        # Set defaults
        indices = np.array([], dtype=np.datetime64)

        # Accumulate continuous data
        if self._dimensions == 2:
            if self.i_training.ready():
                data = self.i_training.data
                mask = (data.index >= start) & (data.index < stop)
                data = data[mask]
                if not data.empty:
                    if self._X_train is None:
                        self._X_train = data.values
                        self._shape = self._X_train.shape[1]
                        indices = data.index.values
                    else:
                        if data.shape[1] == self._shape:
                            self._X_train = np.vstack((self._X_train, data.values))
                            indices = data.index.values
                        else:
                            self.logger.warning("Invalid shape")

        # Accumulate epoched data
        if self._dimensions == 3:
            for _, _, port in self.iterate("i_training_*"):
                if port.ready():
                    # print("I am here")
                    index = port.data.index.values[0]
                    if index >= start and index < stop:
                        # print("I am here now ")
                        data = port.data.values
                        # print("the data I have", data)
                        label = get_meta(port, self.meta_label)
                        if self._shape and (data.shape != self._shape):
                            self.logger.warning("Invalid shape")
                            continue
                        if self.meta_label is not None and label is None:
                            self.logger.warning("Invalid label")
                            continue
                        if self._X_train is None:
                            self._X_train = np.array([data])
                            self._shape = self._X_train.shape[1:]
                        else:
                            self._X_train = np.vstack((self._X_train, [data]))
                        indices = np.append(indices, index)
                        if label is not None:
                            if self._y_train is None:
                                self._y_train = np.array([label])
                            else:
                                self._y_train = np.append(self._y_train, [label])

        # Store indices
        if indices.size != 0:
            self._X_train_indices = np.append(self._X_train_indices, indices)

        # Trim
        if self._X_train is not None:
            mask = (self._X_train_indices >= start) & (self._X_train_indices < stop)
            self._X_train = self._X_train[mask]
            self._X_train_indices = self._X_train_indices[mask]
            if self._y_train is not None:
                self._y_train = self._y_train[mask]

    def _receive(self):
        # Continuous data
        if self._dimensions == 2:
            if self.i.ready():
                if not self._X_columns:
                    self._X_columns = list(self.i.data.columns)
                if self._shape and (self.i.data.shape[1] != self._shape):
                    self.logger.warning("Invalid shape")
                else:
                    self._X = self.i.data.values
                    self._X_indices = self.i.data.index.values
                    self._X_meta = self.i.meta

        # Epochs
        if self._dimensions == 3:
            for name, _, port in self.iterate("i_*"):
                if port.ready() and "training" not in name and "events" not in name:
                    data = port.data.values
                    meta = port.meta
                    indices = port.data.index.values
                    label = get_meta(port, self.meta_label)
                    if not self._X_columns:
                        self._X_columns = list(port.data.columns)
                    if self._shape and (data.shape != self._shape):
                        self.logger.warning("Invalid shape")
                        continue
                    if not self.fit and self.meta_label is not None and label is None:
                        self.logger.warning("Invalid label")
                        continue
                    if self._X is None:
                        self._X = []
                    if self._y is None and label is not None:
                        self._y = []
                    if self._X_meta is None:
                        self._X_meta = []
                    self._X.append(data)
                    self._X_indices.append(indices)
                    self._X_meta.append(meta)
                    if label is not None:
                        self._y.append(label)

    def _send(self):
        # Passthrough
        if self._status < READY and self.passthrough:
            inputs = []
            for _, suffix, port in self.iterate("i*"):
                if not suffix.startswith("_training") and not suffix.startswith(
                    "_events"
                ):
                    inputs.append((suffix, port))
            for suffix, src_port in inputs:
                dst_port = getattr(self, "o" + suffix)
                dst_port.data = src_port.data
                dst_port.meta = src_port.meta

        # Model
        if self._out is not None:
            if "predict" in self.mode:
                # Send events

                if len(self._X_indices) == len(self._out):
                    # TODO: skip JSON serialization?
                    data = [
                        [self.mode, json.dumps({"result": self._np_to_native(result)})]
                        for result in self._out
                    ]
                    times = (
                        self._X_indices
                        if self._dimensions == 2
                        else np.asarray(self._X_indices)[:, 0]
                    )  # Keep the first timestamp of each epoch
                    names = ["label", "data"]
                    meta = (
                        self._X_meta
                        if self._dimensions == 2
                        else {"epochs": self._X_meta}
                    )  # port.meta should always be an object
                    if hasattr(self._pipeline, "classes_"):
                        meta["classes"] = list(self._pipeline.classes_)
                    rows = pd.DataFrame(data, index=times, columns=names)
                    if self.o_events.ready():
                        # Make sure we don't overwrite other events
                        self.o_events.data = pd.concat([self.o_events.data, rows])
                    else:
                        self.o_events.data = rows
                    self.o_events.meta = meta
                else:
                    self.logger.warning(
                        "Number of predictions inconsistent with input length"
                    )
            else:
                # Send data
                if self._dimensions == 2:
                    try:
                        self.o.data = self._reindex(
                            self._out, self._X_indices, self._X_columns
                        )
                        self.o.meta = self._X_meta
                    except Exception as e:
                        self.logger.warning(getattr(e, "message", repr(e)))
                if self._dimensions == 3:
                    if len(self._X_indices) == len(self._out):
                        for i, (data, times) in enumerate(
                            zip(self._out, self._X_indices)
                        ):
                            try:
                                getattr(self, "o_" + str(i)).data = self._reindex(
                                    data, times, self._X_columns
                                )
                                getattr(self, "o_" + str(i)).meta = self._X_meta[i]
                            except Exception as e:
                                self.logger.warning(getattr(e, "message", repr(e)))
                    else:
                        self.logger.warning(
                            "Number of transforms inconsistent with number of epochs"
                        )

    def _np_to_native(self, data):
        """Convert numpy scalars and objects to native types."""
        return getattr(data, "tolist", lambda: data)()

    def _reindex(self, data, times, columns):
        if len(data) != len(times):
            if self.resample:
                # Resample at a specific frequency
                kwargs = {"periods": len(data)}
                if self.resample_rate is None:
                    kwargs["freq"] = pd.infer_freq(times)
                    kwargs["freq"] = pd.tseries.frequencies.to_offset(kwargs["freq"])
                else:
                    kwargs["freq"] = pd.DateOffset(seconds=1 / self.resample_rate)
                if self.resample_direction == "right":
                    kwargs["start"] = times[0]
                elif self.resample_direction == "left":
                    kwargs["end"] = times[-1]
                else:

                    def middle(a):
                        return int(np.ceil(len(a) / 2)) - 1

                    kwargs["start"] = times[middle(times)] - (
                        middle(data) * kwargs["freq"]
                    )
                times = pd.date_range(**kwargs)

            else:
                # Linearly arange between first and last
                times = pd.date_range(start=times[0], end=times[-1], periods=len(data))

        return pd.DataFrame(data, times, columns)