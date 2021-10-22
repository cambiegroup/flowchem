import asyncio
import time

import aioserial
from flowchem import HuberChiller

chiller = HuberChiller(aioserial.AioSerial(port='COM1'))


async def main():
    # Set target temperature
    await chiller.set_temperature_setpoint(35)
    # Start temperature control
    await chiller.start_temperature_control()
    # Start recircul/ation
    await chiller.start_circulation()

    for _ in range(6):
        int_temp = await chiller.internal_temperature()
        process_temp = await chiller.process_temperature()
        ret_temp = await chiller.return_temperature()
        water_in_temp = await chiller.cooling_water_temp()
        water_out_temp = await chiller.cooling_water_temp_outflow()

        print("Current temperatures are:\n"
              f"\tInternal = {int_temp}\n"
              f"\tProcess = {process_temp}\n"
              f"\tReturn = {ret_temp}\n"
              f"\tWater Inlet = {water_in_temp}\n"
              f"\tWater Outlet = {water_out_temp}\n")

        time.sleep(10)

    # Stop temperature control
    await chiller.stop_temperature_control()

    time.sleep(10)

    # Stop circulation
    await chiller.stop_circulation()


if __name__ == '__main__':
    asyncio.run(main())
