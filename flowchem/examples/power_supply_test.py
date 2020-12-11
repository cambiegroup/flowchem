from flowchem.devices.mansonlib import InstrumentInterface
import time


def test():
	ps = InstrumentInterface()
	ps.open("COM30")

	output = {}
	ps.set_current(2)
	ps.output_on()
	for voltage in range(220, 361):
		ps.set_voltage(voltage/10)
		time.sleep(0.1)
		power = ps.get_output_power()
		output[voltage/10] = power
		print(f"output power at {voltage} is {power}")

	import json
	out_file = open("420led.json", "w")
	json.dump(output, out_file)

	ps.output_off()


if __name__ == '__main__':	
	test()
