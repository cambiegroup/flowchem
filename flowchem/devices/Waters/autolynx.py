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
import pymzml
from pandas import DataFrame

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


class IonChromatogram:
    # peak detection would be kind of nice
    # adding spectra off a certain range would be nice
    # extracting the TIC for one mass (or, even better, not only take monoisotopic mass)
    # integrate over a timerange, so add upp all spectra in specific time
    # idea is autoprocessing based on ELSD
    def __init__(self, filepath:Path):
        # read the mzml
        self.spectra_over_time = pymzml.run.Reader(filepath, skip_chromatogram = True)

        # actually, use a dataframe?
        self.time_TIC = self._extract_time_index_tic()

    def _create_offset(self, offset_min: float) -> None:
        # simply add offset_min on the time axis
        self.time_TIC["time_offset"] = self.time_TIC["time"] + offset_min

    def get_tic_for_mass(self) -> None:
        # spectrum.has_peak(m/z) -> [(m/z:intensity)]
        # should append the mz-intensity to dataframe
        pass

    def average_over_spectra(self):
        # should take spectra slice on a time basis, merge all of these on m/z axis and divide resulting intensity by amount of spectra in slice
        # alternative would be to only take the spectra subset of detected peaks
        pass

    def reduce_spectral_width(self):
        pass

    def _extract_time_index_tic(self) -> DataFrame:
        time = []
        _x_index = []
        tic = []
        for i in self.spectra_over_time:
            time.append(i.scan_time_in_minutes())
            tic.append(i.TIC)
        time_TIC = DataFrame(data={"time":time, "TIC":tic})
        return time_TIC

    def smooth_ion_chrom(self, window_size:int = 19, degree:int = 3) -> None:
        from scipy.signal import savgol_filter
        self.time_TIC["Smoothed_TIC"] = savgol_filter(self.time_TIC.TIC, window_size, degree)



if __name__ == "__main__":
    a = AutoLynxQueueFile()
    a.record_mass_spec('testestest')