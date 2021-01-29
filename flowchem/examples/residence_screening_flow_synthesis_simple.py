import time
import logging
from flowchem.devices.Knauer.KnauerPumpValveAPI import KnauerValve, KnauerPump
from flowchem.devices.Knauer.knauer_autodiscover import autodiscover_knauer
from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
from flowchem.devices.mansonlib import PowerSupply
import json
from flowchem.devices.iCIR import FlowIR

# usable, but maybe some output table or format would be nice: especially parameters like t or wavelength


# residence time determines flow rate with known volume
def get_flow_rate_for_residence_time(residence_time_in_min, volume_reactor_in_ml) -> float:
    rate_in_ml_min = volume_reactor_in_ml / residence_time_in_min
    return rate_in_ml_min


# this starts  the pump. loads the sample loop. pushes half the reactor volume through,
# then switches to next collection vial, waits half reactor + full reactor volume.
def perform_experiment(residence_time, reactor_volume, sample_loop_volume, dead_volume, file_name=None):
    flow_rate = get_flow_rate_for_residence_time(residence_time, reactor_volume)

    current_valve_position = necessary_devices_macs['fraction_collection'].get_current_position()

    logging.info(f'Flow rate is {flow_rate} for residence time {residence_time}. This will go into collection vessel on position {int(current_valve_position)+1}')

    str_to_write = f'Collection vessel on valve position {int(current_valve_position)+1}: Flow rate was {flow_rate} ml/min for residence time {residence_time} min.\n\r'
    # dump dict with collection vessel as primary key. links to dict of flow, residence time and spectra 1 to --
    necessary_devices_macs['solvent_delivery'].set_flow(round(flow_rate * 1000))  # transform to µl/min
    necessary_devices_macs['solvent_delivery'].start_flow()

    # load starting mixture to loop
    necessary_devices_macs['injection_loop'].switch_to_position('L')
    necessary_devices_macs['injection_pump'].run()  # TODO check infuse_run()

    time.sleep(30)

    while True:
        if not necessary_devices_macs['injection_pump'].is_moving():
            break

    necessary_devices_macs['injection_loop'].switch_to_position('I')
    # start timer

    start_time = time.time()
    purge_time = start_time + ((reactor_volume/2 + dead_volume) / flow_rate) * 60

    collection_time = purge_time + ((reactor_volume/2+sample_loop_volume/2) / flow_rate) * 60
    #big saftey margin for flushing
    collect_time_end = collection_time + ((sample_loop_volume*1.5) / flow_rate) * 60

    logging.info("this run will be over in "+ str((collect_time_end-start_time)/60) +"min.")

    # wait until half the reactor is full with reagent
    counter = 0
    while time.time() < purge_time:
        time.sleep(1)
        counter += 1
        if counter == 60:
            remaining_time = purge_time-time.time()
            logging.info(f"Still {remaining_time/60:.2f} min to wait until collection starts")
            counter = 0

    necessary_devices_macs['fraction_collection'].switch_to_position(int(current_valve_position) + 1)

    # now collect up till half of sample loop
    while time.time() < collection_time:
        time.sleep(1)
        counter += 1
        if counter == 60:
            logging.info("Still "+str((collect_time_end-time.time())/60)+ "min to wait until collection peaks")
            counter = 0

    spectrum = ir_spectrometer.get_last_spectrum_treated()

    result = {str_to_write: spectrum}
    with open(file_name, 'a') as f:
        json.dump(result, f, indent= "")

    while time.time() < collect_time_end:
        time.sleep(1)
        counter += 1
        if counter == 60:
            logging.info("Still "+str((collect_time_end-time.time())/60)+ "min to wait until collection finishes")
            counter = 0

    # the tail is caught anyway by switching after half the reactor volume
    logging.info('Collection of product is finished')

if __name__ == "__main__":
    # take arguments and calculate everything needed. In the end this will solely be times and flow rates.
    # iterate through experiments
    available_macs_ips = autodiscover_knauer(source_ip='192.168.1.1')

    try:
        necessary_devices_macs = {'solvent_delivery': KnauerPump(available_macs_ips['00:80:a3:ba:bf:e2']),
                                  'injection_loop': KnauerValve(available_macs_ips['00:80:a3:ce:7e:15']),
                                  'injection_pump': Elite11(PumpIO('COM5'), diameter=14.57, volume_syringe=10),
                                  'fraction_collection': KnauerValve(available_macs_ips['00:80:a3:ce:8e:43'])}
    except KeyError as e:
        raise ConnectionError(f'Device with MAC {e} is not available') from e

    # will trhow error if not operational
    ir_spectrometer = FlowIR()
    ir_spectrometer.is_instrument_connected()
    ir_spectrometer.get_last_spectrum_treated()



    # use power supply and switch LEDs on

    ps = PowerSupply()
    ps.open("COM6")

    ps.set_voltage_and_current(voltage_in_volt=36, current_in_ampere=2)
    ps.output_on()


    # ultimately, this could be determined with dye or fluorescence, biphasic mixture(diffusion) known flowrate would yield volume
    # reactortocollection needs to be cleaned actually. This needs to be done after everything is out, but before new stuff arrives
    reactor_volume = 4.7
    # ToDo check:
    injection_loop_volume = 1
    dead_volume = 0.45
    # to the IR it is again 0.2 mL

    # If you want to use units all over the place pint is a nice package for that, see e.g. HA Elite 11 unit conversions
    # That would allow the next line to be residence_time = ["1 sec", "15 sec", "0.5 min"]
    # Using values with units all over the place is slightly more complex, but has the advantage of allowing
    # more descriptive and "human" input (via pint parser), transparent unit transformation and ideally could
    # prevent dimensionality errors. I'm not 100% sold to that as the unit registry syntax is not always clean
    residence_times = [1/60, 0.25, 0.5]
    # set syringe pump
    necessary_devices_macs['injection_pump'].target_volume(injection_loop_volume * 1.1)
    necessary_devices_macs['injection_pump'].infusion_rate(2)
    necessary_devices_macs['injection_pump'].force(percent_force=50)

    for i in residence_times[::-1]:
        perform_experiment(i, reactor_volume, injection_loop_volume, dead_volume, file_name='jbw13_onlymaleimid.txt')

    logging.info('run finished. Now purging some solvent to get last tail out')
    necessary_devices_macs['solvent_delivery'].set_flow(1000)
    necessary_devices_macs['solvent_delivery'].start_flow()
    time.sleep(600)
    necessary_devices_macs['solvent_delivery'].stop_flow()

    ps.output_off()
# Future: ALL parameters should be reported. 