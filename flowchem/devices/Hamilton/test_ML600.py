# purpose is to test ML600
from flowchem.devices.Hamilton.ML600 import ML600, HamiltonPumpIO, ML600Commands
left="left"
right="right"
from time import sleep


def test_single(hio):
	ml_single = ML600(hio, 1, address=2)
	assert input("Syringe connected?") == "YES"
	# ml_dual = ML600(HamiltonPumpIO("COM21"), {"left":1, "right": 0.25}, address=2)

	ml_single.initialize_pump(flowrate=1,syringe=left)
	assert input("pump initializes?") == "YES"
	ml_single.initialize_pump(flowrate=1)
	assert input("pump initializeS w flowrate 1 mL/min?") == "YES"


	ml_single.initialize_syringe(speed = 3)
	assert input("syringe initializes w speed 1 mL/min?") == "YES"
	ml_single.initialize_syringe(syringe = 'left', speed =3)
	assert input("syringe initializes?") == "YES"

	ml_single.initialize_valve()
	assert input("valve initializes?") == "YES"
	ml_single.initialize_valve(syringe = 'left')
	assert input("valve initializes?") == "YES"
	try:
		ml_single.initialize_valve(syringe = 'right')
		raise ValueError("THIS should not work")
	except Exception as e:
		assert isinstance(e, AssertionError)

	ml_single.steps_per_ml(syringe=left)
	assert input("steps per ml?") == "YES"
	try:
		ml_single.steps_per_ml(syringe=right)
		raise ValueError("THIS should not work")
	except Exception as e:
		assert isinstance(e, TypeError)

	ml_single.fill_single_syringe(0.5, 1, syringe=left)
	assert input("fill single syringe to 0.5 mL in 30 s?") == "YES"
	ml_single.deliver_from_single_syringe(0.25, 1, syringe=left)
	assert input("deliver from single syringe 0.25 mL in 15 s?") == "YES"

	ml_single.flowrate_to_seconds_per_stroke(0.1)
	assert input("flowrate to seconds per stroke works?") == "YES"
	ml_single._volume_to_step(0.1)
	assert input("volume to step works?") == "YES"
	ml_single._to_step_position(position=10, speed=10)
	assert input("to step position works?") == "YES"
	ml_single.initialize_valve(syringe = 'left')
	assert input("valve initializes?") == "YES"

	ml_single.to_volume(0.5, flow_rate=1)
	assert input("to volume works?") == "YES"
	ml_single.pause(syringe=left)
	assert input("pause works?") == "YES"
	try:
		ml_single.resume(syringe=right)
		raise ValueError("THIS should not work")
	except Exception as e:
		assert isinstance(e, AssertionError)
	ml_single.resume(syringe=left)
	assert input("resume works?") == "YES"
	try:
		ml_single.pause(syringe=right)
		raise ValueError("THIS should not work")
	except Exception as e:
		assert isinstance(e, AssertionError)

	try:
		ml_single.to_volume(0.5, flow_rate=1, syringe="right")
		raise ValueError("THIS should not work")
	except Exception as e:
		assert isinstance(e, TypeError)

	print(ml_single.send_command_and_read_reply(ML600Commands.BUSY_STATUS))

	print(ml_single.syringe_position(syringe='left'))

	ml_single.stop(syringe=left)
	ml_single.resume(syringe=left)
	assert input("SYRINGE does not resume?") == "YES"

	ml_single.send_multiple_commands(ml_single._absolute_syringe_move(0.2, 1, syringe = 'left'))
	assert input("absolute syringe move works?") == "YES"

	ml_single.fill_single_syringe(0.2, 1, valve_angle = 180, syringe = 'left')
	assert input("fill single syringe works?") == "YES"

	ml_single.deliver_from_single_syringe(0.2, 1, valve_angle=180, syringe='left')
	assert input("deliver from single syringe works?") == "YES"

	ml_single.home_single_syringe(1, syringe='left', valve_angle=180)
	assert input("home single syringe works?") == "YES"

	try:
		ml_single.fill_dual_syringes(0.5, 1)
		raise ValueError("THIS should not work")
	except Exception as e:
		assert isinstance(e, TypeError)

def test_dual(hio):
	ml_dual = ML600(hio, {"left":1, "right": 1}, address=1)
	assert input("Syringe connected?") == "YES"

	for i in ['left', 'right', None]:
		ml_dual.initialize_pump(flowrate=1, syringe=i)
		assert input(f"{'Both' if i is None else i} pump initializes?") == "YES"

	for i in ['left', 'right', None]:
		ml_dual.initialize_syringe(flowrate=1, syringe=i)
		assert input(f"{'Both' if i is None else i} syringe initializes?") == "YES"

	for i in ['left', 'right', None]:
		ml_dual.initialize_valve(syringe=i)
		assert input(f"{'Both' if i is None else i} valve initializes?") == "YES"

	for i in ['left', 'right', None]:
		ml_dual.fill_single_syringe(0.5, 1, syringe=i)
		assert input(f"{'Both' if i is None else i} single syringe to 0.5 mL in 30 s?") == "YES"
		ml_dual.deliver_from_single_syringe(0.25, 1, syringe=i)
		assert input(f"{'Both' if i is None else i} deliver from single syringe 0.25 mL in 15 s?") == "YES"
		ml_dual.home_single_syringe(1, syringe=i)
		assert input(f"{'Both' if i is None else i} home single syringe") == "YES"



	ml_dual.to_volume(0.5, flow_rate=1, syringe=left)
	ml_dual.to_volume(0.5, flow_rate=1, syringe=right)
	sleep(5)

	for i in ['left', 'right', None]:
		ml_dual.pause(syringe=i)
		assert input(f"{'Both' if i is None else i} pause works?") == "YES"
		ml_dual.resume(syringe=i)
		assert input(f"{'Both' if i is None else i} resume works?") == "YES"
		ml_dual.stop(syringe=i)
		assert input(f"{'Both' if i is None else i} stop works?") == "YES"

	# todo this only should work in all cases if the volume is the same
	# todo both does not work
	for i in ['left', 'right', None]:
		to_vol = 0.25 if i is not None else 0.5
		ml_dual.to_volume(to_vol, flow_rate=1, syringe=i)
		assert input(f"{'Both' if i is None else i} to volume {to_vol} works?") == "YES"
	# TODO test if they can be controlled independently

	# those should also be tested
	# also, find out how granular the is busy is accessible

	# assert input("SYRINGE does not resume?") == "YES"
	#
	# # TODO this does not work properly
	# ml_dual.send_multiple_commands(ml_dual._absolute_syringe_move(0.2, 1, syringe='left'))
	# assert input("absolute syringe move works?") == "YES"
	#
	# ml_dual.fill_single_syringe(0.2, 1, valve_angle=180, syringe='left')
	assert input("fill single syringe works?") == "YES"

	ml_dual.deliver_from_single_syringe(0.2, 1, valve_angle=180, syringe='left')
	assert input("deliver from single syringe works?") == "YES"

	ml_dual.home_single_syringe(1, syringe='left', valve_angle=180)
	assert input("home single syringe works?") == "YES"

	ml_dual.fill_dual_syringes(0.5, 1)
	assert input("fill dual syringes does not work?") == "YES"
	ml_dual.deliver_from_dual_syringes(0.5, 1)
	assert input("deliver from dual syringes does not work?") == "YES"

	# set size the same
	ml_dual.syringe_volume = {"left": 0.5, "right": 0.5}
	ml_dual.fill_dual_syringes(0.5, 1)
	assert input("fill dual syringes works?") == "YES"
	ml_dual.deliver_from_dual_syringes(0.5, 1)
	assert input("deliver from dual syringes works?") == "YES"



def test_valve():
	pass

if __name__ == "__main__":
	hio = HamiltonPumpIO("COM21")
	test_single(hio)
	test_dual(hio)
	#test_valve(hio)

# 'version': < property
# at
# 0x1ec21466220 >,
# 'is_idle': < property
# at
# 0x1ec214664a0 >,
# 'is_busy': < property
# at
# 0x1ec21466590 >,
# 'firmware_version': < property
# at
# 0x1ec21466630 >,
# 'valve_position': < property
# at
# 0x1ec21466720 >,
# 'return_steps': < property
# at
# 0x1ec21466770 >,

# ml_dual.fill_single_syringe()
# ml_dual.deliver_from_single_syringe()