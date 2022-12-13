import asyncio
from flowchem.components.devices.Harvard_Apparatus.HA_elite11 import (
    HarvardApparatusPumpIO,Elite11InfuseOnly
)

async def injection_loop(Equiv_dict:dict):
    Total_infusion_rate = 0.02 #ml/min
    vol_dict = {
        "SMIS": 0.225, "EY": Equiv_dict["EY"]*20, "Activator": Equiv_dict["H3BO3"]*1, "Quencher":Equiv_dict["DIPEA"]*0.174, "Solvent": 0
    }
    flow_unit = Total_infusion_rate /sum(vol_dict.values())
    Infusion_rate_dict = dict((s, str(vol_dict[s]*flow_unit)+" ml/min") for s in vol_dict)
    # print(Infusion_rate_dict)

    fill_tube_time_1 = 2.0* (0.0106/(flow_unit*(vol_dict["EY"] + vol_dict["Activator"]))) #min #
    fill_tube_time_2 = 1.5* ((0.0212+0.1)/Total_infusion_rate) #min




    pump_EosinY = Elite11InfuseOnly.from_config(
        port="COM5", syringe_volume="1 ml", diameter="4.61 mm", address=0
    ) # Always the pump connect to the computer have to be address 0
    pump_Solvent = Elite11InfuseOnly.from_config(
        port="COM5", syringe_volume="10 ml", diameter="14.57 mm", address=3
    )
    pump_Activator = Elite11InfuseOnly.from_config(
        port="COM5", syringe_volume="1 ml", diameter="4.61 mm", address=4
    )
    pump_Quencher = Elite11InfuseOnly.from_config(
        port="COM5", syringe_volume="2.5 ml", diameter="7.28 mm", address=5
    )
    pump_SMIS = Elite11InfuseOnly.from_config(
        port="COM5", syringe_volume="2.5 ml", diameter="7.28 mm", address=6
    )

    await pump_EosinY.initialize()
    await pump_Solvent.initialize()
    await pump_Activator.initialize()
    await pump_SMIS.initialize()
    await pump_Quencher.initialize()

    # set the pump infusion rate
    await pump_EosinY.set_infusion_rate(Infusion_rate_dict["EY"])
    await pump_Activator.set_infusion_rate(Infusion_rate_dict["Activator"])
    await pump_Quencher.set_infusion_rate(Infusion_rate_dict["Quencher"])
    await pump_SMIS.set_infusion_rate(Infusion_rate_dict["SMIS"])
    await pump_Solvent.set_infusion(f"{Total_infusion_rate} ml/min")

    # start to fill the loop
    await pump_EosinY.infuse_run()
    await pump_Activator.infuse_run()
    print(f"the infuse duration of the EosinY and Activator will be {fill_tube_time_1} mins")
    await asyncio.sleep(fill_tube_time_1 * 60)  # buffer  duration ?  min
    await pump_Quencher.infuse_run()
    await pump_SMIS.infuse_run()
    print(f"the infuse duration of the injection loop will be {fill_tube_time_2} mins")
    await asyncio.sleep(fill_tube_time_2 * 60)  # buffer  duration ?  min

    # wash the filling tube

    await pump_EosinY.stop()
    await pump_Activator.stop()
    await pump_Solvent.run()
    await asyncio.sleep((0.0106/Total_infusion_rate) * 60)
    await pump_SMIS.stop()
    await pump_Quencher.stop()
    await asyncio.sleep((0.0212/Total_infusion_rate) *60)





async def main():
        Equiv_dict = {"EY":0.01, "H3BO3":0.02, "DIPEA":2}

        await injection_loop(Equiv_dict)




if __name__ == "__main__":
    asyncio.run(main())