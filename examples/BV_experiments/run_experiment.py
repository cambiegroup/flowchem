import time
import asyncio

# import numpy as np
# import pandas as pd
from _hw_control import *
from loguru import logger
# from scipy import integrate

from flowchem.devices.harvardapparatus.elite11 import Elite11
from flowchem.devices.vapourtec import R2
from flowchem.devices.knauer import KnauerValve
from flowchem.devices.bronkhorst import MFC

LOOP_VOLUME = 0.1  # ml
FILLING_TIME = 2.5  # min
total_infusion_rate = LOOP_VOLUME / FILLING_TIME  # 0.02  ml/min
TUBE_BF_LOOP = 0.0212  # ml = 0.30 (m)*70.69 (ul/m)
REACTOR_VOLUME = 2.5  # ml
BPR = 0.0  # ml
TUBE_BPR_TO_VALVEC = 0.069  # in ml = 0.97 (m)*70.69 (ul/m)
TUBE_SENSOR_TO_VALVEC = 0.007  # in ml = 0.10 (m)*70.69 (ul/m)
TUBE_VALVEC_TO_PUMPB = 0.196  # in ml = 0.25 (m)*785.4 (ul/m)
TUBE_PUMPB_TO_SEPARATOR = 0.220  # in ml = 0.28 (m)*785.4 (ul/m)
SEPAEATOR = 0.5  # ml
TUBE_SEPAEATOR_TO_COLLECTOR = 0.393  # in ml = 0.50 (m)*785.4 (ul/m)


def calc_inj_rate(exp_condition: dict) -> dict[str:float]:
    # TODO: find way to save all
    SOLN = {"EY": 0.05, "H3BO3": 1.00}  # in M (mol/L)
    SUB = {"SM": {"MW": 146.19, "density": 1.230},
           "Tol": {"MW": 92.14, "density": 0.866},
           "DIEPA": {"MW": 129.25, "density": 0.742}}  # {MW in g/mol, density in g/mL}
    SOL = {"MeOH": {"MW": 32.04, "density": 0.792}, "MeCN": {"MW": 41.05, "density": 0.786}}

    VOL = {
        "SMIS": 0.001 * (SUB["SM"]["MW"] / SUB["SM"]["density"] + SUB["Tol"]["MW"] / SUB["Tol"]["density"]),
        "EY": exp_condition["eosinY_equiv"] / SOLN["EY"],
        "Activator": exp_condition["activator_equiv"] / SOLN["H3BO3"],
        "Quencher": exp_condition["quencher_equiv"] * SUB["DIEPA"]["MW"] * 0.001 / SUB["DIEPA"]["density"]
    }
    # VOL_ratio = {key: value / VOL["SMIS"] for key, value in VOL.items()}

    # Calculate the required volume to fill the loop [0.1 mL]
    # the required volume of SM for the loop = LOOP_VOLUME * conc_in_M * SUB["SM"]["MW"] * 0.001/ SUB["SM"]["density"]

    mmol_of_SM = LOOP_VOLUME * exp_condition["SM_concentration"]  # concentration in M (mmol/mL)
    # the volume of each substrate/syringe needed for the loop
    ml_of_all = {key: value * mmol_of_SM for key, value in VOL.items()}
    # the volume of make-up solvent to reach the concentration.....
    total_vol = sum(ml_of_all.values())
    ml_of_all["Solvent"] = LOOP_VOLUME - total_vol  # exp_condition["eosinY_equiv"] is useless??

    # return Infuse flow rate in ml/min
    rate_of_all = {key: value / FILLING_TIME for key, value in ml_of_all.items()}

    # return Infuse flow rate in ml/min
    # flow_unit = total_infusion_rate / sum(ml_of_all.values())
    # rate_dict= {key: value * flow_unit for key, value in ml_of_all.items()}
    return rate_of_all


def calc_gas_liquid_flow_rate(exp_condition: dict) -> dict[str:float]:
    """

    Returns:
        object:
    """
    Oxygen_volume_per_mol = 22.4
    total_flow_rate = REACTOR_VOLUME / exp_condition["time"]  # ml/min

    # parameters
    conc = exp_condition["SM_concentration"]  # in M
    vol_ratio_GtoL = Oxygen_volume_per_mol * conc * exp_condition["oxygen_equiv"]
    compressed_G_vol = vol_ratio_GtoL / exp_condition["pressure"]

    # setting flow rate of liquid and gas (in ml/min)
    set_liquid_flow = total_flow_rate / (1 + compressed_G_vol)
    set_gas_flow = set_liquid_flow * vol_ratio_GtoL

    # makeup_solvent flow rate (in ml/min)
    ANAL_CONC = 0.0025  # HPLC sample in M
    makeup_flow = conc * set_liquid_flow / ANAL_CONC - set_liquid_flow
    return {"liquid-flow": set_liquid_flow, "gas-flow": set_gas_flow, "makeup_flow": makeup_flow}


async def loop_purging():
    with command_session() as sess:
        sess.put(solvent_endpoint + "/infuse", params={"rate": f"{total_infusion_rate} ml/min"})
        sess.put(eosinY_endpoint + "/infuse", params={"rate": "0 ml/min"})
        sess.put(activator_endpoint + "/infuse", params={"rate": "0 ml/min"})
        sess.put(quencher_endpoint + "/infuse", params={"rate": "0 ml/min"})
    await asyncio.sleep(FILLING_TIME * 60)
    with command_session() as sess:
        sess.put(solvent_endpoint + "/infuse", params={"rate": "0 ml/min"})


# def set_parameters_for_rxn_mixture(rates: dict):
#     with command_session() as sess:
#
#         # sess.put(
#         #     hexyldecanoic_endpoint + "/flow-rate",
#         #     params={"rate": f"{rates['hexyldecanoic']} ml/min"},
#         # )
#
#         # Sets heater
#         heater_data = {"temperature": f"{temperature:.2f} °C"}
#         sess.put(r4_endpoint + "/temperature", params=heater_data)
#
# def set_parameters_for_reaction():
#     pass

def wait_stable_gas_liquid_mix():
    """Wait until the flow is stable.

    the intensity of gas should btw 0-0.5 voltage
    methanol:
    reaction mixture:
    """
    logger.info("Waiting for the flow to stabilize")
    while True:
        with command_session() as sess:
            r = sess.get(bubble_sensor_measure_endpoint + "/read_intensity")
            if r.text == "true":
                logger.info("Stable temperature reached!")
                break
            else:
                time.sleep(5)


def wait_color_change():
    """Wait until the flow is stable."""
    logger.info("Waiting for the reaction mixture came out.")

    # consecutive 8 measurements show the similar results
    for measure in range(8):

        while True:
            with command_session() as sess:
                r = sess.get(bubble_sensor_measure_endpoint + "/read_intensity")

                if 20 <= float(r.text) <= 55:
                    logger.info("color change!")
                    break
                else:
                    time.sleep(5)
        measure += 1


def hplc_data_processing():
    """Processing Clarity hplc data"""


def integrate_peaks():
    """Integrate areas from `limits.in` in the spectrum provided."""


async def run_experiment(condition: dict, inj_rate: dict, flow_rate: dict):
    # inj_rate:inj_rate = {"SMIS": ,"EY": ,"Activator": ,"Quencher": , "Solvent": }
    # flow_rate: {"liquid-flow":set_liquid_flow, "gas-flow": set_gas_flow, "makeup_flow":makeup_flow}

    logger.info(
        f"Starting experiment with the experiment code {condition[id]}"
    )

    with command_session() as sess:
        # Set up the gas and pumpA
        sess.put(r2_endpoint + "/Pump_A/infuse", params={"rate": f"{flow_rate['liquid-flow']} ml/min"})
        sess.put(MFC_endpoint + "/el_flow_MFC/setpoint", params={"flowrate": f"{flow_rate['gas-flow']} ml/min"})

        # Turn on the temperature and UV
        sess.put(r2_endpoint + "/PhotoReactor/temperature", params={"temperature": f"{condition['temperature']} °C"})
        sess.put(r2_endpoint + "/PhotoReactor/UV", params={"temperature": f"{condition['UV']} °C"})

        # Start to fill the loop: FILLING_TIME(2.5 min)
        sess.put(solvent_endpoint + "/infuse", params={"rate": f"{inj_rate['Solvent']} ml/min"})
        sess.put(eosinY_endpoint + "/infuse", params={"rate": f"{inj_rate['EY']} ml/min"})
        sess.put(activator_endpoint + "/infuse", params={"rate": f"{inj_rate['Activator']} ml/min"})
        sess.put(quencher_endpoint + "/infuse", params={"rate": f"{inj_rate['Quencher']} ml/min"})
        sess.put(SMIS_endpoint + "/infuse", params={"rate": f"{inj_rate['SMIS']} ml/min"}, )

        time.sleep(FILLING_TIME * 1.1 * 60)  # period of filling

        # push the mixture in the tube into the loop
        sess.put(SMIS_endpoint + "/infuse", params={"rate": f"0 ml/min"}, )
        sess.put(solvent_endpoint + "/infuse", params={"rate": f"{inj_rate['SMIS']} ml/min"})

        time.sleep(TUBE_BF_LOOP / total_infusion_rate * 0.9 * 60)

        # check the stability of the mixing of gas and liquid???

        # switch the valveA to inject the reaction mixture
        sess.put(r2_endpoint + "InjectionValve_A/", params={"position": "inject"})

    # purge the tube
    await loop_purging()

    # Wait 1 residence time
    time.sleep(condition[time] * 60)

    # check the color change from the bubble sensor after residence time
    wait_color_change()
    # switch the valveC and pump in make-up  solvent (ACN) by pumpB

    with command_session() as sess:
        sess.put(r2_endpoint + "Pump_B/infuse", params={"rate": f"{flow_rate['makeup_flow']} ml/min"})
        sess.put(r2_endpoint + "CollectionValve/position", params={"position": "Reagent"})

        # the injection loop for HPLC and Clarity HPLC system should be use.... but the pump is not ready yet....

        # collect the reaction mixture

        return peaks["product"]


async def main():
    whh_136 = dict(name=f"WHH-136",
                   SM_concentration=1.22,
                   time=25.0,
                   eosinY_equiv=0.01,
                   activator_equiv=0.02,
                   quencher_equiv=2.0,
                   oxygen_equiv=2.0,
                   solvent_equiv=10.0,
                   pressure=4.0,
                   temperature=30.0,
                   UV=100,
                   category=None,
                   id="mongodb_id"
                   )
    # calculate the setting parameters
    # set_syringe_rate  = calc_inj_rate(whh_136)
    # print(f"syringe:{set_syringe_rate}")
    # print(f"total volume{sum(set_syringe_rate.values()) * FILLING_TIME})
    # set_gas_liquid_flow = calc_gas_liquid_flow_rate(whh_136)
    # print(f"pump:{set_gas_liquid_flow}")

    logger.info(f"test")
    wait_color_change()
    # await run_experiment(whh_136,set_syringe_rate,set_gas_liquid_flow)


async def purge():
    logger.info("starting purging")
    await asyncio.sleep(5.0)
    logger.debug("finishing purging")


async def test():
    logger.info(f"test")
    await purge()
    logger.info("start reaction")
    await asyncio.sleep(30.0)
    logger.debug("finishing reaction")


if __name__ == "__main__":
    asyncio.run(main())
