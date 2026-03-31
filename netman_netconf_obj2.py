from pathlib import Path
import ipaddress
import re
import sys

import pandas as pd
from ncclient import manager
from netaddr import IPAddress
from prettytable import PrettyTable

INFO_FILE = Path("info.csv")
REQUIRED_COLUMNS = [
    "Router",
    "Mgmt IP",
    "Username",
    "Password",
    "Hostname",
    "Loopback Name",
    "Loopback IP",
    "Loopback Subnet",
    "Wildcard",
    "Network",
    "OSPF Area",
]
CONFIG_TEMPLATE = '''
<config>
    <cli-config-data>
        <cmd>hostname {hostname}</cmd>
        <cmd>interface {loopback_name}</cmd>
        <cmd>ip address {loopback_ip} {loopback_subnet}</cmd>
        <cmd>router ospf 1</cmd>
        <cmd>network {network} {wildcard} area {area}</cmd>
        <cmd>network 198.51.100.0 0.0.0.255 area 0</cmd>
    </cli-config-data>
</config>
'''
FILTER_TEMPLATE = '''
<filter>
    <config-format-text-block>
        <text-filter-spec>{text_filter}</text-filter-spec>
    </config-format-text-block>
</filter>
'''

def fail(message):
    print(message)
    sys.exit(1)

def load_inventory():
    if not INFO_FILE.exists():
        fail(f"File {INFO_FILE} not found, exiting")
    if INFO_FILE.stat().st_size == 0:
        fail(f"File {INFO_FILE} is empty, exiting")
    frame = pd.read_csv(INFO_FILE)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        fail(f"Missing columns in {INFO_FILE}: {', '.join(missing)}")
    return frame.to_dict("records")

def open_session(host, username, password):
    return manager.connect(
        host=host,
        port=22,
        username=username,
        password=password,
        hostkey_verify=False,
        device_params={"name": "iosxe"},
        allow_agent=False,
        look_for_keys=False,
        timeout=60,
    )

def configure_router(router):
    payload = CONFIG_TEMPLATE.format(
        hostname=router["Hostname"],
        loopback_name=router["Loopback Name"],
        loopback_ip=router["Loopback IP"],
        loopback_subnet=router["Loopback Subnet"],
        network=router["Network"],
        wildcard=router["Wildcard"],
        area=router["OSPF Area"],
    )
    print(f"Logging into router {router['Router']} and sending configurations")
    with open_session(router["Mgmt IP"], router["Username"], router["Password"]) as session:
        session.edit_config(target="running", config=payload)

def get_running_section(session, text_filter):
    payload = FILTER_TEMPLATE.format(text_filter=text_filter)
    response = session.get_config("running", payload)
    return str(response)

def parse_hostname(output):
    match = re.search(r"hostname\s+(\S+)", output)
    if not match:
        fail("Unable to parse hostname from device output")
    return match.group(1)

def parse_loopback(output):
    match = re.search(r"ip address\s+(\S+)\s+(\S+)", output)
    if not match:
        fail("Unable to parse Loopback99 IP information from device output")
    prefix = IPAddress(match.group(2)).netmask_bits()
    return f"{match.group(1)}/{prefix}"

def parse_ospf(output):
    matches = re.findall(r"network\s+(\S+)\s+(\S+)\s+area\s+(\S+)", output)
    if len(matches) < 2:
        fail("Unable to parse OSPF information from device output")
    area = matches[0][2]
    networks = []
    for network, wildcard, _ in matches[:2]:
        prefix = ipaddress.ip_network(f"{network}/{wildcard}", strict=False).prefixlen
        networks.append(f"{network}/{prefix}")
    return area, tuple(networks)

def collect_state(router, table):
    with open_session(router["Mgmt IP"], router["Username"], router["Password"]) as session:
        print(f"Pulling information from router {router['Router']} to display")
        hostname_output = get_running_section(session, "| include hostname")
        loopback_output = get_running_section(session, "interface Loopback99")
        ospf_output = get_running_section(session, "| section router ospf")
    hostname = parse_hostname(hostname_output)
    loopback_ip = parse_loopback(loopback_output)
    ospf_area, ospf_networks = parse_ospf(ospf_output)
    table.add_row(
        (
            router["Router"],
            hostname,
            loopback_ip,
            ospf_area,
            ospf_networks,
        )
    )

def main():
    routers = load_inventory()
    table = PrettyTable(
        ["Router", "Hostname", "Loopback 99 IP", "OSPF area", "Advertised OSPF Networks"]
    )
    for router in routers:
        configure_router(router)
    print("\n------------------Configs to all routers is sent------------------\n")
    for router in routers:
        collect_state(router, table)
    print("\n------------------Displaying the fetched information------------------\n")
    print(table)

if __name__ == "__main__":
    main()
