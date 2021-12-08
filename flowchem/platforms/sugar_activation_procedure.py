import datetime
import asyncio
from flowchem.platforms.flow_conditions import FlowConditions
from time import sleep
from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpStalled
from flowchem.devices.Knauer.HPLC_control import ClarityInterface
import logging
from flowchem.platforms.platform_scheduler import Scheduler
from flowchem.constants import flowchem_ureg
from flowchem.devices.Petite_Fleur_chiller import Huber


class FlowProcedure:

    def __init__(self, platform_graph: dict, scheduler: Scheduler):
        self.pumps = platform_graph['pumps']
        self.hplc: ClarityInterface = platform_graph['HPLC']
        self.chiller: Huber = platform_graph['chiller']
        self.sample_loop = platform_graph['sample_loop']
        self.log = logging.getLogger(__name__).getChild(__class__.__name__)
        self.scheduler = scheduler

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

        if flow_conditions.activator == True:
            self.log.info('Starting activator pump')
            self.pumps['activator'].run()
        elif flow_conditions.activator == False:
            self.pumps['pure_DCM'].infusion_rate = flow_conditions.activator_flow_rate.m_as('mL/min')
            self.log.info('Starting pure solvent pump')
            self.pumps['pure_DCM'].run()
        else:
            raise ValueError('ExperimentConditions.Activator can only be boolean, you supplied sth else')

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

            self.hplc.set_sample_name(self.scheduler.current_experiment.experiment_id)

            while self.scheduler.experiment_waiting_for_analysis:
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
            self.pumps['pure_DCM'].stop()

            self.sample_loop.set_valve_position_sync(1)

            self.log.info(f'setting experiment {self.scheduler.current_experiment.experiment_id} as finished')
            self.scheduler.current_experiment._experiment_finished = True
            self.pumps['quencher'].stop_flow()

        except PumpStalled:
            # this indicates that a syringe pump blocked. there will be no further handling
            self.scheduler.current_experiment._experiment_failed = True
            self.pumps['donor'].stop()
            self.pumps['activator'].stop()
            self.log.warning('One syringe pump stopped, likely due to stalling. Please resolve.')
            self.pumps['quencher'].stop_flow()

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


