from flowchem.constants.constants import flowchem_ureg
from flowchem.platforms.sugar_experiment import FlowConditions, ExperimentConditions



SugarPlatform = {     # try to combine two pumps to one. flow rate with ratio gives individual flow rate
     'pumps': {
         'donor': 'a',
         'donor_solvent': 'b',
         'acceptor': 'c',
         'acceptor_solvent': 'd',
         'activator': 'e',
         'activator_solvent': 'f',
         'quench': 'f',
     },
     'HPLC': 'f',
     # 'chiller': Huber('COM7'),
     # assume always the same volume from pump to inlet, before T-mixer can be neglected
     'internal_volumes': {'dead_volume_before_reactor': 84.5 * flowchem_ureg.microliter,
                          'volume_mixing': 9.5 * flowchem_ureg.microliter,
                          'volume_reactor': 68.8 * flowchem_ureg.microliter,
                          'dead_volume_to_HPLC': 11 * flowchem_ureg.microliter,
                          }
 }

e = ExperimentConditions()
f= FlowConditions(e, SugarPlatform)

# Todo add meaningful tests, ideally testing validity of calculated values
print(f'Flow rates should be equal:{(f.activator_solvent_flow_rate + f.activator_flow_rate)} '
      f'{f.donor_solvent_flow_rate + f.donor_flow_rate} {f.acceptor_solvent_flow_rate + f.acceptor_flow_rate} '
      f'{f._individual_inlet_flow_rate}')

print(f'Also the equivalents should fit, calculate backwards')
