from pathlib import Path
from typing import Callable
import pandas as pd
import numpy as np
import calliope


class Process:
    """A class to process and collect calliope model data."""
    def __init__(self, function: Callable):
        """
        Parameters
        ----------
        function : Callable
            A function that expects a calliope.Model and returns a pd.DataFrame.
        """
        self.results = pd.DataFrame()
        self.function = function
        
    def process(self, model: calliope.Model, **kwargs) -> None:
        """
        Apply the function to a calliope model and concatenate the result to self.results.

        Parameters
        ----------
        model : calliope.Model
            A calliope model to process.
        **kwargs : dict
            Additional attributes used as extra columns in the results DataFrame.
        """
        result = self.function(model)
        for key, value in reversed(list(kwargs.items())):
            result.insert(0, key, value)

        self.results = self._standardise_and_concat([self.results, result])
        
    @staticmethod
    def _standardise_and_concat(dfs: list[pd.DataFrame]) -> pd.DataFrame:
        """Standardize and concatenate a list of DataFrames."""
        all_columns = [col for df in dfs for col in list(df.columns)]
        all_columns = list(dict.fromkeys(all_columns))  # like set operation, but conserve order
        dfs_standardized = [df.reindex(columns=all_columns, fill_value=np.nan) for df in dfs]
        concatenated = pd.concat(dfs_standardized, ignore_index=True)

        return concatenated


class Processor:
    """
    Class that iterates over several calliope.Models and processes them
    with registered processes.

    Parameters
    ----------
    model_specs : list[dict[str, str]]
        List of dictionaries with model specifications. Each dictionary must
        contain a `path` key pointing to a calliope model file. Other keys may differ
        between models. All keys are prepended to the results
        in first-seen order, with NaN for missing values.
    
    Methods
    -------
    add_process(process: Process) -> None
        Add a Process instance to registered processes.
    
    process_results() -> None
        Process the results using the registered processes.
    
    _validate_model_spec(model_specs: list[dict[str, str]]) -> list[dict[str, str]]
        Validate the model specifications and check for file existence.
    """
    def __init__(self, model_specs: list[dict[str, str]]):
        self.model_specs = self._validate_model_spec(model_specs)
        self.processes = []

    def add_process(self, process: Process) -> None:
        """Add a process instance to the list of registered processes."""
        if not isinstance(process, Process):
            raise TypeError("Process must be of type 'Process'.")
        self.processes.append(process)
        
    def process_results(self, select_labels: list[str] = None) -> None:
        """Iterate over all models and let all registered processes process."""
        all_attributes = list(dict.fromkeys(key for spec in self.model_specs for key in spec))
        if select_labels:
            all_attributes = [key for key in all_attributes if key in select_labels]
        for model_spec in self.model_specs:
            model = calliope.read_netcdf(model_spec["path"])
            attributes = {key: model_spec.get(key, np.nan) for key in all_attributes}
            for process in self.processes:
                process.process(model, **attributes)
    
    @staticmethod
    def _validate_model_spec(model_specs: list[dict[str, str]]) -> list[dict[str, str]]:
        """Check that specifications are string dictionaries with existing paths."""
        for model_spec in model_specs:
            if not isinstance(model_spec, dict):
                raise TypeError("Model specifications must be dictionaries.")
            if "path" not in model_spec:
                raise ValueError(f"model_spec {model_spec} is missing a 'path' key.")
            if not all(isinstance(key, str) and isinstance(value, str)
                       for key, value in model_spec.items()):
                raise TypeError("Model specification keys and values must be strings.")
            if not model_spec["path"] or not Path(model_spec["path"]).exists():
                raise FileNotFoundError(f"File not found: {model_spec['path']}")
        return model_specs
