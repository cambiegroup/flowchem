"""
This is an ugly attempt to control a Waters Xevo MS via Autolynx.
When the MS is running and Autolynx is running, measuring an MS only requires putting a csv file with specific header
into a specific (and installation dependent) folder.
The Aim of this code is to supply a class that deals with creating the file with right experiment code and fields and
dropping it to the right folder.
https://www.waters.com/webassets/cms/support/docs/71500123505ra.pdf
"""
from pathlib import Path
import subprocess

class AutoLynxQueueFile:
    def __init__(self, path_to_AutoLynxQ = r"W:\BS-FlowChemistry\Equipment\Waters MS\AutoLynxQ",
                 ms_exp_file = "15min_scan.exp", tune_file = "SampleTuneAndDev_ManOBz.ipr",
                 inlet_method = "inlet_method"):
        self.fields = "FILE_NAME\tMS_FILE\tMS_TUNE_FILE\tINLET_FILE\tSAMPLE_LOCATION\tIndex"
        self.rows = f"\t{ms_exp_file}\t{tune_file}\t{inlet_method}\t66\t1"
        self.queue_path = Path(path_to_AutoLynxQ)

    def record_mass_spec(self, sample_name: str, file_name = "next.txt"):
        # Autolynx behaves weirdly, it expects a .txt file and that the fields are separated by tabs. A csv file
        # separated w commas however does not work... Autolynx has to be set to look for csv files
        file_path = self.queue_path/Path(file_name)
        if file_path.is_file() and file_path.exists():
            append = True
        else:
            append = False
        with open(file_path,'a') as f:
            if append == False:
                f.write(self.fields)
            f.write(f"\n{sample_name}{self.rows}")

# convert to mzml C:\Users\BS-flowlab\AppData\Local\Apps\ProteoWizard 3.0.22198.0867718 64-bit>
class Converter:


    def __init__(self, path_to_executable = r"C:\Users\BS-flowlab\AppData\Local\Apps\ProteoWizard 3.0.22198.0867718 64-bit", output_dir = r""):
        self.exe = path_to_executable
        self.output_dir = output_dir


# open subprocess in this location
    def convert_masspec(self, filename):
        # create string
        exe_str = f"msconvert {filename}.RAW -o {self.output_dir}"
        print(exe_str)
        subprocess.Popen(exe_str, cwd=self.exe, shell=True)
        #x.run(exe_str, shell=True, capture_output=False, timeout=3)


if __name__ == "__main__":
    a = AutoLynxQueueFile()
    a.record_mass_spec('testestest')