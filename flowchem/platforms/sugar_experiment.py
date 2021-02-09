from time import sleep
from flowchem.devices.Petite_Fleur_chiller import Huber
import queue
from threading import Thread

# from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
# TODO create simulation classes at some point


class ExperimentConditions:
    """This is actively changed, either by human or by optimizer. Goes into the queue.
    When the conditions are taken from the queue, a FlowConditions object is derived from ExperimentCondition.
    ExperimentConditions has to be dropped into a database, eventually, with analytic results and the optimizer activated"""

    def __init__(self, condition_id):
        self.condition_id = condition_id  # this should be generated and passed on to the analyzer
        # when fully analyzed, this, together with analytical results can be dropped to the database

    # fixed, only changed for a new experiment sequence (if stock solution changes)
    _stock_concentration_donor = 1  # M
    _stock_concentration_acceptor = 1  # M
    _stock_concentration_activator = 1  # M
    _stock_concentration_quencher = 1
    # how many reactor volumes until steady state reached
    _reactor_volumes = 3

    # mutable
    residence_time = 60  # sec
    concentration_donor = 0.25
    acceptor_equivalents = 1.2
    activator_equivalents = 1.5
    quencher_equivalents = 5
    temperature = -80

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



class FlowConditions:
    """From  experiment conditions, flow conditions can be derived, which happens right before each experiment.
    Basically, just to separate off redundant data.
    Links Experiment Conditions to platform.
    All private parameters are only internally needed for calculation (and maybe as checkpoints for simpler testing).
    """

    # these can be calculated, from eqach pump 'package', the flow rate should be the same I suppose
    def __init__(self, experiment_conditions: ExperimentConditions,
                 flow_platform: dict):  # for now, the flowplatform is handed in as a manually written dict and abstraction still low
        self._concentration_donor = experiment_conditions.concentration_donor
        self._concentration_acceptor = self.get_dependent_concentration(self._concentration_donor,
                                                                        experiment_conditions.acceptor_equivalents)
        self._concentration_activator = self.get_dependent_concentration(self._concentration_donor,
                                                                         experiment_conditions.activator_equivalents)
        self._total_flow_rate = self.get_flow_rate(flow_platform['internal_volumes']['volume_reactor'],
                                              experiment_conditions.residence_time)

        # since setting ratios by concentration rather than flow rate (and thereby, always having the same flowrate ratios), some abstraction is already possible
        self._individual_inlet_flow_rate = round(self._total_flow_rate / 3,
                                                 3)  # 3 is the number of mating inlets, easily

        # flow rates on pump base by required dilution
        # trim output reasonably
        # explicit better than implicit, these could be dropped as control, but a bit verbose
        self._dilution_acceptor = self.get_dilution_ratio(experiment_conditions.stock_concentration_acceptor,
                                                          self._concentration_acceptor)
        # better readability
        self.platform_volumes = flow_platform['internal_volumes']

        self.acceptor_flow_rate = self._individual_inlet_flow_rate * self._dilution_acceptor
        self.acceptor_solvent_flow_rate = self._individual_inlet_flow_rate - self.acceptor_flow_rate

        self._dilution_donor = self.get_dilution_ratio(experiment_conditions.stock_concentration_donor,
                                                       self._concentration_donor)
        self.donor_flow_rate = self._individual_inlet_flow_rate * self._dilution_donor
        self.donor_solvent_flow_rate = self._individual_inlet_flow_rate - self.donor_flow_rate

        self._dilution_activator = self.get_dilution_ratio(experiment_conditions.stock_concentration_activator,
                                                           self._concentration_activator)
        self.activator_flow_rate = self._individual_inlet_flow_rate * self._dilution_activator
        self.activator_solvent_flow_rate = self._individual_inlet_flow_rate - self.activator_flow_rate

        self.quencher_flow_rate = (self._concentration_donor / experiment_conditions.stock_concentration_quencher) * \
                                  self._individual_inlet_flow_rate

        self.temperature = experiment_conditions.temperature

        self._time_start_till_end = round((self.platform_volumes['dead_volume_before_reactor'] * 3 +
                                           self.platform_volumes['volume_mixing'] +
                                           self.platform_volumes['volume_reactor']) / self._total_flow_rate + \
                                          self.platform_volumes['dead_volume_to_HPLC'] / (self._total_flow_rate +
                                                                                         self.quencher_flow_rate))

        self.steady_state_time = self._time_start_till_end + \
                                 experiment_conditions.residence_time * experiment_conditions.reactor_volumes

    def get_dependent_concentration(self, limiting_reagent_concentration: float, equivalents: float):
        dependent_concentration = limiting_reagent_concentration * equivalents

        return dependent_concentration

    def get_dilution_ratio(self, stock_concentration: float, concentration_after_dilution: float):
        dilution_ratio = concentration_after_dilution / stock_concentration

        return round(dilution_ratio, 2)

    def get_flow_rate(self, relevant_volume: float, residence_time: int):
        # residence time could be float, but I think sec is granular enough?
        flow_rate = relevant_volume / residence_time

        return round(flow_rate, 3)


class FlowProcedure:

    def __init__(self, platform_graph: dict):
        self.pumps = platform_graph['pumps']
        self.hplc = platform_graph['HPLC']
        self.chiller = platform_graph['chiller']

    def individual_procedure(self, flow_conditions: FlowConditions):
        self.chiller.set_temperature(flow_conditions.temperature)
        self.chiller.start()
        while (abs(self.chiller.get_temperature()) - abs(flow_conditions.temperature)) > 2:
            sleep(10)
            print('Chiller waiting for temperature')

        # set all flow rates
        self.pumps['donor'].infusion_rate = flow_conditions.donor_flow_rate
        self.pumps['donor_solvent'].infusion_rate = flow_conditions.donor_solvent_flow_rate
        self.pumps['acceptor'].infusion_rate = flow_conditions.acceptor_flow_rate
        self.pumps['acceptor_solvent'].infusion_rate = flow_conditions.acceptor_solvent_flow_rate
        self.pumps['activator'].infusion_rate = flow_conditions.activator_flow_rate
        self.pumps['activator_solvent'].infusion_rate = flow_conditions.activator_solvent_flow_rate
        self.pumps['quench'].infusion_rate = flow_conditions.quencher_flow_rate

        for pump in self.pumps:
            pump.run()
        # start timer
        sleep(flow_conditions.steady_state_time)
        # timer is over
        for pump in self.pumps:
            if 'solvent' not in pump:
                # save precious starting materials
                self.pumps[pump].stop()
            else:
                # when platform is idle, flush with solvent
                self.pumps[pump].infusion_rate= flow_conditions._individual_inlet_flow_rate

        # inject into HPLC


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
        self.experiment_handler()

        # create a worker function which compares these two. For efficiency, it will just check if analysed_samples is
        # empty. If not, it will get the respective experimental conditions from started_experiments. Combine the two
        # and drop it to the sql. in future, also hand it to the optimizer
        self.started_experiments = {}
        self.analysed_samples = {}


    # just puts minimal conditions to the queue. Initially, this can be done manually/iterating over parameter space
    def create_experiment(self, conditions: ExperimentConditions) -> None:
        self.experiment_queue.put(conditions)

    def experiment_handler(self):
        """sits in separate thread, checks if previous job is finished and if so grabs new job from queue and executes it in a new thread"""
        while True:
            sleep(1)
            if self.experiment_queue.not_empty:
                # get raw experimental data, derive actual platform parameters, create sequence function and execute that in a thread
                experiment: ExperimentConditions = self.experiment_queue.get()
                individual_conditions = FlowConditions(experiment, self.graph)
                new_thread = Thread(target=FlowProcedure.individual_procedure, args=individual_conditions)
                new_thread.start()
                while True:
                    sleep(1)
                    if new_thread.is_alive() is False:
                        break
                # this should be called when experiment is over
                self.experiment_queue.task_done()


# TODO remove DUMMYCLASSES for testing
class PumpIO:
    def __init__(self, sth):
        print('Dummy PumpIO on ' + sth)


class Elite11:
    def __init__(self, pump_conn: PumpIO, address):
        print(f'Dummy Pump with address: {address}')


# FlowGraph as dicitonary
pump_connection = PumpIO('COM5')

# missing init parameters
SugarPlatform = {
    # try to combine two pumps to one. flow rate with ratio gives individual flow rate
    'pumps': {
        'donor': Elite11(pump_connection, address=0),
        'donor_solvent': Elite11(pump_connection, address=1),
        'acceptor': Elite11(pump_connection, address=2),
        'acceptor_solvent': Elite11(pump_connection, address=3),
        'activator': Elite11(pump_connection, address=4),
        'activator_solvent': Elite11(pump_connection, address=5),
        'quench': Elite11(pump_connection, address=6),
    },
    'HPLC': print('hplc'),
    'chiller': Huber('COM7'),
    # assume always the same volume from pump to inlet, before T-mixer can be neglected
    'internal_volumes': {'dead_volume_before_reactor': 100,  # TODO determin
                         'volume_mixing': 9.5,  # µL
                         'volume_reactor': 68.8,
                         'dead_volume_to_HPLC': 100  # TODO determine
                         }  # µL
}

# TODO either devices have to round to reasonable numbers or it has to be done internally. Using pint would be good

if __name__ == "__main__":
    print('test')
