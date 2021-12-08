from flowchem.constants import flowchem_ureg
from flowchem.platforms.experiment_conditions import ExperimentConditions
import datetime
from numpy import array, sum

class FlowConditions:
    """From  experiment conditions, flow conditions can be derived, which happens right before each experiment.
    Basically, just to separate off redundant data.
    Links Experiment Conditions to platform.
    All private parameters are only internally needed for calculation (and maybe as checkpoints for simpler testing).
    """

    def __init__(self, experiment_conditions: ExperimentConditions,
                 flow_platform: dict):  # for now, the flowplatform is handed in as a manually written dict and
        # abstraction still low
        experiment_conditions.experiment_id = round(datetime.datetime.timestamp(datetime.datetime.now()))

        # better readability
        self.platform_volumes = flow_platform['internal_volumes']

        # translate to pint
        self._concentration_donor = flowchem_ureg(experiment_conditions.concentration_donor).to('M')
        self._concentration_activator = flowchem_ureg(experiment_conditions.stock_concentration_activator).to('M')
        self._concentration_quencher = flowchem_ureg(experiment_conditions.stock_concentration_quencher).to('M')
        self.residence_time = flowchem_ureg(experiment_conditions.residence_time).to('s')

        self._total_flow_rate = self.get_flow_rate(self.platform_volumes['volume_reactor'],
                                                   self.residence_time)

        self.activator_flow_rate, self.donor_flow_rate = self.get_individual_flow_rate(self._total_flow_rate,
                                                                           concentrations=(
                                                                           self._concentration_activator.magnitude,
                                                                           self._concentration_donor.magnitude,),
                                                                           equivalents=(
                                                                           experiment_conditions.activator_equivalents,
                                                                           1,))

        self.activator_flow_rate = self.activator_flow_rate.to(flowchem_ureg.milliliter / flowchem_ureg.minute)
        self.donor_flow_rate = self.donor_flow_rate.to(flowchem_ureg.milliliter / flowchem_ureg.minute)

        self.quencher_flow_rate = 0.1 * flowchem_ureg.mL / flowchem_ureg.min  # self.get_flowrate_added_stream(
        # self._concentration_donor, self.donor_flow_rate, self._concentration_quencher,
        # experiment_conditions._quencher_equivalents)

        self.temperature = flowchem_ureg(experiment_conditions.temperature)

        self.activator = experiment_conditions.activator

        # Todo in theory not that simple anymore if different flowrates
        self._time_start_till_end = ((self.platform_volumes['dead_volume_before_reactor'] +
                                      self.platform_volumes['volume_reactor']) / self._total_flow_rate +
                                     (self.platform_volumes['dead_volume_to_HPLC'] / (self._total_flow_rate +
                                                                                      self.quencher_flow_rate))).to(
            flowchem_ureg.second)

        self.steady_state_time = (self._time_start_till_end + self.residence_time *
                                  (experiment_conditions.reactor_volumes - 1)).to(flowchem_ureg.second)

    def get_flow_rate(self, relevant_volume, residence_time):
        return (relevant_volume / residence_time).to('mL/min')

    # TODO for now concentration needs to go in always in the same dimension, and as float, for future, iterate over
    #  tuple, bring to same unit and use a copy of that for array
    def get_individual_flow_rate(self, target_flow_rate: float, equivalents: tuple = (), concentrations: tuple = ()):
        """
        Give as many inputs as desired, output will be in same order as input and hold required flowrates
        """
        normalised_flow_rates = array(equivalents) / array(concentrations)
        sum_of_normalised_flowrates = sum(normalised_flow_rates)
        correction_factor = target_flow_rate / sum_of_normalised_flowrates
        return tuple(normalised_flow_rates * correction_factor)

    def get_flowrate_added_stream(self, concentration_reference_stream: float, flowrate_reference_stream: float,
                                  concentration_added_stream: float, equivalents_added_stream: float):
        return (concentration_reference_stream*flowrate_reference_stream*equivalents_added_stream)/concentration_added_stream

    def wait_for_steady_state(self, steady_state_time):
        pass
