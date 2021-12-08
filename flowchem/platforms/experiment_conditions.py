import dataclasses
from pandas import read_csv, errors
from flowchem.platforms.platform_errors import UnderDefinedError
from pathlib import Path
from time import sleep

@dataclasses.dataclass
class ExperimentConditions:
    """This is actively changed, either by human or by optimizer. Goes into the queue.
    When the conditions are taken from the queue, a FlowConditions object is derived from ExperimentCondition.
    ExperimentConditions has to be dropped into a database, eventually, with analytic results and the optimizer
    activated"""

    # fixed, only changed for a new experiment sequence (if stock solution changes)
    _stock_concentration_donor = "0.09 molar"
    _stock_concentration_activator = "0.156 molar"
    _stock_concentration_quencher = "0.62 molar"
    _analysis_time = '16 min'
    # how many reactor volumes until steady state reached
    _reactor_volumes: float = 2.5
    _quencher_eq_to_activator = 50

    # alternative: hardcode flowrates

    residence_time: str = "300 s"
    concentration_donor: str = _stock_concentration_donor
    activator_equivalents: float = 1.7333
    _quencher_equivalents = _quencher_eq_to_activator * activator_equivalents
    temperature: str = "25  °C"

    building_block_smiles: str = None
    # specifies if activator should be pumped or rather pure solvent. thereby, activation can be 'calibrated'
    activator: bool = True

    _experiment_finished: bool = False

    _experiment_failed: bool = False
    _experiment_id: int = None

    # when fully analysed, hold a dataframe of the chromatogram. Once automatic analysis/assignment works,
    # this should also go in
    _chromatogram: dict = None

    def check_experiment_conditions_completeness(self):
        if not self.building_block_smiles:
            raise UnderDefinedError('Please provide SMILES for your BB. Draw your BB in Chemdraw, select, press Alt+Ctrl+C'
                                    'and paste the smiles here')
        if type(self.building_block_smiles) != str:
            raise TypeError()
        # with RDkit it could also be checked if it is a valid smiles and if the molecule makes sense

    @property
    def experiment_id(self):
        return self._experiment_id

    @experiment_id.setter
    def experiment_id(self, exp_id: int):
        if not self.experiment_id or not exp_id:
            self._experiment_id = exp_id
        else:
            # for now
            print(f'You are trying to change the ID of {self._experiment_id} to {exp_id}. Don\'t do that')

    @property
    def stock_concentration_donor(self):
        return self._stock_concentration_donor

    @property
    def stock_concentration_activator(self):
        return self._stock_concentration_activator

    @property
    def stock_concentration_quencher(self):
        return self._stock_concentration_quencher

    @property
    def reactor_volumes(self):
        return self._reactor_volumes

    @property
    def quencher_equivalents(self):
        return self._quencher_equivalents

    @property
    def chromatogram(self):
        from pandas import read_json
        try:
            return read_json(self._chromatogram)
        except ValueError:
            return self._chromatogram

    @chromatogram.setter
    def chromatogram(self, path: str):
        # Damn, if several detectors are exported, this creates several header lines
        if not self.chromatogram:
            try:
                # several times, I observed pandas.errors.EmptyDataError: No columns to parse from file. The file was
                # checked manually and fine: therefore the sleep
                sleep(1)
                self._chromatogram = read_csv(Path(path), header=16, sep='\t').to_json()
            except errors.ParserError:
                raise errors.ParserError('Please make sure your Analytical data is compliant with pandas.read_csv')
        else:
            print('attempt was made to overwrite chromatogram, check code or stop doing this')