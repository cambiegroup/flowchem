from time import sleep, asctime
from flowchem.devices.Petite_Fleur_chiller import Huber
import queue
from threading import Thread
import datetime
import asyncio
from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO, PumpStalled
from flowchem.devices.Knauer.HPLC_control import ClarityInterface
from flowchem.devices.Knauer.KnauerPumpValveAPI import KnauerPump
from flowchem.miscellaneous_helpers.folder_listener import FileReceiver, ResultListener
from flowchem.devices.ViciValco.ViciValco_Actuator import ViciValco
import logging
from typing import Union
from flowchem.constants import flowchem_ureg
from numpy import array, sum
from pandas import read_csv, errors
from pathlib import Path
import json
import dataclasses

class UnderDefinedError(AttributeError):
    pass




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

    def __init__(self, experiment_folder_name, experiment_folder_path= r"defaultpathblabla", file_extension=".soe"):

        self.experiment_folder = Path(experiment_folder_path, experiment_folder_name)
        self.file_extension = file_extension

    def make_experiment_folder(self):
        try:
            Path.mkdir(self.experiment_folder, parents=True, exist_ok=False)
        except FileExistsError:
            # load already performed experiments
            pass
            # instead check if any of the queue elements is already present as measured examples

    def save_data(self, single_experiment_file_name, single_experiment):
        # save a new piece of data to the folder
        with open(Path(self.experiment_folder, single_experiment_file_name+self.file_extension), 'w') as new_experiment_data_file:
            json.dump(single_experiment, new_experiment_data_file, cls=self.EnhancedJSONEncoder)

#td do same magic here/folderpath should always be appended
    def load_and_decode_single(self, experiment_data_file_name: Union[str, Path]):
        with open(Path(self.experiment_folder, experiment_data_file_name), 'r') as f:
            loaded: dict = json.load(f)
        # remove the expcode as a key - actually, already saving should be done with T in filename, maybe expname_T_expcode
        #unpack the dictionary and hand to class for reconstruction
        return ExperimentConditions(**loaded)


    def load_and_decode_batch(self):
        loaded_experiments = {}
        for files in self.experiment_folder.glob("*" + self.file_extension):
            one_condition = self.load_and_decode_single(files)
            if not loaded_experiments[one_condition.temperature]:
                loaded_experiments[one_condition.temperature] = one_condition
            else:
                logging.warning("Could not be loaded since same temperature was already loaded - probably another "
                                "parameter is different. Yet to be implemented")
        return loaded_experiments

#ToDo:
# optional 1b) Check the experiments in the folder in the beginning, if experiments already performed -> take from queue and don't execute
# 2b) do comparison if all other parameters are the same, if not, issue a warning and expand key description
# 3) get plotting and legend setup out of the box
# 4) determine peaks and do integration
# 5) report integration vs T
# 6) visualize integration




# TODO combining the sample name with the commit hash would make the experiment even more traceable. probably a
#  good idea...
# what I don't really get is why the class attributes are not printed to dict
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

    building_block_smiles = None

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

        # TODO watch out, now the quencher equivalents are based on donor, I think
        self.quencher_flow_rate = 0.1 * flowchem_ureg.mL / flowchem_ureg.min  # self.get_flowrate_added_stream(
        # self._concentration_donor, self.donor_flow_rate, self._concentration_quencher,
        # experiment_conditions._quencher_equivalents)

        self.temperature = flowchem_ureg(experiment_conditions.temperature)

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


class FlowProcedure:

    def __init__(self, platform_graph: dict):
        self.pumps = platform_graph['pumps']
        self.hplc: ClarityInterface = platform_graph['HPLC']
        self.chiller: Huber = platform_graph['chiller']
        self.sample_loop = platform_graph['sample_loop']
        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

    def individual_preparations(self, flow_conditions: FlowConditions):
        # TODO also here, for now this is a workaround for ureg.
        self.log.info(f'Setting Chiller to  {flow_conditions.temperature}')
        self.chiller.set_temperature(flow_conditions.temperature.magnitude)
        self.log.info(f'Chiller successfully set to  {flow_conditions.temperature}')
        self.chiller.start()
        self.log.info('Chiller started')

    def individual_procedure(self, flow_conditions: FlowConditions):
        while abs(((flowchem_ureg.celsius*self.chiller.get_process_temperature()).m_as("K") - flow_conditions.temperature.m_as("K"))) > 2:
            sleep(10)
            self.log.info(
                f'Chiller waiting, current: {self.chiller.get_process_temperature()} set: {flow_conditions.temperature}')

        # set all flow rates
        self.log.info(f'Setting donor flow rate to  {flow_conditions.donor_flow_rate}')
        self.pumps['donor'].infusion_rate = flow_conditions.donor_flow_rate.m_as('mL/min')  # dimensionless, in ml/min
        self.pumps['activator'].infusion_rate = flow_conditions.activator_flow_rate.m_as('mL/min')

        self.log.info(f'Setting quencher flow rate to  {flow_conditions.quencher_flow_rate}')
        self.pumps['quencher'].set_flow(flow_conditions.quencher_flow_rate.m_as(
            'mL/min'))  # in principal, this works, if wrong flowrate set, check from here what is problem

        self.log.info('Starting donor pump')
        self.pumps['donor'].run()
        self.log.info('Starting activator pump')
        self.pumps['activator'].run()

        self.log.info('Starting quencher pump')
        self.pumps['quencher'].start_flow()

        # start timer
        time_done = (datetime.datetime.now() +
                     datetime.timedelta(0, flow_conditions.steady_state_time.m_as('s'))).strftime('%H:%M:%S')
        self.log.info(f'Timer starting, sleep for {flow_conditions.steady_state_time}, experiment will be done at {time_done}')
        sleep(flow_conditions.steady_state_time.magnitude)
        self.log.info('Timer over, now take measurement}')

        try:
            self.pumps['donor'].is_moving()
            self.pumps['activator'].is_moving()

            self.hplc.set_sample_name(scheduler.current_experiment.experiment_id)

            while scheduler.experiment_waiting_for_analysis:
                sleep(5)
                self.log.warning('Previous analysis not yet finished - waiting with injection until finished')
            self.sample_loop.set_valve_position_sync(2)
            # this is as a safety measure - it happened once that the run did not start even though it got triggered
            self.hplc.run()
            # timer is over, start
            self.log.info('Stop pump Donor')
            self.pumps['donor'].stop()

            self.log.info('Stop pump Activator')
            self.pumps['activator'].stop()

            self.sample_loop.set_valve_position_sync(1)

            self.log.info(f'setting experiment {scheduler.current_experiment.experiment_id} as finished')
            scheduler.current_experiment._experiment_finished = True

        except PumpStalled:
            # this indicates that a syringe pump blocked. there will be no further handling
            scheduler.current_experiment._experiment_failed = True
            self.pumps['donor'].stop()
            self.pumps['activator'].stop()
            self.log.warning('One syringe pump stopped, likely due to stalling. Please resolve.')

    def get_platform_ready(self):
        """Here, code is defined that runs once to prepare the platform. These are things like switching on HPLC lamps,
        sending the hplc method"""
        # prepare HPLC

        self.log.info('getting the platform ready: HPLC')
        [p.stop() for p in self.pumps.values() if isinstance(p, Elite11)]

        self.hplc.exit()
        self.hplc.switch_lamp_on()  # address and port hardcoded
        self.log.info('switch on lamps')

        self.hplc.open_clarity_chrom("admin", config_file=r"C:\ClarityChrom\Cfg\automated_exp.cfg ",
                                     start_method=r"D:\Data2q\sugar-optimizer\autostartup_analysis\autostartup_005_"
                                                  r"Sugar-c18_shortened.MET")
        self.log.info('open clarity and now start ramp')
        self.hplc.slow_flowrate_ramp(r"D:\Data2q\sugar-optimizer\autostartup_analysis",
                                     method_list=("autostartup_005_Sugar-c18_shortened.MET",
                                                  "autostartup_01_Sugar-c18_shortened.MET",
                                                  "autostartup_015_Sugar-c18_shortened.MET",
                                                  "autostartup_02_Sugar-c18_shortened.MET",
                                                  "autostartup_025_Sugar-c18_shortened.MET",
                                                  "autostartup_03_Sugar-c18_shortened.MET",
                                                  "autostartup_035_Sugar-c18_shortened.MET",
                                                  "autostartup_04_Sugar-c18_shortened.MET",
                                                  "autostartup_045_Sugar-c18_shortened.MET",
                                                  "autostartup_05_Sugar-c18_shortened.MET",))
        self.hplc.load_file(r"D:\Data2q\sugar-optimizer\autostartup_analysis\auto_Sugar-c18_shortened.MET")
        self.log.info('load method')

        # Todo fill
        # commander.load_file("opendedicatedproject") # open a project for measurements

        # fill the activator to the hamilton syringe

        self.log.info('getting the platform ready: setting HPLC max pressure')
        self.pumps['quencher'].set_maximum_pressure(13)
        asyncio.run(self.sample_loop.valve_io.initialize())


class Scheduler:
    """put together procedures and conditions, assign ID, put this to experiment Queue"""

    def __init__(self, graph: dict, experiment_name: str = "",
                 analysis_results: Path = Path(r'D:/transferred_chromatograms'),
                 experiments_results: Path = Path(f'D:/transferred_chromatograms/'), procedure=FlowProcedure):

        self.graph = graph
        self.log = logging.getLogger(__name__).getChild(__class__.__name__)
        self.procedure = procedure(self.graph)
        self.experiment_queue = queue.Queue()
        # start worker

        self.experiment_worker = Thread(target=self.experiment_handler)
        self.experiment_worker.start()
        self.log.debug('Starting the experiment worker')
        self.analysis_results = analysis_results

        # create a worker function which compares these two. For efficiency, it will just check if analysed_samples is
        # empty. If not, it will get the respective experimental conditions from started_experiments. Combine the two
        # and drop it to the sql. in future, also hand it to the optimizer
        # noinspection PyTypeChecker
        self._current_experiment: ExperimentConditions = None
        # noinspection PyTypeChecker
        self._experiment_waiting_for_analysis: ExperimentConditions = None

        self.analysed_samples = []

        self.data_worker = Thread(target=self.data_handler)
        self.data_worker.start()
        self.log.debug('Starting the data worker')
        self.experiment_name = experiment_name

        self.current_building_block = None

        self.experiment_saving_loading = SaveRetrieveData(self.experiment_name, experiment_folder_path=f'D:/transferred_chromatograms/sugar_optimizer_experiments')
        self.experiment_saving_loading.make_experiment_folder()

        # takes necessery steps to initialise the platform
        self.procedure.get_platform_ready()
        self.log.debug('Initialising the platform')

    @property
    def current_experiment(self):
        return self._current_experiment

    @property
    def experiment_waiting_for_analysis(self):
        return self._experiment_waiting_for_analysis

    @current_experiment.setter
    def current_experiment(self, new_running_experiment: ExperimentConditions):
        if not self.current_experiment or not new_running_experiment:
            self._current_experiment = new_running_experiment
        else:
            self.log.warning(
                f'Something is trying to replace the current, still running experiment '
                f'{scheduler.current_experiment.experiment_id} with a new experiment')

    @experiment_waiting_for_analysis.setter
    def experiment_waiting_for_analysis(self, new_experiment_waiting: ExperimentConditions):
        if not self.experiment_waiting_for_analysis or not new_experiment_waiting:
            self._experiment_waiting_for_analysis = new_experiment_waiting
        else:
            self.log.warning(
                f'Something is trying to replace experiment {scheduler.experiment_waiting_for_analysis.experiment_id} '
                f'currently still waiting for analysis with a new experiment')

    def create_experiments_from_user_input(self):
        self.log.info('Queue empty and nothing running, switch me off or add a new experiment. Add one or '
                      'multiple experiments by specifying temperatures, separated by semicolons, eg 25 °C; '
                      '35 °C')
        new_user_experiments = input().split(';')
        for new_user_experiment in new_user_experiments:
            # in case someone gives a string
            self.create_experiment(ExperimentConditions(temperature=new_user_experiment.strip('\'')))

    def data_handler(self):
        """Checks if there is new analysis results. Since there may be multiple result files, these need to be pruned
        to individual ID and put into the set"""

        # Think about how to do that in more simple way
        while True:
            if self.experiment_waiting_for_analysis:
                for analysed_samples_file in self.analysed_samples:
                    if str(self.experiment_waiting_for_analysis.experiment_id) in analysed_samples_file:
                        self.log.info(
                            f'New analysis result found for experiment '
                            f'{self.experiment_waiting_for_analysis.experiment_id}, analysis set True accordingly')

                        self.experiment_waiting_for_analysis.chromatogram = self.analysis_results / Path(
                            (str(self.experiment_waiting_for_analysis.experiment_id) +' - Detector 1.txt')) # TODO workaround should be more elegant

                        # here, drop the results dictionary to json. In case sth goes wrong, it can be reloaded.
                        self.experiment_saving_loading.save_data(self.experiment_name+self.experiment_waiting_for_analysis.temperature, self.experiment_waiting_for_analysis)
                        self.experiment_waiting_for_analysis = None
                        sleep(1)
                        # should become MongoDB, should be possible to be updated from somewhere else, eg with current T
            sleep(1)

    # just puts minimal conditions to the queue. Initially, this can be done manually/iterating over parameter space
    def create_experiment(self, conditions: ExperimentConditions) -> None:
        self.log.debug('New conditions put to queue')
        # Do a sanity check on experiment conditions, smiles has to be provided
        conditions.check_experiment_conditions_completeness()
        self.experiment_queue.put(conditions)

    def experiment_handler(self):
        """sits in separate thread, checks if previous job is finished and if so grabs new job from queue and executes
        it in a new thread"""
        while True:
            sleep(1)
            if self.current_experiment:
                # no! this is a local variable, the current_experiment. It needs to be checked if current experiment in
                # the  list has failed
                if self.current_experiment._experiment_failed:
                    self.current_experiment._experiment_failed = False
                    self.current_experiment.experiment_id = None
                    self.experiment_queue.put(self.current_experiment)
                    self.current_experiment = None

                    self.log.warning(
                        'Last experiment failed due to pump stalling. Please, refill the syringe and then press enter. '
                        'Press Y for resuming or N for ending the experiment. The failed experiment was put to the '
                        'queue again and will be repeated')

                    user_input = input()
                    while user_input not in 'YN':
                        sleep(1)
                        self.log.info('Please, type either Y or N')
                        user_input = input()
                        if user_input == 'YN':
                            user_input = ''
                            self.log.warning("You typed YN, please type either Y or N")
                    if user_input == 'Y':
                        pass
                    elif user_input == 'N':
                        break

                elif self.current_experiment._experiment_finished:
                    self.experiment_waiting_for_analysis = self.current_experiment
                    self.current_experiment = None

            elif not self.current_experiment:
                if not self.experiment_queue.empty():
                    # get raw experimental data, derive actual platform parameters, create sequence function and execute
                    # that in a thread
                    self.current_experiment: ExperimentConditions = self.experiment_queue.get()
                    if self.current_building_block == self.current_experiment.building_block_smiles:
                        self.log.info("Measuring another data point for the building block that already was measured")
                    elif not self.current_building_block:
                        self.current_building_block = self.current_experiment.building_block_smiles
                        self.log.info("Platform is starting, first building block in sequence of building blocks to screen is loaded")
                    elif self.current_building_block != self.current_experiment.building_block_smiles:
                        self.log.info("You want to measure a new building block, different from the one before."
                                      "Therefore, please load new BB syringe and exchange activator. Type GO once done")
                        # here needs to block and allow for user feedback
                        while input() != "GO":
                            self.log.info("please try again. Type GO")

                    # here, check if the smiles of previous experiment is the same as of experiment now
                    self.experiment_queue.task_done()

                    individual_conditions = FlowConditions(self.current_experiment, self.graph)
                    self.log.info(f'New experiment {self.current_experiment.experiment_id} about to be started')

                    # should set temperture directly after previous experiment finished
                    new_preparation_thread = Thread(target=self.procedure.individual_preparations, args=(individual_conditions,))
                    new_preparation_thread.start()
                    new_preparation_thread.join()

                    new_thread = Thread(target=self.procedure.individual_procedure,
                                        args=(individual_conditions,))

                    # use ureg
                    if not self.experiment_waiting_for_analysis:  # avoids contests
                        new_thread.start()
                        self.log.info('New experiment started because none was waiting for analysis')
                        new_thread.join()
                    elif individual_conditions.steady_state_time > flowchem_ureg(
                            self.current_experiment._analysis_time):
                        new_thread.start()
                        self.log.info(
                            'New experiment started, though one is still waiting for analysis because analysis time is '
                            'shorter than experiment time')
                        new_thread.join()

                    else:
                        time_difference = flowchem_ureg(
                            self.current_experiment._analysis_time) - individual_conditions.steady_state_time
                        waiting_done = (datetime.datetime.now() + datetime.timedelta(0, time_difference.m_as('s'))).strftime('%H:%M:%S')
                        self.log.info(f'sleeping for {time_difference}, until {waiting_done}, then starting next experiment. This is because '
                                      f'analysis time is {self.current_experiment._analysis_time}, and the full '
                                      f'experiment steady state time is {individual_conditions.steady_state_time}')
                        sleep(time_difference.m_as('s'))
                        new_thread.start()
                        self.log.info(
                            'New experiment started, though one is still waiting for analysis after waiting for the lag'
                            ' time')
                        new_thread.join()

# somehow doesn't work anyway
            # elif self.experiment_queue.empty() and self.started_experiments:
            #     # start timer in separate thread. this timer should be killed by having sth in the queue again.
            #     # When exceeding some time, platform should shut down

            #     user_input = Thread(target=self.create_experiments_from_user_input)
            #     user_input.start()
            #     user_input.join()


if __name__ == "__main__":
    # FlowGraph as dicitonary
    logging.basicConfig()
    logging.getLogger("__main__").setLevel(logging.DEBUG)

    # missing init parameters
    elite_port = PumpIO("COM11")
    SugarPlatform = {
        # try to combine two pumps to one. flow rate with ratio gives individual flow rate
        'pumps': {
            'donor': Elite11(elite_port, address=0, diameter=4.606, volume_syringe=1),

            'activator': Elite11(elite_port, address=1, diameter=4.606, volume_syringe=1),

            'quencher': KnauerPump("192.168.10.113"),
        },
        'HPLC': ClarityInterface(remote=True, host='192.168.10.11', port=10014, instrument_number=2),

        'sample_loop': ViciValco.from_config({"port": "COM13", "address": 0, "name": "test1"}),
        'chiller': Huber('COM1'),
        'internal_volumes': {'dead_volume_before_reactor': 8 * 2 * flowchem_ureg.microliter,
                             'volume_reactor': 58 * flowchem_ureg.microliter,
                             'dead_volume_to_HPLC': (46 + 28 + 20) * flowchem_ureg.microliter, # 20 µl for tubing from readtor to valve, 28 µl after microstructure (sounds a lot), 46µL for microrstructure
                             }
    }

    #
    fr = FileReceiver('192.168.10.20', 10339, allowed_address='192.168.10.11')
    analysed_samples_folder = Path(r'D:/transferred_chromatograms')
    scheduler = Scheduler(SugarPlatform, experiment_name='fullcharacterisationyuntao',
                          analysis_results=analysed_samples_folder,
                          experiments_results=analysed_samples_folder / Path('experiments_test'))

    # This obviously could be included into the scheduler
    results_listener = ResultListener(analysed_samples_folder, '*Detector 1.txt', scheduler.analysed_samples)

    scheduler.create_experiment(ExperimentConditions(temperature="10 °C", residence_time="300 s"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="0 °C"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="-10 °C"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="-15 °C"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="-20 °C"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="-40 °C"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="-50 °C"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="20 °C", activator_equivalents=0)) # TODO, flowrate can't be set to 0, so this throws error in internal validation and pump pumps with nl/min



    # TODO when queue empty, after some while everything should be switched off
# TODO