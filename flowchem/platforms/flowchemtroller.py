import queue

# graph: every node has a abstract node name. This should be something descriptive, like Acceptor or chiller
# potentially non unique names could be operated together, so that eg solvent flows from all solvent containers
# everything should be as explicit as possible. These explicit commands can later be transferred to a more abstract from, eg pump from through to.
# For now, since that is not that easy, it's probably better to simply go with explicity, though more detailed and thereby harder to understand and graph-specific code

# later on: take start and end. in the graph, see what is between-take via arguments, if there is valve in between switch it accordingly, if not and these nodes are not connected raise exception

class FlowProcedure:

    def individual_procedure(self):
        # this should hold all procedure code, like
        # start pump
        # load sample
        # start timer
        # as variables, flow_conditions are used.
        pass

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

class FlowConditions:
    def __init__(self, condition_id):
        self.condition_id = condition_id
    # container for holding variables. The ones to optimize will be changed by the optimizer algorithm. Also, a
    # condition ID is stored
    pass

class Scheduler:
    def __init__(self, graph: FlowGraph, initial_conditions: FlowConditions, procedure: FlowProcedure):
        # initialise the graph and hold it
        # put together procedures and conditions, assign ID, put this to experiment Queue
        self.graph = self.graph_initializer()
        self.experiment_queue = queue.Queue()
        self.experiment_data = 'some sql database derived object' # this is simply created from the given initial conditions
        # start optimizer
        # start analyser

    def graph_initializer(self):
        # needs to iterate through the graph object and create the needed objects, if objects are named after individual
        # and meaningful name, resulting code should be easily readable and understandable
        pass

    def create_experiment(self, procedure, condition) -> object: # return function object and put that to experiment_queue
        self.experiment_queue.put()

    def experiment_handler(self):
        # sits in separate thread, checks if previous job is finished and if so grabs new job from queue and executes it in a new thread
        pass




class AnalyticsAnalyser:
    # should take a spectrum and analyse it for something. This will always largely depend on mainly the analytical
    # method, but also the type of experiment
    # anyways, the output should be very simple, and written to the sql in position of the ExpID. Alternatively it could
    # be directly put to the optimizer queue, which makes combination with experiments condition a bit more unclear, I think
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
# folder. The analyzer detects a new file, analyses it and writes the results to a sql