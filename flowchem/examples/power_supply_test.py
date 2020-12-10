from flowchem.devices.mansonlib import InstrumentInterface
import time


def test():
	ps = InstrumentInterface()
	ps.open("COM30")

	input("SETTING PS TO 36V 2A, Enter to continue, auto-stop in 3 seconds...")
	ps.set_current(0.4)
	ps.set_voltage(31)
	ps.output_on()
	time.sleep(3)
	output = ps.get_output_read()
	ps.output_off()
	ps.close()
	print(f"V, I, MODE = {output}")


if __name__ == '__main__':	
	test()
