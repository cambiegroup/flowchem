import time
import logging
from flowchem.devices.Knauer.KnauerPumpValveAPI import KnauerValve, KnauerPump
from flowchem.devices.Knauer.knauer_autodiscover import autodiscover_knauer
from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
from flowchem.devices.mansonlib import PowerSupply
import csv

# usable, but maybe some output table or format wouzld be nicee


#residence time determines flow rate with know volume
def get_flow_rate_for_residence_time(residence_time, volume_reactor):
    #input a mL and min
    rate= volume_reactor/residence_time
    return rate



# this starts  the pump. loads the sample loop. pushes half the reactor volume through, then switches to next collection vial, waits half reactor + full reactor volume.
def perform_experiment(residence_time, reactor_volume, sample_loop_volume, file_name=None):
    flow_rate = get_flow_rate_for_residence_time(residence_time, reactor_volume)

    current_valve_position = neccessary_devices_macs['fraction_collection'].get_current_position()

    logging.info('Flow rate is {} for residence time {}. This will go into collection vessel on position {}'.format(flow_rate, residence_time, int(current_valve_position)+1))

    if file_name:
        with open(file_name, 'a') as f:
            f.write('Collection vessel on valve position {2}: Flow rate was {0} ml/min for residence time {1} min.\n\r'.format(flow_rate, residence_time, int(current_valve_position)+1))

    neccessary_devices_macs['solvent_delivery'].set_flow(flow_rate*1000) # transorm to µl/min
    neccessary_devices_macs['solvent_delivery'].start_flow()

    # load starting mixture to loop
    neccessary_devices_macs['injection_loop'].switch_to_position('L')
    neccessary_devices_macs['injection_pump'].run() #TODO check infuse_run()

    time.sleep(60)

    while True:
        if not neccessary_devices_macs['injection_pump'].is_moving():
            break

    neccessary_devices_macs['injection_loop'].switch_to_position('I')
    #start timer

    start_time = time.time()
    purge_time = start_time + ((reactor_volume/2) / flow_rate) * 60
    collect_time_end = purge_time + ((reactor_volume/2+sample_loop_volume) / flow_rate) * 60
    logging.info("this run will be over in "+ str((collect_time_end-start_time)/60) +"min.")

    # wait until half the reactor is full with reagent
    counter = 0
    while time.time() < purge_time:
        time.sleep(1)
        counter+=1
        if counter ==  60:
            logging.info("Still "+str((purge_time-time.time())/60)+ "min to wait until collection starts")
            counter = 0

    neccessary_devices_macs['fraction_collection'].switch_to_position(int(current_valve_position)+1)

    # now collect rest plus sample loop
    while time.time() < collect_time_end:
        time.sleep(1)
        counter += 1
        if counter == 60:
            logging.info("Still "+str((collect_time_end-time.time())/60)+ "min to wait until collection finishes")
            counter = 0

    # the tail is caught anyway by switching after half the reactor volume
    logging.info('Collection of product is finished')

    #create several smaller wait times, to ensure purity



if __name__ == "__main__":
    # take arguments and calculate everything needed. In the end this will solely be times and flow rates.
    # iterate through experiments
    # get available macs and check against required_macs list.  This isn't elegant for sure
    available_macs_ips = autodiscover_knauer()
    print(available_macs_ips)

    neccessary_devices_list = ['00:80:a3:ce:7e:15','00:80:a3:ba:bf:e2','00:80:a3:ce:8e:43']

    for i in neccessary_devices_list:
        if i not in available_macs_ips:
            raise ConnectionError('At least one device with MAC {} is not available'.format(i))

    # use power supply and switch leds on
    ps = PowerSupply()
    ps.open("COM30")

    ps.set_current(2)
    ps.output_on()

    ps.set_voltage(36)

    neccessary_devices_macs = {'solvent_delivery': KnauerPump(available_macs_ips['00:80:a3:ba:bf:e2']),
                               'injection_loop': KnauerValve(available_macs_ips['00:80:a3:ce:7e:15']),
                               'injection_pump': Elite11(PumpIO('COM7'), diameter=30, volume_syringe=10),
                               'fraction_collection': KnauerValve(available_macs_ips['00:80:a3:ce:8e:43'])}

    # ultimately, this could be determined with dye or fluorescence, biphasic mixture(diffusion) known flowrate would yield volume
    # reactortocollection needs to be cleaned actually. This needs to be done after everything is out, but before new stuff arrives
    reactor_volume = 4.7
    # ToDo check:
    injection_loop_volume = 1


    residence_time_list = [0.5, 1, 2, 3]#[15, 20, 25, 30, 35, 40, 45, 50]  # in min
    # set syringe pump
    neccessary_devices_macs['injection_pump'].target_volume(injection_loop_volume*1.1)
    neccessary_devices_macs['injection_pump'].infusion_rate(5)

    for i in residence_time_list:
        perform_experiment(i, reactor_volume, injection_loop_volume, file_name='/flowchem/examples/catalyst_screening_residence_time')

    logging.info('run finished. Now purging some solvent to get last tail out')
    neccessary_devices_macs['solvent_delivery'].set_flow(1000)
    neccessary_devices_macs['solvent_delivery'].start_flow()
    time.sleep(600)
    neccessary_devices_macs['solvent_delivery'].stop_flow()


# Future: ALL parameters should be reported. 