import queue
from threading import Thread
from time import sleep

# graph: every node has a abstract node name. This should be something descriptive, like Acceptor or chiller
# potentially non unique names could be operated together, so that eg solvent flows from all solvent containers
# everything should be as explicit as possible. These explicit commands can later be transferred to a more abstract from, eg pump from through to.
# For now, since that is not that easy, it's probably better to simply go with explicity, though more detailed and thereby harder to understand and graph-specific code

# later on: take start and end. in the graph, see what is between-take via arguments, if there is valve in between switch it accordingly, if not and these nodes are not connected raise exception

#TODO logging the temperature and getting data from input devices would be cool///also listening on the sockets

class FlowProcedure:

    def individual_procedure(self):
        # this should hold all procedure code, like
        # start pump
        # load sample
        # start timer
        # as variables, flow_conditions are used.#
        # should hold an experiment_done flag which is set from the timer thread. :
        pass

    # and could hold wrapper methods:
    def general_method_1(self):
        pass

    def general_method_2(self):
        pass

    # maybe not even needed, but this let's one still perform tasks while waiting
    def timer(self, duration, action, action_arguments):
        def function_to_execute():
            sleep(duration)
            action(*action_arguments)
        timer_thread = Thread(target=function_to_execute)
        timer_thread.start()


# flow graph in the simplest case consists of attached devices. might be worth doing that for the start
class FlowGraph:
    def __init__(self, path_to_graph):
        self.platform = self.load_platform(path_to_graph)

    def load_platform(self, path_to_graph):
        # with networkx, load a logically ordered version of a graph based on a graphfile
        pass

    def do_calculations(self):
        # iterate through the graph and fill  empty fields by calculating there value after given metrics
        # class holding methods for flow calculations, like internal volume, flow rate residence time, reynolds number and
        #   so on. Check if that already exists
        pass

# initial conditions and experiment code need to be separate!

# could also be a dicitionary
class FlowConditions:
    def __init__(self, condition_id):
        self.condition_id = condition_id
    # container for holding variables. The ones to optimize will be changed by the optimizer algorithm. Also, a
    # condition ID is stored
    pass


class Scheduler:
    def __init__(self, graph: FlowGraph, initial_conditions: dict, procedure: FlowProcedure, experiment_code):
        # initialise the graph and hold it
        # put together procedures and conditions, assign ID, put this to experiment Queue
        self.graph = self.graph_initializer()
        self.experiment_queue = queue.Queue()

        # these should be dropped to the sql after analyse is done
        self.experiment_conditions = initial_conditions # this is simply created from the given initial conditions
        self.experiment_code = experiment_code
        self.procedure = procedure
        self.experiment_queue.put(self.experiment_code)

        self.optimizer = Optimizer()
        self.analyzer = AnalyticsAnalyser()
        # start worker
        self.experiment_handler()

    # def connect_to_database(self, full_db_filepath):
    #     self.database_connector = sqlite3.connect(full_db_filepath)
    #     self.database_cursor = self.database_connector.cursor()
    #     # build the string
    #     row_names = tuple(initial_conditions.keys())
    #     table_creator = f"CREATE TABLE {self.experiment_code} {row_names}"
    #     self.database_cursor.execute(table_creator) #rownames have to be derived from the flow conditions objects
    #
    # def update_database_entry(self):
    #     # used to get optimizer suggestion and analytic results into database
    #     # assemble string
    #     z = "INSERT INTO ? (?,?,?)"
    #     self.database_cursor.execute()
    #     self.database_connector.commit()
    #     pass


    def graph_initializer(self):
        # needs to iterate through the graph object and create the needed objects, if objects are named after individual
        # and meaningful name, resulting code should be easily readable and understandable
        pass

    def create_experiment(self, procedure): # return function object and put that to experiment_queue
        self.experiment_queue.put(procedure)

    def experiment_handler(self):
        # sits in separate thread, checks if previous job is finished and if so grabs new job from queue and executes it in a new thread
        # could be broken by exceptions or by a flag which indicates that the optimizer run is over. Should also work to only conduct one experiment or screenings
        # this one could check if the task is done and call the experiment_queue.task_done()?
        # here all synthesis code will run. This will trigger the hplc and so on.
        # subthread with timing will be created
        # when the timing is over, both threads stop. when this happens, cleaning can be started. But these are very detailed and not so abstract instructions...
        while True:
            sleep(1)
            if self.experiment_queue.not_empty:
                new_thread = Thread(target=self.experiment_queue.get())
                new_thread.start()
                while True:
                    sleep(1)
                    if new_thread.is_alive() is False:
                        break
                # this should be called when experiment is over
                self.experiment_queue.task_done()





class AnalyticsAnalyser:
    # should take a spectrum and analyse it for something. This will always largely depend on mainly the analytical
    # method, but also the type of experiment
    # anyways, the output should be very simple, and directly put to the optimizer queue
    pass

class Optimizer:
    # ideally taking modular optimization algorithm
    # together with previous conditions and results from sql
    # also one or more parameters that should be optimized
    # only modifies the conditions object and puts it to the Queue of scheduler
    pass

# Miscellaneous
# folder watcher needed
# Knauer communication interface needed, with socket as option. This simply sends commands to a socket. The other side
# will then execute the commands. A spectrum will be measured, when this is done it has to be converted to csv file or
# sth and sent back to the optimizer computer, together with a experiment id. Optimizer computer will safe this in a
# folder. The analyzer detects a new file, analyses it and puts it to the optimizer queue

# everything could also be pickled?