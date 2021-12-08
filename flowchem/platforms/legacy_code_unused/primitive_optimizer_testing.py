from flowchem.platforms.sugar_experiment_activation import ExperimentConditions, Scheduler
from flowchem.platforms.flow_conditions import FlowConditions
from flowchem.constants import flowchem_ureg
import logging
from time import sleep


SugarPlatform = {
    # try to combine two pumps to one. flow rate with ratio gives individual flow rate
    'pumps': {
        'donor': 1,

        'activator': 2,

        'quencher': 3,
    },
    'HPLC': 4,

    'sample_loop': 5,
    'chiller': 6,
    'internal_volumes': {'dead_volume_before_reactor': (8) * 2 * flowchem_ureg.microliter,
                         'volume_reactor': 58 * flowchem_ureg.microliter,
                         'dead_volume_to_HPLC': (46 + 28 + 56) * flowchem_ureg.microliter,
                         }
}




class TestFlowProcedure:

    def __init__(self, platform_graph: dict):

        self.log = logging.getLogger(__name__).getChild(__class__.__name__)

    def individual_procedure(self, flow_conditions: FlowConditions):
        # TODO also here, for now this is a workaround for ureg.
        self.log.info(f'Setting Chiller to  {flow_conditions.temperature}')

        self.log.info(f'Chiller successfully set to  {flow_conditions.temperature}')
        self.log.info('Chiller started')


        # set all flow rates
        self.log.info(f'Setting donor flow rate to  {flow_conditions.donor_flow_rate}')

        self.log.info(f'Setting quencher flow rate to  {flow_conditions.quencher_flow_rate}')

        self.log.info('Starting donor pump')
        #
        self.log.info('Starting activator pump')

        self.log.info('Starting quencher pump')

        # start timer
        self.log.info(f'Timer starting, sleep for {flow_conditions.steady_state_time}')
        sleep(flow_conditions.steady_state_time.magnitude)
        self.log.info('Timer over, now take measurement}')

        if pump_1_moving and pump_2_moving:

            # timer is over, start
            self.log.info('Stop pump Donor')

            self.log.info('Stop pump Activator')

            self.log.info(f'setting experiment {scheduler.current_experiment.experiment_id} as finished')
            scheduler.current_experiment._experiment_finished = True

        else:
            # this indicates that a syringe pump blocked. there will be no further handling
            scheduler.current_experiment._experiment_failed = True
            self.log.warning('One syringe pump stopped, likely due to stalling. Please resolve.')

    def get_platform_ready(self):
        """Here, code is defined that runs once to prepare the platform. These are things like switching on HPLC lamps,
        sending the hplc method"""
        # prepare HPLC

        self.log.info('getting the platform ready: HPLC')
        self.log.info('switch on lamps')

        self.log.info('load method')

        # Todo fill
        # commander.load_file("opendedicatedproject") # open a project for measurements

        # fill the activator to the hamilton syringe

        self.log.info('getting the platform ready: setting HPLC max pressure')


if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger("__main__").setLevel(logging.DEBUG)
    scheduler = Scheduler(SugarPlatform, procedure=TestFlowProcedure)
    pump_1_moving = True
    pump_2_moving = True
    scheduler.create_experiment(ExperimentConditions(temperature='22 °C', residence_time='3 s'))
    print('first experiment successful')
    #pump_1_moving = False
    scheduler.create_experiment(ExperimentConditions(temperature='22 °C', residence_time='3 s'))

    sleep(1)

# find way to stimulate waiting for analysis and geeting the result