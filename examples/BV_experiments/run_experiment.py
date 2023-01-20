import time
import asyncio

from collections import namedtuple
# import numpy as np
# import pandas as pd
from _hw_control import *
from loguru import logger
from dotenv import load_dotenv

from examples.BV_experiments._hw_control import command_session
# from scipy import integrate

from flowchem.devices.harvardapparatus.elite11 import Elite11
from flowchem.devices.vapourtec import R2
from flowchem.devices.knauer import KnauerValve
from flowchem.devices.bronkhorst import MFC

LOOP_VOLUME = 0.1  # ml
FILLING_TIME = 2.5  # min
total_infusion_rate = LOOP_VOLUME / FILLING_TIME  # 0.02  ml/min
TUBE_MIXER_TO_LOOP = 0.0212  # ml = 0.30 (m)*70.69 (ul/m)
TUBE_LOOP_TO_REACTOR = 0.014 # in ml = 0.20 (m)*70.69 (ul/m)
REACTOR_VOLUME = 3.075  # ml

BPR = 0.0  # ml
TUBE_BPR_TO_SEPARATOR = 0.069  # in ml = 0.97 (m)*70.69 (ul/m)
SEPARATOR = 0.5  # ml
TUBE_SEPARATOR_TO_SENSOR = 0.181  # in ml = (0.28-0.05) (m)*785.4 (ul/m)
TUBE_SENSOR_TO_VALVEC = 0.039  # in ml = 0.05 (m)*785.4 (ul/m)
TUBE_VALVEC_TO_PUMPB = 0.047  # in ml = 0.06 (m)*785.4 (ul/m)
TUBE_PUMPB_TO_COLLECTOR = 0.393  # in ml = 0.50 (m)*785.4 (ul/m)


def calc_inj_rate(condition: dict) -> dict[str:float]:
    # TODO: find way to save all
    SOLN = {"EY": 0.05, "H3BO3": 1.00}  # in M (mol/L)
    SUB = {"SM": {"MW": 146.19, "density": 1.230},
           "Tol": {"MW": 92.14, "density": 0.866},
           "DIEPA": {"MW": 129.25, "density": 0.742}}  # {MW in g/mol, density in g/mL}
    SOL = {"MeOH": {"MW": 32.04, "density": 0.792}, "MeCN": {"MW": 41.05, "density": 0.786}}

    VOL = {
        "SMIS": 0.001 * (SUB["SM"]["MW"] / SUB["SM"]["density"] + SUB["Tol"]["MW"] / SUB["Tol"]["density"]),
        "EY": condition["eosinY_equiv"] / SOLN["EY"],
        "Activator": condition["activator_equiv"] / SOLN["H3BO3"],
        "Quencher": condition["quencher_equiv"] * SUB["DIEPA"]["MW"] * 0.001 / SUB["DIEPA"]["density"]
    }
    # VOL_ratio = {key: value / VOL["SMIS"] for key, value in VOL.items()}

    # Calculate the required volume to fill the loop [0.1 mL]
    # the required volume of SM for the loop = LOOP_VOLUME * conc_in_M * SUB["SM"]["MW"] * 0.001/ SUB["SM"]["density"]

    mmol_of_SM = LOOP_VOLUME * condition["SM_concentration"]  # concentration in M (mmol/mL)
    # the volume of each substrate/syringe needed for the loop
    ml_of_all = {key: value * mmol_of_SM for key, value in VOL.items()}
    # the volume of make up solvent to reach the concentration.....
    total_vol = sum(ml_of_all.values())
    ml_of_all["Solvent"] = LOOP_VOLUME - total_vol  # condition["eosinY_equiv"] is useless??

    # return Infuse flow rate in ml/min
    rate_of_all = {key: value / FILLING_TIME for key, value in ml_of_all.items()}

    # return Infuse flow rate in ml/min
    # flow_unit = total_infusion_rate / sum(ml_of_all.values())
    # rate_dict= {key: value * flow_unit for key, value in ml_of_all.items()}
    return rate_of_all


def calc_gas_liquid_flow_rate(condition: dict) -> dict:
    """
    Calculation all flow used in the reaction....
    Returns:
        dict:{
        total flow,
        liquid flow,
        gas flow,
        makeup flow
        }
    """

    Oxygen_volume_per_mol = 22.4
    total_flow_rate = REACTOR_VOLUME / condition["time"]  # ml/min

    # parameters
    conc = condition["SM_concentration"]  # in M
    vol_ratio_GtoL = Oxygen_volume_per_mol * conc * condition["oxygen_equiv"]
    compressed_G_vol = vol_ratio_GtoL / condition["pressure"]

    # setting flow rate of liquid and gas (in ml/min)
    set_liquid_flow = total_flow_rate / (1 + compressed_G_vol)
    set_gas_flow = set_liquid_flow * vol_ratio_GtoL

    # makeup_solvent flow rate (in ml/min)
    ANAL_CONC = 0.0025  # HPLC sample in M
    first_dilution = LOOP_VOLUME / SEPARATOR  # 0.1/0.5 = 0.2 (5 times) by methanol
    makeup_flow = conc * first_dilution * set_liquid_flow / ANAL_CONC - set_liquid_flow
    return {"total_flow": total_flow_rate, "liquid_flow": set_liquid_flow,
            "gas_flow": set_gas_flow, "makeup_flow": makeup_flow
            }


def calc_time(condition: dict, flow_rate: dict) -> namedtuple:
    """
        calculate the time period
        [0]: period of filling;
        [1]: push to loop;
        [2]: wash loop;
        [3]: waiting: residence time - wash loop;
        [4]: unlimited time for check reaction mixture came out
        [5]: change the valve after check the mixture came out (short!)
        [6]: the time bwt valveC and collector
        [7]: buffer time before sampling
        [8]: HPLC sampling time (important!!)
        [9]: buffer time after sampling
        """

    periods = namedtuple("time_period",
                         ["filling",
                          "pushing_loop",
                          "loop_to_sensor",
                          "detect_RM",
                          "switch_valveC",
                          "BF_collect",
                          "collecting",
                          "AF_collect"
                          ])

    rate_after_BPR = flow_rate["liquid_flow"] + flow_rate["gas_flow"]  # TODO: some gas will be consumed
    rate_after_makeup = flow_rate["liquid_flow"] + flow_rate["makeup_flow"]
    # rate_for_liquid = flow_rate["liquid_flow"] + flow_rate["makeup_flow"]

    # trial and error for the purging time required..........
    before_sensor_time = (TUBE_LOOP_TO_REACTOR / flow_rate["liquid_flow"] + condition["time"] + TUBE_BPR_TO_SEPARATOR / rate_after_BPR + (SEPARATOR + TUBE_SEPARATOR_TO_SENSOR) / flow_rate["liquid_flow"])

    time_period = [FILLING_TIME * 1.1,
                   TUBE_MIXER_TO_LOOP / total_infusion_rate * 0.9,
                   before_sensor_time * 1.0,
                   0,
                   TUBE_SENSOR_TO_VALVEC / flow_rate["liquid_flow"]
                   ]

    # collecting HPLC sample : collect 1.00 ml of HPLC sample... in the middle of the reaction

    # Owing to dilute by the solvent (methanol) in line,
    # the liquid flow rate did not change but the volume of reaction mixture will be the inner volume of separator
    total_sampling_time = SEPARATOR / flow_rate["liquid_flow"]
    vol_sampling = total_sampling_time * rate_after_makeup
    logger.info(f"total volume of HPLC sample will be {vol_sampling}")

    # collecting time modify by the total_vol and collected vial
    ANAL_VOL = 1.00  # mL
    collecting_time = ANAL_VOL / rate_after_makeup

    # time required to reach the collector from valve C
    to_collector = TUBE_VALVEC_TO_PUMPB / flow_rate["liquid_flow"] + TUBE_PUMPB_TO_COLLECTOR / rate_after_makeup

    if total_sampling_time > collecting_time:
        buffer_time = total_sampling_time / 2 - collecting_time / 2
        sampling_period = [to_collector + buffer_time, collecting_time, buffer_time]
    else:
        sampling_period = [to_collector, total_sampling_time, 0]

    time_period.extend(sampling_period)
    t_periods = periods._make(time_period)
    return t_periods


# def wait_stable_gas_liquid_mix():
#     """Wait until the flow is stable.
#
#     """
#     logger.info("Waiting for the flow to stabilize")
#     while True:
#         with command_session() as sess:
#             r = sess.get(bubble_sensor_measure_endpoint + "/read_intensity")
#             if r.text == "true":
#                 logger.info("Stable temperature reached!")
#                 break
#             else:
#                 time.sleep(5)


def wait_color_change():
    """
    Wait until the flow is stable.

    the intensity of gas should btw 0-0.3 voltage
    methanol: 0.3 mm ID, 1/16" OD, 2.62-2.64 voltage (light); 2.6-2.75 voltage (without light) --> 1/20 2.97     (with foil)
    reaction mixture: depandent on the concentration ( 5 mM : 2.94  --> 2.93 )

    """
    logger.info("Waiting for the reaction mixture came out.")

    # consecutive 8 measurements show the similar results
    for measure in range(8):

        while True:
            with command_session() as sess:
                r = sess.get(bubble_sensor_measure_endpoint + "/bubble-sensor/read-intensity")
                if 20 <= float(r.text) <= 55:
                    logger.info("color change!")
                    break

        measure += 1


async def initialize_hardware():
    # initialize the hardware after any experiment

    with command_session() as sess:
        pass


async def run_experiment(condition: dict, inj_rate: dict, flow_rate: dict):
    time_period = calc_time(condition, flow_rate)
    logger.info(f"Starting experiment with the experiment code {condition['name']}")
    logger.info(f"time periods:{time_period}; "
                f"required experiment time : {sum(time_period)-time_period.purging_mixer} mins roughly")

    with command_session() as sess:
        # Set up the gas and pumpA
        sess.put(r2_endpoint + "/Pump_A/infuse", params={"rate": f"{flow_rate['liquid_flow']} ml/min"})
        sess.put(MFC_endpoint + "/el_flow_MFC/setpoint", params={"flowrate": f"{flow_rate['gas_flow']} ml/min"})

        # Turn on the temperature and UV
        sess.put(r2_endpoint + "/PhotoReactor/temperature", params={"temperature": f"{condition['temperature']}°C"})
        sess.put(r2_endpoint + "/PhotoReactor/UV", params={"power": f"{condition['UV']}"})
        # Start to fill the loop: FILLING_TIME
        # TODO: Cannot convert from 'dimensionless' (dimensionless) to 'nanoliter / minute' ([length] ** 3 / [time])
        sess.put(solvent_endpoint + "/pump/infuse", params={"rate": f"{inj_rate['Solvent']} ml/min"})
        sess.put(eosinY_endpoint + "/pump/infuse", params={"rate": f"{inj_rate['EY']} ml/min"})
        sess.put(activator_endpoint + "/pump/infuse", params={"rate": f"{inj_rate['Activator']} ml/min"})
        sess.put(quencher_endpoint + "/pump/infuse", params={"rate": f"{inj_rate['Quencher']} ml/min"})
        sess.put(SMIS_endpoint + "/pump/infuse", params={"rate": f"{inj_rate['SMIS']} ml/min"}, )
        time.sleep(time_period.filling * 60)  # period of filling

        # push som mixture in the tube into the loop
        sess.put(SMIS_endpoint + "/pump/stop")
        sess.put(solvent_endpoint + "/pump/infuse", params={"rate": f"{inj_rate['SMIS']} ml/min"})
        time.sleep(time_period.pushing_loop * 60)

        # switch the InjValveA to inject the reaction mixture into the system
        switching_time = time.monotonic()
        sess.put(r2_endpoint + "/InjectionValve_A/position", params={"position": "inject"})
        logger.info("switch the injectionValve A to inject! keep purge the tube....")
        logger.info(f"purging {time_period.purging_mixer} mins wotj ")

        # purge the tube for mixing
        # sess.put(solvent_endpoint + "/pump/infuse", params={"rate": f"{total_infusion_rate} ml/min"})
        purge_volume_ml = LOOP_VOLUME * 6
        sess.put(solvent_endpoint + "/pump/infuse", params={
            "rate": f"{total_infusion_rate*2} ml/min",
            "volume": f"{purge_volume_ml} ml"
        })
        sess.put(eosinY_endpoint + "/pump/stop")
        sess.put(activator_endpoint + "/pump/stop")
        sess.put(quencher_endpoint + "/pump/stop")
        logger.info(f"purging finishes! continue reaction......")

    # Wait 1 residence time
    # time.sleep(condition["time"] * 60)
    # waiting time calculation by tube....
    # end_time = switching_time + (time_period.loop_to_sensor) * 60
    end_time = switching_time  # Use the line above for real experiment :)
    while time.monotonic() < end_time:
        # print(f"Sleeping and waiting for the reaction to be ready... We need another {end_time-time.monotonic():.0f} s")
        time.sleep(0.1)

    # check the color change from the bubble sensor after residence time
    # wait_color_change()
    # run on make up pump
    # wait 10 cm delay to valve
    # wait valve to INJECTION VALVE
    # inject

    with command_session() as sess:
        # start pumping makeup solvent
        sess.put(r2_endpoint + "/Pump_B/infuse",
                 params={"rate": f"{flow_rate['makeup_flow']} ml/min"})

        # switch the valveC and pump in make-up  solvent (ACN) by pumpB
        time.sleep(time_period.switch_valveC * 60)
        sess.put(r2_endpoint + "/CollectionValve/position", params={"position": "Reagent"})

        # turn off reactor
        sess.put(r2_endpoint + "/PhotoReactor/UV-power-off")
        sess.put(r2_endpoint + "/PhotoReactor/temperature", params={"temperature": "20°C"})

        # the injection loop for HPLC and Clarity HPLC system should be use.... but the pump is not ready yet....
        # wait the diluted reaction mixture to reach the collector valve and wait for collect the HPLC sample
        time.sleep(time_period.BF_collect * 60)

        # collect the HPLC sample
        sess.put(collector_endpoint + "/distribution-valve/position", params={"position": f"4"})
        time.sleep(time_period.collecting * 60)

        # after collecting sample, switch the valve to waste + purge the tube
        sess.put(collector_endpoint + "/distribution-valve/position", params={"position": f"2"})
        time.sleep(time_period.AF_collect * 60)

        # initialized all hardware

        # stop pump (set to 0 ul/min)
        sess.put(r2_endpoint + "/Pump_A/stop")
        sess.put(r2_endpoint + "/Pump_B/stop")

        # stop MFC
        # TODO:Cannot convert from 'dimensionless' (dimensionless) to 'microliter / minute' ([length] ** 3 / [time])
        sess.put(MFC_endpoint + "/el_flow_MFC/setpoint", params={"flowrate": f"0 ml/min"})

        # switch injection valve to loading
        sess.put(r2_endpoint + "/InjectionValve_A/position", params={"position": "load"})

        # switch valveC to solvent
        sess.put(r2_endpoint + "/CollectionValve/position", params={"position": "Solvent"})
        sess.put(r2_endpoint + "/Power/power-off")

    logger.info(f"the reaction was finished!")


async def main():
    whh_136 = dict(name=f"WHH-136",
                   SM_concentration=0.5,
                   time=6.0,
                   eosinY_equiv=0.01,
                   activator_equiv=0.02,
                   quencher_equiv=2.0,
                   oxygen_equiv=2.0,
                   solvent_equiv=10.0,
                   pressure=5.0,
                   temperature=24,
                   UV=0,
                   category=None,
                   id="mongodb_id"
                   )

    # calculate the setting parameters
    set_syringe_rate = calc_inj_rate(whh_136)
    logger.info(f"syringe:{set_syringe_rate}")
    logger.info(f"total volume {sum(set_syringe_rate.values()) * FILLING_TIME}")
    set_gas_liquid_flow = calc_gas_liquid_flow_rate(whh_136)
    logger.info(f"pump:{set_gas_liquid_flow}")

    # time_period = calc_time(whh_136, set_gas_liquid_flow)
    # logger.info(f"time period:{time_period}; total required time : {sum(time_period)} mins roughly")

    logger.info(f"test")
    await run_experiment(whh_136, set_syringe_rate, set_gas_liquid_flow)


if __name__ == "__main__":
    asyncio.run(main())
