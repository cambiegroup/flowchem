from .client import get_all_flowchem_devices
import time
import asyncio
import csv
import os
from loguru import logger
import threading
import toml
import inspect


class Watch:

    def __init__(self,
                 experimental_id: int | str,
                 address: str,
                 discrete_time: float = 1,
                 add_info: dict | None = None):

        self.devices = get_all_flowchem_devices(IP_machine="local")

        self.files = dict()

        self.loop = True

        self.experimental_id = experimental_id

        self.discrete_time = discrete_time

        self.address = address+f"_experiment_id_{self.experimental_id}"

        self.add_info = add_info

        self.inspect = dict()

    def setup(self):

        try:
            os.mkdir(self.address)
        except:
            logger.info(f"Recording folder {self.address} already exist. The supervisor will overwrite it")

        logger.add(self.address+"/log.log", level="INFO")

        if self.add_info is not None:

            file = open(self.address+f"/Information_id_{self.experimental_id}.toml", "w")
            toml.dump(self.add_info, file)
            file.close()

        for device_name, device in self.devices.items():

            try:
                os.mkdir(self.address + "/" + device_name)
            except:
                logger.info(f"Recording device folder {device_name} already exist. The supervisor will overwrite it")

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

        threading.Thread(target=self.__run_loop).start()

    def __run_loop(self):

        toc = time.perf_counter()

        while self.loop:

            current_time = time.localtime()

            # Extract the components
            year = current_time.tm_year
            month = current_time.tm_mon
            day = current_time.tm_mday
            hour = current_time.tm_hour
            minute = current_time.tm_min
            second = current_time.tm_sec

            if time.perf_counter() - toc >= self.discrete_time:

                #logger.info(f"Reading time: {year}-{month:02d}-{day:02d}-{hour:02d}:{minute:02d}:{second:02d}")

                for device_name, device in self.devices.items():

                    for component_name, component in device.components.items():

                        for method in component.component_info.get_methods.keys():

                            value = self.devices[device_name][component_name].get(method).text

                            row = {"time": f"{year}-{month:02d}-{day:02d}-{hour:02d}:{minute:02d}:{second:02d}",
                                   "value": value}

                            self.files[device_name][component_name][method][0].writerow(row)

                            if device_name in self.inspect.keys():

                                if component_name in self.inspect[device_name].keys():

                                    if method in self.inspect[device_name][component_name].keys():

                                        rule = self.inspect[device_name][component_name][method]

                                        if not self.__rule_tranlate(value, rule):

                                            logger.error(f"The {method} of the component/device: {component_name}"
                                                         f"/{device_name} should obey the rule:"
                                                         f" {inspect.getsource(rule)}, however it return:"
                                                         f" {value}")

                toc = time.perf_counter()

    def close(self):

        self.loop = False

        time.sleep(0.5)

        for device_name, device in self.devices.items():

            for component_name, component in device.components.items():

                for method in component.component_info.get_methods.keys():

                    self.files[device_name][component_name][method][1].close()

    def inset_inspect(self, device: str, component: str, command: str, condition):

        self.inspect[device] = {component: {command: condition}}

    def __rule_tranlate(self, value, rule)->bool:

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
                     logger.error(f"It was not possible to verify the received value {value} with the rule:"
                                  f" {inspect.getsource(rule)}")
                     return True
