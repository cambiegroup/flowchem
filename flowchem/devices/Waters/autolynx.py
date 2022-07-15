"""
This is an ugly attempt to control a Waters Xevo MS via Autolynx.
When the MS is running and Autolynx is running, measuring an MS only requires putting a csv file with specific header
into a specific (and installation dependent) folder.
The Aim of this code is to supply a class that deals with creating the file with right experiment code and fields and
dropping it to the right folder.
"""
from pathlib import Path


class AutoLynxQueueFile:
    def __init__(self, path_to_AutoLynxQ = r"W:\BS-FlowChemistry\Equipment\Waters MS\AutoLynxQ",
                 ms_exp_file = "15min_scan.exp", tune_file = "SampleTuneAndDev_ManOBz.ipr",
                 inlet_method = "inlet_method"):
        self.fields = "FILE_NAME\tMS_FILE\tMS_TUNE_FILE\tINLET_FILE\tSAMPLE_LOCATION\tIndex"
        self.rows = f"\t{ms_exp_file}\t{tune_file}\t{inlet_method}\t66\t1"
        self.queue_path = Path(path_to_AutoLynxQ)

    def record_mass_spec(self, sample_name: str, file_name = "next.csv"):
        file_path = self.queue_path/Path(file_name)
        if file_path.is_file() and file_path.exists():
            append = True
        else:
            append = False
        with open(file_path,'a') as f:
            if append == False:
                f.write(self.fields)
            f.write("\n" + sample_name + self.rows)


if __name__ == "__main__":
    a = AutoLynxQueueFile()
    a.record_mass_spec('testestest')