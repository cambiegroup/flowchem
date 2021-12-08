import json
from typing import Union
import dataclasses
from pathlib import Path
from flowchem.platforms.experiment_conditions import ExperimentConditions


class SaveRetrieveData:
    """
    Class that can handle saving and loading experiment data
    It creates a new folder of experiment name, and populates that with experiment data files
    this files can be loaded again to objects, single or in batch
    """
    class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            return super().default(o)

    def __init__(self, experiment_folder_name, experiment_folder_path=r"defaultpathblabla", file_extension=".soe"):

        self.experiment_folder = Path(experiment_folder_path, experiment_folder_name)
        self.file_extension = file_extension

    def make_experiment_folder(self):
        try:
            Path.mkdir(self.experiment_folder, parents=True, exist_ok=False)
        except FileExistsError:
            # load already performed experiments
            pass
            # instead check if any of the queue elements is already present as measured examples

    def save_data(self, single_experiment_file_name, single_experiment: ExperimentConditions):
        # save a new piece of data to the folder
        with open(Path(self.experiment_folder, single_experiment_file_name+self.file_extension), 'w') as \
                new_experiment_data_file:
            json.dump(single_experiment, new_experiment_data_file, cls=self.EnhancedJSONEncoder)

# td do same magic here/folderpath should always be appended
    def load_and_decode_single(self, experiment_data_file_name: Union[str, Path]):
        with open(Path(self.experiment_folder, experiment_data_file_name), 'r') as f:
            loaded: dict = json.load(f)
        # remove the expcode as a key - actually, already saving should be done with T in filename,
        # maybe expname_T_expcode
        # unpack the dictionary and hand to class for reconstruction
        return ExperimentConditions(**loaded)

    def load_and_decode_batch(self):
        loaded_experiments = {}
        for files in self.experiment_folder.glob("*" + self.file_extension):
            one_condition = self.load_and_decode_single(files)
            if one_condition.temperature not in loaded_experiments.keys():
                loaded_experiments[one_condition.temperature] = one_condition
            elif one_condition.temperature in loaded_experiments.keys():
                # find the differences between the twoi experiments
                same_T_1: dict = {k: v for k, v in loaded_experiments[one_condition.temperature].__dict__.items() if k
                                  not in ["_chromatogram", "_experiment_id"]}
                same_T_2: dict = {k: v for k, v in one_condition.__dict__.items() if k not in ["_chromatogram",
                                                                                               "_experiment_id"]}

                # take both, compare to each other and find the different keys
                differences: set = same_T_1.items() ^ same_T_2.items()
                unique = [i[0] for i in differences]
                unique = set(unique)
                # construct difference keys
                same_T_key_1 = ''
                same_T_key_2 = ''
                for i in unique:
                    same_T_key_1 = f"{same_T_key_1} {i}={loaded_experiments[one_condition.temperature].__dict__[i]}"
                    same_T_key_2 = f"{same_T_key_2} {i}={one_condition.__dict__[i]}"
                # add with expanded names
                loaded_experiments[f"{one_condition.temperature} {same_T_key_1}"] = \
                    loaded_experiments[one_condition.temperature]
                loaded_experiments[f"{one_condition.temperature} {same_T_key_2}"] = one_condition
                # drop old
                del loaded_experiments[one_condition.temperature]
        return loaded_experiments

    def plot_single_trace(self, experiment_conditions: ExperimentConditions, label):
        a = experiment_conditions.chromatogram.plot(x="[Min.]", y="[mV]", label=label)
        return a

    def plot_all_traces(self, experiments_conditions: dict):
        # Hand dict for experiments_conditions, where key is the label you want in plot and value is one
        # specific experiment condition
        canvas = None
        for i in experiments_conditions:
            if not canvas:
                canvas = self.plot_single_trace(experiments_conditions[i], i)
            else:
                experiments_conditions[i].chromatogram.plot(x="[Min.]", y="[mV]", ax=canvas, label=i)
