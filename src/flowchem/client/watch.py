from flowchem.client.client import get_all_flowchem_devices
import time
import asyncio
import csv
import os
from loguru import logger
import threading
import toml
import inspect
from typing import Callable


class Watch:
    """
    A class used to monitor and log the behavior of flowchem devices in real-time, recording data from devices
    and components at a specified time interval. It also allows setting custom conditions (rules) to monitor
    specific values from the devices and raise errors if the conditions are violated.

    Attributes:
    ----------
    experimental_id : int | str
        Unique identifier for the experiment being monitored.

    address : str
        Directory path where logs and data will be saved, appended with experiment id.

    discrete_time : float
        Time interval in seconds at which data from the devices is logged.

    add_info : dict | None
        Additional information related to the experiment to be stored as a `.toml` file.

    devices : dict
        A dictionary of all flowchem devices obtained from the `get_all_flowchem_devices()` function.

    files : dict
        A dictionary to hold file handlers for writing CSV logs from devices.

    loop : bool
        A boolean flag controlling the logging loop in the background thread.

    inspect : dict
        A dictionary to store inspection rules (conditions) for specific devices, components, and commands.


    Methods:
    -------
    __init__(experimental_id, address, discrete_time=1, add_info=None):
        Initializes the Watch object with experiment id, logging address, and time interval for logging.

    setup():
        Sets up logging directories, initializes CSV files for devices and components, and stores additional
        experiment information if provided.

    run():
        Starts a background thread that runs a logging loop, collecting data at specified intervals.

    __run_loop():
        Internal method that runs in a thread, periodically logging the values from the devices and comparing them
        against custom rules if provided.

    close():
        Stops the logging loop, closes all open files, and terminates the background thread.

    inset_inspect(device: str, component: str, command: str, condition: Callable):
        Inserts an inspection rule for a specific device, component, and command, defining the condition that the
        value must satisfy.

    __rule_tranlate(value, rule) -> bool:
        Translates and evaluates the received value against a provided rule, converting the value to a numeric
        format if necessary. Returns True if the condition is satisfied, or logs an error if not.
    """

    def __init__(self,
                 experimental_id: int | str,
                 address: str,
                 discrete_time: float = 1,
                 add_info: dict | None = None):
        """
        Initializes the Watch instance with an experiment id, a logging directory, a time interval,
        and optional additional information to store.

        Args:
            experimental_id: Unique identifier for the experiment (can be an integer or a string).
            address: Directory where experiment logs and data will be stored.
            discrete_time: Time interval (in seconds) at which device data will be logged. Default is 1 second.
            add_info: Optional dictionary containing additional experiment information to save as a `.toml` file.
        """
        self.devices = get_all_flowchem_devices(IP_machine="local")
        self.files = dict()
        self.loop = True
        self.experimental_id = experimental_id
        self.discrete_time = discrete_time
        self.address = address + f"_experiment_id_{self.experimental_id}"
        self.add_info = add_info
        self.inspect = dict()

    def setup(self):
        """
        Sets up the environment for logging by creating directories for storing data and logs for each
        device and component. Also saves additional information if provided in the `add_info` attribute.

        This method initializes CSV files where component data is written during the logging loop.
        """
        try:
            os.mkdir(self.address)
        except:
            logger.info(f"Recording folder {self.address} already exists. The supervisor will overwrite it")

        logger.add(self.address + "/Watchlog.log", level="INFO")

        if self.add_info is not None:
            with open(self.address + f"/Information_id_{self.experimental_id}.toml", "w") as file:
                toml.dump(self.add_info, file)

        for device_name, device in self.devices.items():
            try:
                os.mkdir(self.address + "/" + device_name)
            except:
                logger.info(f"Recording device folder {device_name} already exists. The supervisor will overwrite it")

            logger.info(f"Recording folder from device: {device_name} was created")

            self.files[device_name] = dict()

            for component_name, component in device.components.items():
                self.files[device_name][component_name] = dict()

                for method in component.component_info.get_methods.keys():
                    file = open(f"{self.address}/{device_name}/{component_name}_{method}.csv", mode="w", newline="")
                    writer = csv.DictWriter(file, fieldnames=["time", "value"])
                    writer.writeheader()
                    self.files[device_name][component_name][method] = [writer, file]

    def run(self):
        """
        Starts the data logging process by launching a background thread that periodically logs device and
        component data at the time interval specified by `discrete_time`.
        """
        threading.Thread(target=self.__run_loop).start()

    def __run_loop(self):
        """
        Internal method that runs the actual logging loop. It collects data from each device and component at
        regular intervals, stores the data in CSV files, and checks the data against defined inspection rules.
        This method runs until the `close()` method is called.
        """
        toc = time.perf_counter()

        while self.loop:
            current_time = time.localtime()
            year, month, day = current_time.tm_year, current_time.tm_mon, current_time.tm_mday
            hour, minute, second = current_time.tm_hour, current_time.tm_min, current_time.tm_sec

            if time.perf_counter() - toc >= self.discrete_time:
                for device_name, device in self.devices.items():
                    for component_name, component in device.components.items():
                        for method in component.component_info.get_methods.keys():
                            value = self.devices[device_name][component_name].get(method).text
                            row = {
                                "time": f"{year}-{month:02d}-{day:02d}-{hour:02d}:{minute:02d}:{second:02d}",
                                "value": value
                            }
                            self.files[device_name][component_name][method][0].writerow(row)

                            if device_name in self.inspect.keys():
                                if component_name in self.inspect[device_name].keys():
                                    if method in self.inspect[device_name][component_name].keys():
                                        rule = self.inspect[device_name][component_name][method]
                                        if not self.__rule_tranlate(value, rule):
                                            logger.error(f"The {method} of the component/device: {component_name}/"
                                                         f"{device_name} should obey the rule: {inspect.getsource(rule)},"
                                                         f" however it returned: {value}")

                toc = time.perf_counter()

    def close(self):
        """
        Stops the logging process, terminates the background thread, and closes all open CSV files
        where device data was being logged.
        """
        self.loop = False
        time.sleep(0.5)

        for device_name, device in self.devices.items():
            for component_name, component in device.components.items():
                for method in component.component_info.get_methods.keys():
                    self.files[device_name][component_name][method][1].close()

    def inset_inspect(self, device: str, component: str, command: str, condition: Callable):
        """
        Inserts a rule (condition) to inspect the data from a specific device, component, and command.
        The rule is a callable that takes the value as an argument and returns True if the condition is met,
        or False if it is violated.

        Args:
            device: Name of the device to inspect.
            component: Name of the component within the device to inspect.
            command: The method/command on the component to inspect.
            condition: A lambda function representing the condition that the data should satisfy (e.g., lambda x: x < 1).
        """
        self.inspect[device] = {component: {command: condition}}

    def __rule_tranlate(self, value, rule) -> bool:
        """
        Evaluates a value against a provided rule, attempting to convert the value to a numeric format
        if necessary before applying the rule. Logs an error if the rule cannot be applied or the value
        violates the rule.

        Args:
            value: The value retrieved from the device component to be checked.
            rule: The rule (a callable) that should be applied to the value.

        Returns:
            bool: True if the value satisfies the rule, False otherwise.
        """
        try:
            return rule(value)
        except:
            try:
                x = float(value)
                return rule(x)
            except:
                try:
                    x = float(value.split()[0])
                    return rule(x)
                except:
                    logger.error(f"It was not possible to verify the received value {value} with the rule: "
                                 f"{inspect.getsource(rule)}")
                    return True


if __name__ == "__main__":

    address = os.path.dirname(os.path.abspath(__file__))

    inf = {"some_information": "oiiuasd4712", "id_io": 8587}

    watch = Watch(experimental_id=1, address=address + "/recording", discrete_time=2, add_info=inf)

    watch.setup()

    watch.inset_inspect(device="fake-device",
                        component="FakeComponent",
                        command="fake_receive_data",
                        condition=lambda x: x < 0.4)

    watch.run()

    time.sleep(10)

    watch.close()