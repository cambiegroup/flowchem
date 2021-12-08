from flowchem.platforms.Saving_Retrieving import SaveRetrieveData
import queue
from threading import Thread
from pathlib import Path
from flowchem.platforms.experiment_conditions import ExperimentConditions
import logging
from time import sleep
from flowchem.constants import flowchem_ureg
import datetime
from flowchem.platforms.flow_conditions import FlowConditions
from flowchem.platforms.sugar_activation_procedure import FlowProcedure

class Scheduler:
    """put together procedures and conditions, assign ID, put this to experiment Queue"""

    def __init__(self, graph: dict, experiment_name: str = "",
                 analysis_results: Path = Path(r'D:/transferred_chromatograms'),
                 procedure=FlowProcedure):

        self.graph = graph
        self.log = logging.getLogger(__name__).getChild(__class__.__name__)
        self.procedure = procedure(self.graph, self)
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
                f'{self.current_experiment.experiment_id} with a new experiment')

    @experiment_waiting_for_analysis.setter
    def experiment_waiting_for_analysis(self, new_experiment_waiting: ExperimentConditions):
        if not self.experiment_waiting_for_analysis or not new_experiment_waiting:
            self._experiment_waiting_for_analysis = new_experiment_waiting
        else:
            self.log.warning(
                f'Something is trying to replace experiment {self.experiment_waiting_for_analysis.experiment_id} '
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
                        self.experiment_saving_loading.save_data(f"{self.experiment_name}_{self.experiment_waiting_for_analysis.experiment_id}_{self.experiment_waiting_for_analysis.temperature}", self.experiment_waiting_for_analysis)
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

                    # makes sure that performed experiment is safed. If transmission of chromatogram fails or platform
                    # needs to be stopped, it is thereby still possible to retrieve data
                    self.experiment_saving_loading.save_data(
                        f"{self.experiment_name}_{self.experiment_waiting_for_analysis.experiment_id}_{self.experiment_waiting_for_analysis.temperature}",
                        self.experiment_waiting_for_analysis)

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


            elif self.experiment_queue.empty() and not self.current_experiment:
                # start timer in separate thread. this timer should be killed by having sth in the queue again.
                # When exceeding some time, platform should shut down

                user_input = Thread(target=self.create_experiments_from_user_input)
                user_input.start()
                user_input.join()