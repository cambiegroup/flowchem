from flowchem.client.client import get_all_flowchem_devices
from flowchem.client.device_client import FlowchemDeviceClient

from datetime import datetime
import time
import asyncio
import csv
import os
from pathlib import Path
from loguru import logger
import threading
import toml
import inspect
from typing import Callable, Any


class Watch:

    def __init__(self, devices: dict[str, FlowchemDeviceClient],
                 address: Path | str,
                 experimental_id: str | int = 1,
                 information_to_file: dict[str, Any] | None = None):

        self.devices = devices

        self.experimental_id = experimental_id

        self.add_info = information_to_file

        self.loop = True

        self.file: dict[str, Any] = dict()

        self.address = os.path.join(address,f"_experiment_id_{self.experimental_id}")

        self.inspect: dict[str, Any] = dict()

        self.start_watch = time.localtime()

        self.devices_to_watch: list[str] = None

        self.discrete_time = 2

        if not os.path.exists(self.address):
            os.mkdir(self.address)
            logger.add(self.address + "/Watchlog.log", level="INFO")
        else:
            logger.add(self.address + "/Watchlog.log", level="INFO")
            logger.info(f"Recording folder {self.address} already exists. The supervisor will overwrite it")

        if self.add_info is not None:
            with open(self.address + f"/Information_id_{self.experimental_id}.toml", "w") as file:
                toml.dump(self.add_info, file)

    def setup_watch_client(self,
                           devices_to_watch: list[str] | dict[str, FlowchemDeviceClient],
                           discrete_time: float = 2.0):
        """
        Sets up the environment for logging by creating directories for storing data and logs for each
        device and component. Also saves additional information if provided in the `add_info` attribute.

        This method initializes CSV files where component data is written during the logging loop.
        """

        if type(devices_to_watch) == dict:

            devices_to_watch = [d for d in devices_to_watch.keys()]

        self.devices_to_watch = devices_to_watch

        self.discrete_time = discrete_time

        if self.devices_to_watch:

            row_name = ["time"]

            for device_name in self.devices_to_watch:

                for component in self.devices[device_name].components.values():

                    component_name = component.component_info.name

                    for method in component.component_info.get_methods.keys():

                        row_name.append(f"{device_name}/{component_name}/{method}")

            file = open(f"{self.address}/data.csv", mode="w", newline="")

            writer = csv.DictWriter(file, fieldnames=row_name)

            writer.writeheader()

            self.file = {"write": writer, "file": file}

            logger.info(f"Recording of the devices: {self.devices_to_watch} was setup")

    def run(self):
        """
        Starts the data logging process by launching a background thread that periodically logs device and
        component data at the time interval specified by `discrete_time`.
        """
        if self.devices_to_watch is not None:

            threading.Thread(target=self.__run_loop).start()

        else:

            logger.warning(f"There is not device to watch. Be sure that the devices were setup in the "
                           f"class initialization: Watch(...,devices_towatch=[...]")

    def __run_loop(self):
        """
        Internal method that runs the actual logging loop. It collects data from each device and component at
        regular intervals, stores the data in CSV files, and checks the data against defined inspection rules.
        This method runs until the `close()` method is called.
        """
        toc = time.perf_counter()

        while self.loop:

            if time.perf_counter() - toc >= self.discrete_time:
                row = dict()
                for device_name in self.devices_to_watch:

                    for component in self.devices[device_name].components.values():

                        component_name = component.component_info.name

                        for method in component.component_info.get_methods.keys():

                            current_time = time.localtime()

                            value = self.devices[device_name][component_name].get(method).text

                            year, month, day = current_time.tm_year, current_time.tm_mon, current_time.tm_mday
                            hour, minute, second = current_time.tm_hour, current_time.tm_min, current_time.tm_sec

                            row["time"] = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"

                            row[f"{device_name}/{component.component_info.name}/{method}"] = value

                            if device_name in self.inspect.keys():

                                if component_name in self.inspect[device_name].keys():

                                    if method in self.inspect[device_name][component_name].keys():

                                        rule = self.inspect[device_name][component_name][method]

                                        if not self.__rule_tranlate(value, rule):
                                            logger.error(f"The {method} of the component/device: {component_name}/"
                                                         f"{device_name} should obey the rule: {inspect.getsource(rule)},"
                                                         f" however it returned: {value}")
                self.file["write"].writerow(row)

                toc = time.perf_counter()

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

    def close(self):
        """
        Stops the logging process, terminates the background thread, and closes all open CSV files
        where device data was being logged.
        """

        """ Getting the current logs """
        # Convert time.localtime() to a datetime object
        specific_time = datetime(*self.start_watch[:6])

        logging_dir = os.path.join(os.path.dirname(__file__), "loggings")

        components_logs = dict()

        lines = []

        for devices_name in os.listdir(logging_dir):

            subdirectories = os.path.join(logging_dir,devices_name)

            for f in os.listdir(subdirectories):

                # Open the log file and filter the lines based on the target time
                with open(os.path.join(subdirectories, f), 'r') as log_file:
                    for line in log_file:
                        # Extract the timestamp part of the log line (assuming it's the first part)
                        timestamp_str = line.split('-Endpoint')[0]
                        log_time = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%f%z').replace(tzinfo=None)

                        # Compare the log time with the specific time
                        if log_time >= specific_time:

                            lines.append((log_time, line))

        # Sort the list of log lines by the log_time
        sorted_lines = sorted(lines, key=lambda x: x[0])

        # Write the sorted lines into the output file
        with open(os.path.join(self.address, "loggings.log"), 'w') as output:
            for _, line in sorted_lines:
                output.write(line)

        if self.devices_to_watch is not None:
            if self.loop:
                self.loop = False
            time.sleep(0.5)
            self.file["file"].close()



if __name__ == "__main__":

    address = os.path.dirname(os.path.abspath(__file__))

    devices = get_all_flowchem_devices(IP_machine="local")

    inf = {"some_information": "---", "id_io": 0000}

    watch = Watch(devices=devices,
                  address=address,
                  information_to_file=inf,
                  experimental_id=0)

    watch.setup_watch_client(devices_to_watch=devices)

    watch.inset_inspect(device="fake-device",
                        component="FakeComponent",
                        command="fake_receive_data",
                        condition=lambda x: x < 0.4)

    watch.run()

    time.sleep(10)

    watch.close()