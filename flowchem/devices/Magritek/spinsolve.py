"""
Module to control Magritek SpinSolve benchtop NMR.
"""
from pathlib import Path

# Store shim coils parameters in custom location
SHIMMING_LOCATION = Path.home() / "flowchem" / "spinsolve_shimming.json"
SHIMMING_LOCATION.parent.mkdir(exist_ok=True)
SHIMMING_LOCATION.touch(exist_ok=True)


class SpinsolveNMR:
    def __init__(self, address: str = None, port: int = 13000):
        """
        Args:
            address: IP address of the local host
            port: port number
        """

        # Queue for storing path of the measured spectrum
        self.data_folder_queue = queue.Queue()

        # Flag for check the instrument status
        self._device_ready_flag = threading.Event()

        # Instantiating submodules
        self._parser = ReplyParser(self._device_ready_flag, self.data_folder_queue)
        self._connection = SpinsolveConnection(HOST=address, PORT=port)
        self.cmd = ProtocolCommands(spinsolve_options_path)
        self.req_cmd = RequestCommands()
        self.spectrum = SpinsolveNMRSpectrum()

        # placeholder to store shimming parameters
        self.last_shimming_results = {}

        # placeholders for experiment data
        self._user_data = {}
        self._solvent = None
        self._sample = None

    def check_last_shimming(self):
        """ Checks last shimming.

        Returns:
            bool: False if shimming procedure is required, True otherwise.
        """
        if not self.last_shimming_results:
            try:
                with open(SHIMMING_PATH) as fobj:
                    self.last_shimming_results = json.load(fobj)
            except FileNotFoundError:
                self.logger.warning('Last shimming was not recorded, please run\
 any shimming protocol to update!')
                return False
        now = time.time()
        # if the last shimming was performed more than 24 hours ago
        if now - self.last_shimming_results['timestamp'] > 24*3600:
            self.logger.critical('Last shimming was performed more than 24 \
hours ago, please perform CheckShim to check spectrometer performance!')
            return False
        return True

    def connect(self):
        """Connects to the instrument"""

        self.logger.debug("Connection requested")
        self._connection.open_connection()

    def disconnect(self):
        """Closes the socket connection"""

        self.logger.info("Request to close the connection received")
        self._connection.close_connection()
        self.logger.info("The instrument is disconnected")

    def send_message(self, msg):
        """Sends the message to the instrument"""

        if self._parser.connected_tag != "true":
            raise HardwareError("The instrument is not connected, check the Spinsolve software")
        self.logger.debug("Waiting for the device to be ready")
        self._device_ready_flag.wait()
        self.logger.debug("Sending the message \n%s", msg)
        self._connection.transmit(msg)
        self.logger.debug("Message sent")

    def receive_reply(self, parse=True):
        """Receives the reply from the instrument and parses it if necessary"""

        while True:
            self.logger.debug("Reply requested from the connection")
            reply = self._connection.receive()
            self.logger.debug("Reply received")
            if parse:
                reply = self._parser.parse(reply)
            if self._device_ready_flag.is_set():
                return reply

    def initialise(self):
        """Initialises the instrument by sending HardwareRequest"""

        cmd = self.req_cmd.request_hardware()
        self._connection.transmit(cmd)
        return self.receive_reply()

    def is_instrument_ready(self):
        """Checks if the instrument is ready for the next command"""

        if self._parser.connected_tag == "true" and self._device_ready_flag.is_set():
            return True
        else:
            return False

    def load_commands(self):
        """Requests the available commands from the instrument"""

        cmd = self.req_cmd.request_available_protocol_options()
        self.send_message(cmd)
        reply = self.receive_reply()
        self.cmd.reload_commands(reply)
        self.logger.info("Commands updated, see available protocols \n <%s>", list(self.cmd._protocols.keys())) # pylint: disable=protected-access

    @shimming
    def shim(
            self,
            option="CheckShimRequest",
            *,
            line_width_threshold=1,
            base_width_threshold=40,
        ):
        """Initialise shimming protocol

        Consider checking <Spinsolve>.cmd.get_protocol(<Spinsolve>.cmd.SHIM_PROTOCOL) for available options

        Args:
            option (str, optional): A name of the instrument shimming method
        """

        # updating default values
        self._parser.shimming_line_width_threshold = line_width_threshold
        self._parser.shimming_base_width_threshold = base_width_threshold

        cmd = self.req_cmd.request_shim(option)
        self.send_message(cmd)
        return self.receive_reply()

    @shimming
    def shim_on_sample(self, reference_peak, option="LockAndCalibrateOnly", *, line_width_threshold=1, base_width_threshold=40):
        """Initialise shimming on sample protocol

        Consider checking <Spinsolve>.cmd.get_protocol(<Spinsolve>.cmd.SHIM_ON_SAMPLE_PROTOCOL) for available options

        Args:
            reference_peak (float): A reference peak to shim and calibrate on
            option (str, optional): A name of the instrument shimming method
            line_width_threshold (float, optional): Spectrum line width at 50%, should be below 1
                for good quality spectrums
            base_width_threshold (float, optional): Spectrum line width at 0.55%, should be below 40
                for good quality spectrums
        """

        self._parser.shimming_line_width_threshold = line_width_threshold
        self._parser.shimming_base_width_threshold = base_width_threshold
        cmd = self.cmd.shim_on_sample(reference_peak, option)
        self.send_message(cmd)
        return self.receive_reply()

    def set_user_folder(self, data_path, data_folder_method="TimeStamp"):
        """Indicate the path and the method for saving NMR data

        Args:
            data_folder_path (str): Valid path to save the spectral data
            data_folder_method (str, optional): One of three methods according to the manual:
                'UserFolder' - Data is saved directly in the provided path
                'TimeStamp' (default) - Data is saved in newly created folder in format
                    yyyymmddhhmmss in the provided path
                'TimeStampTree' - Data is saved in the newly created folders in format
                    yyyy/mm/dd/hh/mm/ss in the provided path

        Returns:
            bool: True if successfull
        """

        cmd = self.req_cmd.set_data_folder(data_path, data_folder_method)
        self.send_message(cmd)
        return True

    @property
    def user_data(self):
        """ Dictionary with user specific data. """
        if not self._user_data:
            user_data_req = self.req_cmd.get_user_data()
            self.send_message(user_data_req)
            self._user_data = self.receive_reply()

        return self._user_data

    @user_data.setter
    def user_data(self, user_data):
        """ Sets the user data.

        Args:
            user_data (Dict): Dictionary with user data.
        """
        # updating placeholder
        self._user_data.update(user_data)
        # sending command
        user_data_cmd = self.req_cmd.set_user_data(user_data)
        self.send_message(user_data_cmd)

    @user_data.deleter
    def user_data(self):
        """ Removes previously stored user data. """

        # generating command to reset the data in spinsolve
        empty_user_data_command = self.req_cmd.set_user_data(
            {key: '' for key in self._user_data}
        )
        self.send_message(empty_user_data_command)

        # updating placeholder
        self._user_data = {}

    @property
    def solvent(self):
        """ Solvent record to be stored with spectrum acquisition params. """
        if self._solvent is None:
            solvent_req = self.req_cmd.get_solvent()
            self.send_message(solvent_req)
            self._solvent = self.receive_reply()
        return self._solvent

    @solvent.setter
    def solvent(self, solvent):
        """ Sets the solvent record for the current experiment. """
        self._solvent = solvent
        solvent_data_cmd = self.req_cmd.set_solvent_data(solvent)
        self.send_message(solvent_data_cmd)

    @solvent.deleter
    def solvent(self):
        """ Removes the solvent record for the current experiment. """
        self._solvent = None
        empty_solvent_data_cmd = self.req_cmd.set_solvent_data('')
        self.send_message(empty_solvent_data_cmd)

    @property
    def sample(self):
        """ Sample record to be stored with spectrum acquisition params. """
        if self._sample is None:
            sample_req = self.req_cmd.get_sample()
            self.send_message(sample_req)
            self._sample = self.receive_reply()
        return self._sample

    @sample.setter
    def sample(self, sample):
        """ Sets the sample record for the current experiment.

        Also sets the folder to save the spectrum, so avoid special characters.
        """
        self._sample = sample
        sample_data_cmd = self.req_cmd.set_sample_data(sample)
        self.send_message(sample_data_cmd)

    @sample.deleter
    def sample(self):
        """ Removes the sample record for the current experiment. """
        self._sample = None
        empty_sample_data_cmd = self.req_cmd.set_sample_data('')
        self.send_message(empty_sample_data_cmd)

    def get_duration(self, protocol, options):
        """Requests for an approximate duration of a specific protocol

        Args:
            protocol (str): A name of the specific protocol
            options (dict): Options for the selected protocol
        """

        cmd = self.cmd.generate_command((protocol, options), self.cmd.ESTIMATE_DURATION_REQUEST)
        self.send_message(cmd)
        return self.receive_reply()

    def proton(self, option="QuickScan"):
        """Initialise simple 1D Proton experiment"""

        cmd = self.cmd.generate_command((self.cmd.PROTON, {"Scan": f"{option}"}))
        self.send_message(cmd)
        return self.receive_reply()

    def proton_extended(self, options):
        """Initialise extended 1D Proton experiment"""

        cmd = self.cmd.generate_command((self.cmd.PROTON_EXTENDED, options))
        self.send_message(cmd)
        return self.receive_reply()

    def carbon(self, options=None):
        """Initialise simple 1D Carbon experiment"""

        if options is None:
            options = {"Number": "128", "RepetitionTime": "2"}
        cmd = self.cmd.generate_command((self.cmd.CARBON, options))
        self.send_message(cmd)
        return self.receive_reply()

    def carbon_extended(self, options):
        """Initialise extended 1D Carbon experiment"""

        cmd = self.cmd.generate_command((self.cmd.CARBON_EXTENDED, options))
        self.send_message(cmd)
        return self.receive_reply()

    def fluorine(self, option="QuickScan"):
        """Initialise simple 1D Fluorine experiment"""

        cmd = self.cmd.generate_command((self.cmd.FLUORINE, option))
        self.send_message(cmd)
        return self.receive_reply()

    def fluorine_extended(self, options):
        """Initialise extended 1D Fluorine experiment"""

        cmd = self.cmd.generate_command((self.cmd.FLUORINE_EXTENDED, options))
        self.send_message(cmd)
        return self.receive_reply()

    def wait_until_ready(self):
        """Blocks until the instrument is ready"""

        self._device_ready_flag.wait()

    def calibrate(self, reference_peak, option="LockAndCalibrateOnly"):
        """Performs shimming on sample protocol"""

        self.logger.warning("DEPRECATION WARNING: use shim_on_sample() method instead")
        return self.shim_on_sample(reference_peak, option)

    @property
    def protocols_list(self):
        """Returns a list of all available protocols"""

        return list(self.cmd)

    def get_spectrum(self, protocol=None):
        """Wrapper method to load the spectral data to inner Spectrum class.

        Loads the last measured data. If no data previously measured, will
            perform self.DEFAULT_EXPERIMENT and load its data.
        """

        if self.data_folder_queue.empty():
            self.logger.warning('No previous data.')
            if protocol is None:
                protocol = self.DEFAULT_EXPERIMENT
                self.logger.warning('Running default <%s> protocol.',
                                    self.DEFAULT_EXPERIMENT[0])
            cmd = self.cmd.generate_command(protocol)
            self.send_message(cmd)
            self.receive_reply()

        # will block if spectrum is measuring
        data_folder = self.data_folder_queue.get()

        self.spectrum.load_spectrum(data_folder)

        warning_message = 'Method "get_spectrum" will no longer return the \
spectropic data. Please use .spectrum class to access the spectral data and \
to the documentation for its usage.'

        warnings.warn(warning_message, DeprecationWarning)

        # for backwards compatibility
        data1d = os.path.join(data_folder, 'data.1d')
        _, fid_real, fid_img = self.spectrum.extract_data(data1d)

        fid_complex = [
            complex(real, img)
            for real, img
            in zip(fid_real, fid_img)
        ]

        return fid_complex
