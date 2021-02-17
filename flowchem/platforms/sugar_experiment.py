from time import sleep
from flowchem.devices.Petite_Fleur_chiller import Huber
import queue
from threading import Thread
from datetime import datetime
from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
from flowchem.devices.Knauer.HPLC_control import ClarityInterface
from flowchem.miscellaneous_helpers.folder_listener import FileReceiver, ResultListener
import logging
from flowchem.constants.constants import flowchem_ureg

# TODO combining the sample name with the commit hash would make the experiment even more traceable. probably a good idea...


class ExperimentConditions:
    """This is actively changed, either by human or by optimizer. Goes into the queue.
    When the conditions are taken from the queue, a FlowConditions object is derived from ExperimentCondition.
    ExperimentConditions has to be dropped into a database, eventually, with analytic results and the optimizer activated"""

    # fixed, only changed for a new experiment sequence (if stock solution changes)
    _stock_concentration_donor = 1 * flowchem_ureg.molar
    _stock_concentration_acceptor = 1 * flowchem_ureg.molar
    _stock_concentration_activator = 1 * flowchem_ureg.molar
    _stock_concentration_quencher = 1 * flowchem_ureg.molar
    # how many reactor volumes until steady state reached
    _reactor_volumes = 3

    # mutable
    residence_time = 60 * flowchem_ureg.second  # sec
    concentration_donor = 0.25 * flowchem_ureg.molar
    acceptor_equivalents = 1.2
    activator_equivalents = 1.5
    _quencher_equivalents = 2 * activator_equivalents  # fixed, from SI, but eq with regards to activator
    temperature = flowchem_ureg.Quantity(-80, flowchem_ureg.celsius)

    @property
    def stock_concentration_donor(self):
        return self._stock_concentration_donor

    @property
    def stock_concentration_acceptor(self):
        return self._stock_concentration_acceptor

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


class FlowConditions:
    """From  experiment conditions, flow conditions can be derived, which happens right before each experiment.
    Basically, just to separate off redundant data.
    Links Experiment Conditions to platform.
    All private parameters are only internally needed for calculation (and maybe as checkpoints for simpler testing).
    """

    # these can be calculated, from eqach pump 'package', the flow rate should be the same I suppose
    def __init__(self, experiment_conditions: ExperimentConditions,
                 flow_platform: dict):  # for now, the flowplatform is handed in as a manually written dict and abstraction still low

        self.experiment_id = round(datetime.timestamp(datetime.now()))

        # better readability
        self.platform_volumes = flow_platform['internal_volumes']

        self._concentration_donor = experiment_conditions.concentration_donor
        self._concentration_acceptor = self.get_dependent_concentration(self._concentration_donor,
                                                                        experiment_conditions.acceptor_equivalents)
        self._concentration_activator = self.get_dependent_concentration(self._concentration_donor,
                                                                         experiment_conditions.activator_equivalents)
        self._total_flow_rate = self.get_flow_rate(self.platform_volumes['volume_reactor'],
                                                   experiment_conditions.residence_time)

        # since setting ratios by concentration rather than flow rate (and thereby, always having the same flowrate ratios), some abstraction is already possible
        self._individual_inlet_flow_rate = self._total_flow_rate / 3  # 3 is the number of mating inlets

        # flow rates on pump base by required dilution
        # explicit better than implicit, these could be dropped as control, but a bit verbose
        self.acceptor_flow_rate, self.acceptor_solvent_flow_rate = self.get_dilution_flow_rates(
            experiment_conditions.stock_concentration_acceptor, self._concentration_acceptor,
            self._individual_inlet_flow_rate)

        self.donor_flow_rate, self.donor_solvent_flow_rate = self.get_dilution_flow_rates(
            experiment_conditions.stock_concentration_donor, self._concentration_donor,
            self._individual_inlet_flow_rate)

        self.activator_flow_rate, self.activator_solvent_flow_rate = self.get_dilution_flow_rates(
            experiment_conditions.stock_concentration_activator, self._concentration_activator,
            self._individual_inlet_flow_rate)

        self.quencher_flow_rate = (experiment_conditions.quencher_equivalents * self._concentration_donor *
                                   self._individual_inlet_flow_rate) / experiment_conditions.stock_concentration_quencher

        self.temperature = experiment_conditions.temperature

        self._time_start_till_end = ((self.platform_volumes['dead_volume_before_reactor'] +
                                     self.platform_volumes['volume_mixing'] +
                                     self.platform_volumes['volume_reactor']) / self._total_flow_rate + \
                                    (self.platform_volumes['dead_volume_to_HPLC'] / (self._total_flow_rate +
                                                                                     self.quencher_flow_rate))).to(
                                        flowchem_ureg.second)

        self.steady_state_time = (self._time_start_till_end + experiment_conditions.residence_time *
                                  experiment_conditions.reactor_volumes).to(flowchem_ureg.second)

    def get_dependent_concentration(self, limiting_reagent_concentration: flowchem_ureg.molar, equivalents: float):
        return limiting_reagent_concentration * equivalents

    def get_dilution_ratio(self, stock_concentration: float, concentration_after_dilution: float):
        return concentration_after_dilution / stock_concentration

    def get_flow_rate(self, relevant_volume: float, residence_time: int):
        return (relevant_volume / residence_time).to(flowchem_ureg.milliliter / flowchem_ureg.minute)

    def get_dilution_flow_rates(self, stock_concentration, desired_concentration, desired_flow_rate):
        dilution_factor = self.get_dilution_ratio(stock_concentration, desired_concentration)
        flow_rate_stock_solution = (desired_flow_rate * dilution_factor)
        flow_rate_diluent = desired_flow_rate - flow_rate_stock_solution
        return flow_rate_stock_solution, flow_rate_diluent


class FlowProcedure:

    def __init__(self, platform_graph: dict):
        self.pumps = platform_graph['pumps']
        self.hplc: ClarityInterface = platform_graph['HPLC']
        # self.chiller: Huber = platform_graph['chiller']

    def individual_procedure(self, flow_conditions: FlowConditions):
        # self.chiller.set_temperature(flow_conditions.temperature)
        # self.chiller.start()

        # while (abs(self.chiller.get_temperature()) - abs(flow_conditions.temperature)) > 2:
        #     sleep(10)
        #    print('Chiller waiting for temperature')

        # set all flow rates
        self.pumps['donor'].infusion_rate = flow_conditions.donor_flow_rate
        self.pumps['donor_solvent'].infusion_rate = flow_conditions.donor_solvent_flow_rate
        self.pumps['acceptor'].infusion_rate = flow_conditions.acceptor_flow_rate
        self.pumps['acceptor_solvent'].infusion_rate = flow_conditions.acceptor_solvent_flow_rate
        self.pumps['activator'].infusion_rate = flow_conditions.activator_flow_rate
        self.pumps['activator_solvent'].infusion_rate = flow_conditions.activator_solvent_flow_rate
        self.pumps['quench'].infusion_rate = flow_conditions.quencher_flow_rate

        for pump in self.pumps.values():
            if pump.get_status().name != 'INFUSING':
                pump.run()
        # start timer
        sleep(flow_conditions.steady_state_time)

        self.hplc.set_sample_name(flow_conditions.experiment_id)
        self.hplc.run()

        # timer is over
        for pump in self.pumps:
            if 'solvent' not in pump:
                # save precious starting materials
                self.pumps[pump].stop()
            else:
                # when platform is idle, flush with solvent
                self.pumps[pump].infusion_rate = flow_conditions._individual_inlet_flow_rate

        return 'done'

    def get_platform_ready(self):
        """Here, code is defined that runs once to prepare the platform. These are things like switching on HPLC lamps,
        sending the hplc method"""
        # prepare HPLC
        self.hplc.exit()
        sleep(5)
        print('preparing HPLC')
        self.hplc.switch_lamp_on('192.168.10.107', 10001)
        sleep(5)
        self.hplc.open_clarity_chrom('admin')
        # TODO insert appropriate file here
        self.hplc.load_file('D:\\Data2q\\testopt\\test_opt_method_shortest.met')
        print('HPLC ready')
        for pump in self.pumps.values():
            pump.force = 20

    # and could hold wrapper methods:
    def general_method_1(self):
        pass

    def general_method_2(self):
        pass


class Scheduler:
    """put together procedures and conditions, assign ID, put this to experiment Queue"""

    def __init__(self, graph: dict):

        self.graph = graph
        self.procedure = FlowProcedure(self.graph)
        self.experiment_queue = queue.Queue()
        # start worker
        self.experiment_worker = Thread(target=self.experiment_handler)
        self.experiment_worker.start()

        # create a worker function which compares these two. For efficiency, it will just check if analysed_samples is
        # empty. If not, it will get the respective experimental conditions from started_experiments. Combine the two
        # and drop it to the sql. in future, also hand it to the optimizer
        self.started_experiments = {}
        # later transfer to dict to hold analysis results, for now it only holds analysed sample
        self.analysed_samples = []

        self.data_worker = Thread(target=self.data_handler)
        self.data_worker.start()

        self._experiment_running = False

        # takes necessery steps to initialise the platform
        self.procedure.get_platform_ready()

    @property
    def experiment_running(self) -> bool:
        "returns the flag if experiment is running"
        return self._experiment_running

    @experiment_running.setter
    def experiment_running(self, experiment_running: bool):
        self._experiment_running = experiment_running

    def data_handler(self):
        x = 3
        while True:
            # check if analysis of started experiments returned results already. If so, indicate the run finished and
            # clear the results list
            sleep(1)
            if len(self.analysed_samples) >= x:
                self.experiment_running = False
                print(f'Experiment Running was set to {self.experiment_running} by data handler')
                x += 3

        # while True:
        #     if self.analysed_samples.keys():
        #         # take the first, normally, there should not be more than one in there
        #         analysis_id=self.analysed_samples.keys()[0]
        #         analysis_results = self.analysed_samples.pop(analysis_id)
        #         experimental_conditions=self.started_experiments.pop(analysis_id)
        #         # TODO drop these somewhere: Timestamp : conditions : results
        #     sleep(5)

    # just puts minimal conditions to the queue. Initially, this can be done manually/iterating over parameter space
    def create_experiment(self, conditions: ExperimentConditions) -> None:
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
                self.started_experiments[individual_conditions.experiment_id] = experiment
                new_thread = Thread(target=FlowProcedure.individual_procedure,
                                    args=(self.procedure, individual_conditions,))
                new_thread.start()
                self.experiment_running = True
                print(f'Experiment Running was set to {self.experiment_running} by experiment handler')
                # this should be called when experiment is over
                self.experiment_queue.task_done()
            elif self.experiment_queue.empty and not self.experiment_running:
                # start timer in separate thread. this timer should be killed by having sth in the queue again. When exceeding some time, platform shuts down
                pass


if __name__ == "__main__":
    # FlowGraph as dicitonary
    pump_connection = PumpIO('COM5')
    log = logging.getLogger()
    # missing init parameters
    SugarPlatform = {
        # try to combine two pumps to one. flow rate with ratio gives individual flow rate
        'pumps': {
            'donor': Elite11(pump_connection, address=2, diameter=4.608, volume_syringe=1),
            'donor_solvent': Elite11(pump_connection, address=1, diameter=10.3, volume_syringe=5),
            'acceptor': Elite11(pump_connection, address=4, diameter=10.3, volume_syringe=5),
            'acceptor_solvent': Elite11(pump_connection, address=5, diameter=10.3, volume_syringe=5),
            'activator': Elite11(pump_connection, address=6, diameter=4.608, volume_syringe=1),
            'activator_solvent': Elite11(pump_connection, address=3, diameter=10.3, volume_syringe=5),
            'quench': Elite11(pump_connection, address=0, diameter=14.57, volume_syringe=10),
        },
        'HPLC': ClarityInterface(remote=True, host='192.168.10.11', port=10349,
                                 path_to_executable='C:\\ClarityChrom\\bin\\', instrument_number=2),
        # 'chiller': Huber('COM7'),
        # assume always the same volume from pump to inlet, before T-mixer can be neglected
        'internal_volumes': {'dead_volume_before_reactor': 84.5 * flowchem_ureg.microliter,
                             'volume_mixing': 9.5 * flowchem_ureg.microliter,
                             'volume_reactor': 68.8 * flowchem_ureg.microliter,
                             'dead_volume_to_HPLC': 11 * flowchem_ureg.microliter,
                             }
    }

    fr = FileReceiver('192.168.10.20', 10359, allowed_address='192.168.10.11')
    scheduler = Scheduler(SugarPlatform)

    results_listener = ResultListener('D:\\transferred_chromatograms', '*.txt', scheduler.analysed_samples)

    e = ExperimentConditions()
    e.residence_time = 1 * flowchem_ureg.seconds
    scheduler.create_experiment(e)

    e.residence_time = 2 * flowchem_ureg.seconds
    scheduler.create_experiment(e)

    e.residence_time = 3 * flowchem_ureg.seconds
    scheduler.create_experiment(e)

    e.residence_time = 4 * flowchem_ureg.seconds
    scheduler.create_experiment(e)

    e.residence_time = 5 * flowchem_ureg.seconds
    scheduler.create_experiment(e)

    # TODO when queue empty, after some while everything should be switched off
