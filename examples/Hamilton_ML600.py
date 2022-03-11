""" Example file for controlling Hamilton ML600 pumps with fllowchem """
import asyncio
from flowchem import ML600

conf_pump1 = {
    "port": "COM12",
    "address": 1,
    "name": "water",
    "syringe_volume": 5,
}

conf_pump2 = {
    "port": "COM12",
    "address": 2,
    "name": "acetone",
    "syringe_volume": 5,
}


async def example(p1: ML600, p2: ML600):
    """Example code for Hamilton ML600 pumps"""
    # Initialize pumps.
    await p1.initialize_pump()
    await p2.initialize_pump()

    # We can also run commands on different pumps concurrently
    await asyncio.gather(p1.initialize_pump(), p2.initialize_pump())

    # Let's set the valve position to inlet
    await p1.set_valve_position(ML600.ValvePositionName.INPUT)
    await p2.set_valve_position(ML600.ValvePositionName.INPUT)

    # Let's change valve positions a couple of time
    print(f"Pump 1 valve position is now {await p1.get_valve_position()}")
    await p1.set_valve_position(ML600.ValvePositionName.OUTPUT)
    print(f"Pump 1 valve position is now {await p1.get_valve_position()}")
    await p1.set_valve_position(ML600.ValvePositionName.INPUT)

    # Valve position commands are special because, as default, they return only at the end of the movement.
    # You can avoid this by passing wait_for_movement_end=False.
    # The reason for this behaviour is that, while it is intuitive the need to wait for a syringe movement,
    # awaiting for the end of a brief valve movement is often forgotten.
    await p1.set_valve_position(
        ML600.ValvePositionName.OUTPUT, wait_for_movement_end=False
    )
    print(f"Pump 1 valve position is now {await p1.get_valve_position()}")
    await p1.set_valve_position(ML600.ValvePositionName.INPUT)

    # Note that all the speed parameters are intended in seconds for full stroke, i.e. seconds for syringe_volume
    await p1.to_volume(target_volume=0, speed=10)
    # We suggest to call the class methods with the full keywords and not positionally.
    # For example this line is a lot less readable:
    await p2.to_volume(0, 10)

    # Then we can rapidly fill our syringes
    await asyncio.gather(
        p1.to_volume(p1.syringe_volume, speed=10),
        p2.to_volume(p2.syringe_volume, speed=10),
    )
    # And let's wait for the movement to be over
    await asyncio.gather(p1.wait_until_idle(), p2.wait_until_idle())

    # And pump in the outlet port
    await p1.set_valve_position(ML600.ValvePositionName.OUTPUT)
    await p2.set_valve_position(ML600.ValvePositionName.OUTPUT)

    # If you find the stroke per second not convienent, the utility function ML600.flowrate_to_seconds_per_stroke
    # can be used to translate flow rate in seconds per stroke.
    speed1 = p1.flowrate_to_seconds_per_stroke(flowrate_in_ml_min=0.5)
    speed2 = p1.flowrate_to_seconds_per_stroke(flowrate_in_ml_min=0.75)
    await p1.to_volume(target_volume=0, speed=speed1)
    await p2.to_volume(target_volume=0, speed=speed2)


pump1 = ML600.from_config(conf_pump1)
pump2 = ML600.from_config(conf_pump2)

asyncio.run(example(pump1, pump2))
