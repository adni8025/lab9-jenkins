import re
import unittest

from netmiko import ConnectHandler

DEVICES = {
    "R1": "198.51.100.11",
    "R2": "198.51.100.12",
    "R3": "198.51.100.13",
    "R4": "198.51.100.14",
    "R5": "198.51.100.15",
}
USERNAME = "lab"
PASSWORD = "lab123"

def run_command(host, command, read_timeout=20):
    connection = ConnectHandler(
        device_type="cisco_ios",
        host=host,
        username=USERNAME,
        password=PASSWORD,
        fast_cli=False,
    )
    output = connection.send_command(command, read_timeout=read_timeout)
    connection.disconnect()
    return output

class TestLab9(unittest.TestCase):
    def test_r3_loopback99(self):
        output = run_command(DEVICES["R3"], "show running-config interface Loopback99")
        self.assertIn("ip address 10.1.3.1 255.255.255.0", output)

    def test_r1_single_area(self):
        output = run_command(DEVICES["R1"], "show running-config | section ^router ospf")
        areas = set(re.findall(r"area\s+(\d+)", output))
        self.assertEqual(areas, {"0"})
        self.assertEqual(len(areas), 1)

    def test_r2_to_r5_ping(self):
        output = run_command(
            DEVICES["R2"],
            "ping 10.1.5.1 source 10.1.2.1 repeat 5",
            read_timeout=30,
        )
        self.assertRegex(output, r"Success +rate +is +100 +percent")

if __name__ == "__main__":
    unittest.main(verbosity=2)
