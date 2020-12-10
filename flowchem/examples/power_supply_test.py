from flowchem.devices.mansonlib import InstrumentInterface
import time


def test():
	ps = InstrumentInterface()
	ps.open("com3")

	input("SETTING PS TO 2V 0.1A, Enter to continue, auto-stop in 3 seconds...")
	ps.set_current(0.1)
	ps.set_voltage(2)
	ps.output_on()
	time.sleep(3)
	output = ps.get_output_read()
	ps.output_off()

	print(f"V, I, MODE = {output}")

	input("SETTING PS TO 10V 0.2A, Enter to continue, auto-stop in 3 seconds...")
	ps.set_current(0.2)
	ps.set_voltage(10)
	ps.output_on()
	time.sleep(3)
	output = ps.get_output_read()
	ps.output_off()
	ps.close()
	print(f"V, I, MODE = {output}")


if __name__ == '__main__':	
	test()
