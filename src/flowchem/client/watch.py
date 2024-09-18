from .client import get_all_flowchem_devices
import time
import asyncio
import csv
import os
from loguru import logger
import threading


class Watch:

    def __init__(self, experimental_id: int, address: str, discrete_time: float = 1):

        self.devices = get_all_flowchem_devices(IP_machine="local")

        self.address = address

        self.files = dict()

        self.loop = True

        self.experimental_id = experimental_id

        self.discrete_time = discrete_time

    def setup(self):

        os.mkdir(self.address)

        for device_name, device in self.devices.items():

            os.mkdir(self.address + "/" + device_name)

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

        threading.Thread(target=self.run_loop).start()

    def run_loop(self):

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

                logger.info(f"Reading time: {year}-{month:02d}-{day:02d}-{hour:02d}:{minute:02d}:{second:02d}")

                for device_name, device in self.devices.items():

                    for component_name, component in device.components.items():

                        for method in component.component_info.get_methods.keys():

                            value = self.devices[device_name][component_name].get(method).text

                            row = {"time": f"{year}-{month:02d}-{day:02d}-{hour:02d}:{minute:02d}:{second:02d}",
                                   "value": value}

                            self.files[device_name][component_name][method][0].writerow(row)

                toc = time.perf_counter()

    def close(self):

        self.loop = False

        time.sleep(0.5)

        for device_name, device in self.devices.items():

            for component_name, component in device.components.items():

                for method in component.component_info.get_methods.keys():

                    self.files[device_name][component_name][method][1].close()
