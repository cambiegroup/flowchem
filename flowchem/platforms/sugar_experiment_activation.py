from time import sleep
from flowchem.devices.Petite_Fleur_chiller import Huber
import queue
from threading import Thread
from datetime import datetime
import asyncio
from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
from flowchem.devices.Knauer.HPLC_control import ClarityInterface
from flowchem.devices.Knauer.KnauerPumpValveAPI import KnauerPump
from flowchem.miscellaneous_helpers.folder_listener import FileReceiver, ResultListener
from flowchem.devices.Hamilton.ML600 import HamiltonPumpIO, ML600
from flowchem.devices.ViciValco.ViciValco_Actuator import ViciValco
import logging
from flowchem.constants import flowchem_ureg
from numpy import array, sum
from pandas import read_csv, errors
from pathlib import Path
import json

# TODO combining the sample name with the commit hash would make the experiment even more traceable. probably a good idea...

# what I don't really get is why the class attributes are not printed to dict
@dataclasses.dataclass
class ExperimentConditions:
    """This is actively changed, either by human or by optimizer. Goes into the queue.
    When the conditions are taken from the queue, a FlowConditions object is derived from ExperimentCondition.
    ExperimentConditions has to be dropped into a database, eventually, with analytic results and the optimizer activated"""

    # fixed, only changed for a new experiment sequence (if stock solution changes)
    _stock_concentration_donor = "0.09 molar"
    _stock_concentration_activator = "0.156 molar"
    _stock_concentration_quencher = "0.62 molar"
    # how many reactor volumes until steady state reached
    _reactor_volumes: float = 3
    _quencher_eq_to_activator = 50

    # alternative: hardcode flowrates

    residence_time: str = "300 s"
    concentration_donor: str = _stock_concentration_donor
    activator_equivalents: float = 1.7333
    _quencher_equivalents = _quencher_eq_to_activator * activator_equivalents
    temperature: str = "25  °C"

    _experiment_finished: bool = False
    _analysis_finished: bool = False

    # when fully analysed, hold a dataframe of the chromatogram. Once automatic analysis/assignment works, this should also go in
    _chromatogram: dict = None

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
        return self._chromatogram

    @chromatogram.setter
    def chromatogram(self, path: str):
        #Damn, if several detectors are exported, this creates several header lines
        try:
            read_csv(Path(path), header=16, sep='\t').to_json()
        except errors.ParserError:
            raise errors.ParserError('Please make sure your Analytical data is compliant with pandas.read_csv')


class FlowConditions:
    """From  experiment conditions, flow conditions can be derived, which happens right before each experiment.
    Basically, just to separate off redundant data.
    Links Experiment Conditions to platform.
    All private parameters are only internally needed for calculation (and maybe as checkpoints for simpler testing).
    """

    def __init__(self, experiment_conditions: ExperimentConditions,
                 flow_platform: dict):  # for now, the flowplatform is handed in as a manually written dict and abstraction still low

        self.experiment_id = round(datetime.timestamp(datetime.now()))

        # better readability
        self.platform_volumes = flow_platform['internal_volumes']

        self._concentration_donor = experiment_conditions.concentration_donor
        self._concentration_activator = experiment_conditions.stock_concentration_activator
        self._concentration_quencher = experiment_conditions.stock_concentration_quencher

        self._total_flow_rate = self.get_flow_rate(self.platform_volumes['volume_reactor'],
                                                   experiment_conditions.residence_time)


        self.activator_flow_rate, self.donor_flow_rate = self.get_individual_flow_rate(self._total_flow_rate,
                                                                                       concentrations=(self._concentration_activator.magnitude, self._concentration_donor.magnitude,), equivalents=(experiment_conditions.activator_equivalents, 1,))

        self.activator_flow_rate = self.activator_flow_rate.to(flowchem_ureg.milliliter / flowchem_ureg.minute)
        self.donor_flow_rate = self.donor_flow_rate.to(flowchem_ureg.milliliter / flowchem_ureg.minute)

        # TODO watch out, now the quencher equivalents are based on donor, I think
        self.quencher_flow_rate = 0.1*flowchem_ureg.mL/flowchem_ureg.min #self.get_flowrate_added_stream(self._concentration_donor, self.donor_flow_rate, self._concentration_quencher, experiment_conditions._quencher_equivalents)

        self.temperature = experiment_conditions.temperature

        # Todo in theory not that simple anymore if different flowrates
        self._time_start_till_end = ((self.platform_volumes['dead_volume_before_reactor'] +
                                     self.platform_volumes['volume_reactor']) / self._total_flow_rate +
                                     (self.platform_volumes['dead_volume_to_HPLC'] / (self._total_flow_rate +
                                                                                      self.quencher_flow_rate))).to(flowchem_ureg.second)

        self.steady_state_time = (self._time_start_till_end + experiment_conditions.residence_time *
                                  (experiment_conditions.reactor_volumes-1)).to(flowchem_ureg.second)

    def get_flow_rate(self, relevant_volume: float, residence_time: int):
        return (relevant_volume / residence_time).to(flowchem_ureg.milliliter / flowchem_ureg.minute)

    #TODO for now concentration needs to go in always in the same dimension, and as float, for future, iterate over tuple, bring to same unit and use a copy of that for array
    def get_individual_flow_rate(self, target_flow_rate: float, equivalents: tuple = (), concentrations: tuple = ()):
        """
        Give as many inputs as desired, output will be in same order as input and hold required flowrates
        """

        normalised_flow_rates = array(equivalents) / array(concentrations)
        sum_of_normalised_flowrates = sum(normalised_flow_rates)
        correction_factor = target_flow_rate / sum_of_normalised_flowrates
        return tuple(normalised_flow_rates * correction_factor)

    def get_flowrate_added_stream(self, concentration_reference_stream:float, flowrate_reference_stream:float,
                                  concentration_added_stream:float, equivalents_added_stream:float):
        return (concentration_reference_stream*flowrate_reference_stream*equivalents_added_stream)/concentration_added_stream

    def wait_for_steady_state(self, steady_state_time):
        pass


class FlowProcedure:

    def __init__(self, platform_graph: dict):
        self.pumps = platform_graph['pumps']
        self.hplc: ClarityInterface = platform_graph['HPLC']
        self.chiller: Huber = platform_graph['chiller']
        self.sample_loop = platform_graph['sample_loop']
        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

    def individual_procedure(self, flow_conditions: FlowConditions):
        # TODO also here, for now this is a workaround for ureg.
        self.log.info(f'Setting Ciller to  {flow_conditions.temperature}')
        self.chiller.set_temperature(flow_conditions.temperature.magnitude)
        self.log.info(f'Chiller successfully set to  {flow_conditions.temperature}')
        self.chiller.start()
        self.log.info('Ciller started')

        while abs(abs(self.chiller.get_temperature()) - abs(flow_conditions.temperature.magnitude)) > 2:
            sleep(10)
            self.log.info(f'Chiller waiting for temperature, at {self.chiller.get_temperature()} set {flow_conditions.temperature}')

        # set all flow rates
        self.log.info(f'Setting donor flow rate to  {flow_conditions.donor_flow_rate}')
        self.pumps['donor'].infusion_rate = flow_conditions.donor_flow_rate.m_as('mL/min') # dimensionless, in ml/min
        self.pumps['activator'].infusion_rate = flow_conditions.activator_flow_rate.m_as('mL/min')

        self.log.info(f'Setting quencher flow rate to  {flow_conditions.quencher_flow_rate}')
        self.pumps['quencher'].set_flow(flow_conditions.quencher_flow_rate.m_as('mL/min')) # in principal, this works, if wrong flowrate set, check from here what is problen

        self.log.info('Starting donor pump')
        self.pumps['donor'].run()

        self.log.info('Starting aactivator pump')
        self.pumps['activator'].run()

        self.log.info('Starting quencher pump')
        self.pumps['quencher'].start_flow()

        # start timer
        self.log.info(f'Timer starting, sleep for {flow_conditions.steady_state_time}')
        sleep(3)#flow_conditions.steady_state_time.magnitude)
        self.log.info('Timer over, now take measurement}')

#        self.hplc.set_sample_name(flow_conditions.experiment_id)
        asyncio.run(self.sample_loop.set_valve_position(2))

        # timer is over, start
        self.log.info('Stop pump Donor')
        self.pumps['donor']. stop()

        self.log.info('Stop pump Activator')
        self.pumps['activator'].stop()

        asyncio.run(self.sample_loop.set_valve_position(1))

        # I think that's not nice
        self.log.info(f'setting experiment {flow_conditions.experiment_id} as finished')
        scheduler.started_experiments[str(flow_conditions.experiment_id)].experiment_finished = True

    def get_platform_ready(self):
        """Here, code is defined that runs once to prepare the platform. These are things like switching on HPLC lamps,
        sending the hplc method"""
        # prepare HPLC

        self.log.info('getting the platform ready: HPLC')

#        self.hplc.exit()
#        self.hplc.switch_lamp_on()  # address and port hardcoded
#        self.hplc.open_clarity_chrom("admin", config_file=r"C:\ClarityChrom\Cfg\automated_exp.cfg ",
#                                     start_method=r"D:\Data2q\sugar-optimizer\autostartup_analysis\autostartup_005_Sugar-c18_shortened.MET")
#        self.hplc.slow_flowrate_ramp(r"D:\Data2q\sugar-optimizer\autostartup_analysis",
#                                     method_list=("autostartup_005_Sugar-c18_shortened.MET",
                                                  # "autostartup_01_Sugar-c18_shortened.MET",
                                                  # "autostartup_015_Sugar-c18_shortened.MET",
                                                  # "autostartup_02_Sugar-c18_shortened.MET",
                                                  # "autostartup_025_Sugar-c18_shortened.MET",
                                                  # "autostartup_03_Sugar-c18_shortened.MET",
                                                  # "autostartup_035_Sugar-c18_shortened.MET",
                                                  # "autostartup_04_Sugar-c18_shortened.MET",
                                                  # "autostartup_045_Sugar-c18_shortened.MET",
#                                                  "autostartup_05_Sugar-c18_shortened.MET",))
#        self.hplc.load_file(r"D:\Data2q\sugar-optimizer\autostartup_analysis\auto_Sugar-c18_shortened.MET")

        # Todo fill
        # commander.load_file("opendedicatedproject") # open a project for measurements

        # fill the activator to the hamilton syringe

        self.log.info('getting the platform ready: setting HPLC max pressure')
        self.pumps['quencher'].set_maximum_pressure(13)
        asyncio.run(self.sample_loop.valve_io.initialize())


class Scheduler:
    """put together procedures and conditions, assign ID, put this to experiment Queue"""

    def __init__(self, graph: dict, analysis_results: Path = Path('D:\\transferred_chromatograms'), experiments_results: Path = Path(f'D:/transferred_chromatograms/')):

        self.graph = graph
        self.log = logging.getLogger(__name__).getChild(__class__.__name__)
        self.procedure = FlowProcedure(self.graph)
        self.experiment_queue = queue.Queue()
        # start worker

        self.experiment_worker = Thread(target=self.experiment_handler)
        self.experiment_worker.start()
        self.log.debug('Starting the experiment worker')
        self.analysis_results = analysis_results

        # create a worker function which compares these two. For efficiency, it will just check if analysed_samples is
        # empty. If not, it will get the respective experimental conditions from started_experiments. Combine the two
        # and drop it to the sql. in future, also hand it to the optimizer
        self.started_experiments = {}

        # for now it only holds analysed samples, but later it should be used to add the analysis results and spectrum to experiment conditions
        self.analysed_samples = []

        self.data_worker = Thread(target=self.data_handler)
        self.data_worker.start()
        self.log.debug('Starting the data worker')

        self._experiment_running = False

        # takes necessery steps to initialise the platform
        self.procedure.get_platform_ready()
        self.log.debug('Initialising the platform')
        self.experiments_results = experiments_results / str(round(datetime.timestamp(datetime.now())))

    @property
    def experiment_running(self) -> bool:
        "returns the flag if experiment is running"
        return self._experiment_running

    @experiment_running.setter
    def experiment_running(self, experiment_running: bool):
        self.log.debug('experiment set running')
        self._experiment_running = experiment_running

    def data_handler(self):
        """Checks if there is new analysis results. Since there may be multiple result files, these need to be pruned to individual ID and put into the set"""

        # TODO put that part of code to the folder listener or so -> could more easily and readable just change experiment status
        while True:
            if self.started_experiments:
                # return volatile copy so no size change during iteration
               for experiment_id in list(self.started_experiments.keys()):
                    if self.started_experiments[experiment_id].experiment_finished and not self.started_experiments[experiment_id].analysis_finished:
                        # needs to
                        if str(experiment_id) in self.analysed_samples:
                            self.started_experiments[experiment_id].analysis_finished = True
                            print(experiment_id)
                            self.log.info(f'New analysis result found for experiment {experiment_id}, analysis set True accordingly')

                            self.started_experiments[experiment_id].chromatogram = self.analysis_results / Path((str(experiment_id)+'.txt'))

                            self.log.debug('Experiment running was set false')
                            self.experiment_running = False # potentially redundant

                            # here, drop the results dictionary to json. In case sth goes wrong, it can be reloaded.
                            with open(self.experiments_results, 'w') as f:
                                json.dump(self.started_experiments)
                            # TODO this can be expanded to trigger the analysis of the sample

# check if experiments can be stopped by only chromatogram available, but actually not having been ran -> this happens. Here not important, but in general, streamlining could mean that experiments are started before previous analysis is over

    # just puts minimal conditions to the queue. Initially, this can be done manually/iterating over parameter space
    def create_experiment(self, conditions: ExperimentConditions) -> None:
        self.log.debug('New conditions put to queue')
        self.experiment_queue.put(conditions)

    def experiment_handler(self):
        """sits in separate thread, checks if previous job is finished and if so grabs new job from queue and executes it in a new thread"""
        while True:
            sleep(1)
            if self.experiment_queue.not_empty and not self.experiment_running:
                # get raw experimental data, derive actual platform parameters, create sequence function and execute that in a thread
                experiment: ExperimentConditions = self.experiment_queue.get()
                # append the experiment  to the dictionary
                individual_conditions = FlowConditions(experiment, self.graph)
                self.log.info(f'New experiment {individual_conditions.experiment_id} about to be started')
                self.started_experiments[str(individual_conditions.experiment_id)] = experiment # the actual  Experiment conditions instance sits in the self.started experiments under its id, so attributes can be changed here (analysed and running mainly)
                new_thread = Thread(target=FlowProcedure.individual_procedure,
                                    args=(self.procedure, individual_conditions,))
                new_thread.start()
                self.log.info('experiment running set True')
                self.experiment_running = True
                # this should be called when experiment is over
                self.experiment_queue.task_done()
            elif self.experiment_queue.empty and not self.experiment_running:
                # start timer in separate thread. this timer should be killed by having sth in the queue again. When exceeding some time, platform shuts down
                self.log.info('Queue empty and nothing running, switch me off')


if __name__ == "__main__":
    # FlowGraph as dicitonary
    logging.basicConfig()
    logging.getLogger("__main__").setLevel(logging.DEBUG)

    # missing init parameters
    elite_port=PumpIO("COM11")
    SugarPlatform = {
        # try to combine two pumps to one. flow rate with ratio gives individual flow rate
        'pumps': {
            'donor': Elite11(elite_port, address=0, diameter=14.567, volume_syringe=10),

            'activator': Elite11(elite_port, address=1, diameter=14.567, volume_syringe=10), # for now elite11 pump, hamilton will be used once small syringes arrive, and will be used in continuous mode

            'quencher': KnauerPump("192.168.10.113"),
        },
        'HPLC': ClarityInterface(remote=True, host='192.168.10.11', port=10014, instrument_number=2),

        'sample_loop': ViciValco.from_config({"port": "COM13", "address": 0, "name": "test1"}),
        'chiller': Huber('COM1'),
        # assume always the same volume from pump to inlet, before T-mixer can be neglected, times three for inlets since 3 equal inlets
        'internal_volumes': {'dead_volume_before_reactor': (56+3)* 3 * flowchem_ureg.microliter, # TODO misses volume from tmixer to steel capillaries
                             'volume_mixing': 9.5 * flowchem_ureg.microliter,
                             'volume_reactor': 68.8 * flowchem_ureg.microliter,
                             'dead_volume_to_HPLC': (56+15) * flowchem_ureg.microliter,
                             }
    }

    #
    fr = FileReceiver('192.168.10.20', 10339, allowed_address='192.168.10.11')
    analysed_samples_folder = Path(r'D:/transferred_chromatograms')
    scheduler = Scheduler(SugarPlatform,  analysis_results = analysed_samples_folder, experiments_results=analysed_samples_folder / Path('experiments_test'))


    # This obviously could be included into the scheduler
    results_listener = ResultListener(analysed_samples_folder, '*.txt', scheduler.analysed_samples)

    scheduler.create_experiment(ExperimentConditions(residence_time_in_seconds=300, temperature_in_celsius=25))
    scheduler.create_experiment(ExperimentConditions(temperature_in_celsius=23, residence_time_in_seconds=300))
    # scheduler.create_experiment(ExperimentConditions(residence_time_in_seconds=5))
    # scheduler.create_experiment(ExperimentConditions(residence_time_in_seconds=10))
    # scheduler.create_experiment(ExperimentConditions(residence_time_in_seconds=20))

    # TODO when queue empty, after some while everything should be switched off
