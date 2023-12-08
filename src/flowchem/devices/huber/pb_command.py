from dataclasses import dataclass

from flowchem import ureg


@dataclass
class PBCommand:
    """Class representing a PBCommand."""

    command: str

    def to_chiller(self) -> bytes:
        """Validate and encode to bytes array to be transmitted."""
        self.validate()
        return self.command.encode("ascii")

    def validate(self):
        """Check command structure to be compliant with PB format."""
        if len(self.command) == 8:
            self.command += "\r\n"
        # 10 characters
        assert len(self.command) == 10
        # Starts with {
        assert self.command[0] == "{"
        # M for master (commands) S for slave (replies).
        assert self.command[1] in ("M", "S")
        # Address, i.e. the desired function. Hex encoded.
        assert 0 <= int(self.command[2:4], 16) < 256
        # Value
        assert self.command[4:8] == "****" or 0 <= int(self.command[4:8], 16) <= 65536
        # EOL
        assert self.command[8:10] == "\r\n"

    @property
    def data(self) -> str:
        """Data portion of PBCommand."""
        return self.command[4:8]

    def parse_temperature(self) -> float:
        """Parse a device temp from hex string to Celsius float."""
        # self.data is the two's complement 16-bit signed hex, see manual
        temp = (
            (int(self.data, 16) - 65536) / 100
            if int(self.data, 16) > 32767
            else (int(self.data, 16)) / 100
        )
        # Note: -151 used for invalid temperatures!
        return temp

    def parse_integer(self) -> int:
        """Parse a device reply from hexadecimal string to base 10 integers."""
        return int(self.data, 16)

    def parse_rpm(self) -> str:
        """Parse a device reply from hexadecimal string to rpm."""
        return str(ureg.Quantity(f"{self.parse_integer()} rpm"))

    def parse_bits(self) -> list[bool]:
        """Parse a device reply from hexadecimal string to 16 constituting bits."""
        bits = f"{int(self.data, 16):016b}"
        return [bool(int(x)) for x in bits]

    def parse_boolean(self):
        """Parse a device reply from hexadecimal string (0x0000 or 0x0001) to boolean."""
        return self.parse_integer() == 1

    def parse_status1(self) -> dict[str, bool]:
        """Parse response to status1 command and returns dict."""
        bits = self.parse_bits()
        return {
            "temp_ctl_is_process": bits[0],
            "circulation_active": bits[1],
            "refrigerator_on": bits[2],
            "temp_is_process": bits[3],
            "circulating_pump": bits[4],
            "cooling_power_available": bits[5],
            "tkeylock": bits[6],
            "is_pid_auto": bits[7],
            "error": bits[8],
            "warning": bits[9],
            "int_temp_mode": bits[10],
            "ext_temp_mode": bits[11],
            "dv_e_grade": bits[12],
            "power_failure": bits[13],
            "freeze_protection": bits[14],
        }

    def parse_status2(self) -> dict[str, bool]:
        """Parse response to status2 command and returns dict. See manufacturer docs for more info."""
        bits = self.parse_bits()
        return {
            "controller_is_external": bits[0],
            "drip_tray_full": bits[5],
            "venting_active": bits[7],
            "venting_successful": bits[8],
            "venting_monitored": bits[9],
        }
