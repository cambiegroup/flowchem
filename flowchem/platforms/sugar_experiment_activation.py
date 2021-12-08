import logging
from pathlib import Path

from flowchem.devices.Harvard_Apparatus.HA_elite11 import Elite11, PumpIO
from flowchem.devices.Knauer.HPLC_control import ClarityInterface
from flowchem.devices.Knauer.KnauerPumpValveAPI import KnauerPump
from flowchem.miscellaneous_helpers.folder_listener import FileReceiver, ResultListener
from flowchem.devices.ViciValco.ViciValco_Actuator import ViciValco
from flowchem.devices.Petite_Fleur_chiller import Huber
from flowchem.constants import flowchem_ureg
from flowchem.platforms.experiment_conditions import ExperimentConditions
from flowchem.platforms.platform_scheduler import Scheduler

#ToDo:
# optional 1b) Check the experiments in the folder in the beginning, if experiments already performed -> take from queue and don't execute
# 2b) do comparison if all other parameters are the same, if not, issue a warning and expand key description
# 3) get plotting and legend setup out of the box
# 4) determine peaks and do integration
# 5) report integration vs T
# 6) visualize integration




# TODO combining the sample name with the commit hash would make the experiment even more traceable. probably a
#  good idea...
# what I don't really get is why the class attributes are not printed to dict

if __name__ == "__main__":
    # FlowGraph as dicitonary
    logging.basicConfig()
    logging.getLogger("__main__").setLevel(logging.DEBUG)

    # missing init parameters
    elite_port = PumpIO("COM11")
    SugarPlatform = {
        # try to combine two pumps to one. flow rate with ratio gives individual flow rate
        'pumps': {
            'donor': Elite11(elite_port, address=1, diameter=4.606, volume_syringe=1),

            'activator': Elite11(elite_port, address=0, diameter=4.606, volume_syringe=1),

            'pure_DCM': Elite11(elite_port, address=2, diameter=4.608, volume_syringe=1),

            'quencher': KnauerPump("192.168.10.113"),
        },
        'HPLC': ClarityInterface(remote=True, host='192.168.10.11', port=10014, instrument_number=2),

        'sample_loop': ViciValco.from_config({"port": "COM13", "address": 0, "name": "test1"}),
        'chiller': Huber('COM1'),
        'internal_volumes': {'dead_volume_before_reactor': 8 * 2 * flowchem_ureg.microliter,
                             'volume_reactor': 58 * flowchem_ureg.microliter,
                             'dead_volume_to_HPLC': (46 + 28 + 20) * flowchem_ureg.microliter, # 20 µl for tubing from readtor to valve, 28 µl after microstructure (sounds a lot), 46µL for microrstructure
                             }
    }

    #
    fr = FileReceiver('192.168.10.20', 10339, allowed_address='192.168.10.11')
    analysed_samples_folder = Path(r'D:/transferred_chromatograms')
    scheduler = Scheduler(SugarPlatform, experiment_name='fullcharacterisationyuntao',
                          analysis_results=analysed_samples_folder)
    # This obviously could be included into the scheduler

    results_listener = ResultListener(analysed_samples_folder, '*Detector 1.txt', scheduler.analysed_samples)

#    scheduler.create_experiment(ExperimentConditions(temperature="10 °C", residence_time="300 s", building_block_smiles = "[STol][C@H]1[C@H](OC(C2=CC=CC=C2)=O)[C@@H](OCC3=CC=CC=C3)[C@H](OC(OCC4C(C=CC=C5)=C5C6=C4C=CC=C6)=O)[C@@H](COCC7=CC=CC=C7)O1"))

    scheduler.create_experiment(ExperimentConditions(temperature="0 °C", residence_time="300 s", activator=False, building_block_smiles = "[STol][C@H]1[C@H](OC(C2=CC=CC=C2)=O)[C@@H](OCC3=CC=CC=C3)[C@H](OC(OCC4C(C=CC=C5)=C5C6=C4C=CC=C6)=O)[C@@H](COCC7=CC=CC=C7)O1"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="0 °C", building_block_smiles = "[STol][C@H]1[C@H](OC(C2=CC=CC=C2)=O)[C@@H](OCC3=CC=CC=C3)[C@H](OC(OCC4C(C=CC=C5)=C5C6=C4C=CC=C6)=O)[C@@H](COCC7=CC=CC=C7)O1"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="-5 °C", building_block_smiles = "[STol][C@H]1[C@H](OC(C2=CC=CC=C2)=O)[C@@H](OCC3=CC=CC=C3)[C@H](OC(OCC4C(C=CC=C5)=C5C6=C4C=CC=C6)=O)[C@@H](COCC7=CC=CC=C7)O1"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="-10 °C", building_block_smiles = "[STol][C@H]1[C@H](OC(C2=CC=CC=C2)=O)[C@@H](OCC3=CC=CC=C3)[C@H](OC(OCC4C(C=CC=C5)=C5C6=C4C=CC=C6)=O)[C@@H](COCC7=CC=CC=C7)O1"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="-20 °C", building_block_smiles = "[STol][C@H]1[C@H](OC(C2=CC=CC=C2)=O)[C@@H](OCC3=CC=CC=C3)[C@H](OC(OCC4C(C=CC=C5)=C5C6=C4C=CC=C6)=O)[C@@H](COCC7=CC=CC=C7)O1"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="-40 °C", building_block_smiles = "[STol][C@H]1[C@H](OC(C2=CC=CC=C2)=O)[C@@H](OCC3=CC=CC=C3)[C@H](OC(OCC4C(C=CC=C5)=C5C6=C4C=CC=C6)=O)[C@@H](COCC7=CC=CC=C7)O1"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="-50 °C", building_block_smiles = "[STol][C@H]1[C@H](OC(C2=CC=CC=C2)=O)[C@@H](OCC3=CC=CC=C3)[C@H](OC(OCC4C(C=CC=C5)=C5C6=C4C=CC=C6)=O)[C@@H](COCC7=CC=CC=C7)O1"))
    scheduler.create_experiment(ExperimentConditions(residence_time="300 s", temperature="20 °C", building_block_smiles = "test"))



    # TODO when queue empty, after some while everything should be switched off
# TODO