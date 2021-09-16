from __future__ import annotations

import time

from flowchem.devices.Vapourtec.R4_heater import R4Heater, VapourtecCommand

# Heater - R4
heater = R4Heater(port="COM41")
firmware_version = heater.write_and_read_reply(VapourtecCommand.FIRMWARE)
assert "V3.68" in firmware_version
_reactor_position = 3

temp_to_screen = [80, 60, 40, 30, 70, 50]

for temp in temp_to_screen:

    """
    Each cycle is an experiment, assumption is that the previous point is over.
    """
    print(f"Applying the following conditions: temp={temp}, SOCl2_eq={row['eq']}, temp={row['T']}")

    # 1) Set temperature
    #  This is done first as it might take a while to equilibrate
    heater.set_temperature(channel=_reactor_position, target_temperature=temp, wait=False)

    heater.wait_for_target_temp(channel=_reactor_position)

    time.sleep(60*40)