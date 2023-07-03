from zeroconf import ServiceBrowser, Zeroconf, ServiceListener
import socket


class MyListener(ServiceListener):
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name}%s removed")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name}%s updated")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zeroconf.get_service_info(type_, name)
        if info:
            # Convert IPv4 from bytes to string
            device_ip = socket.inet_ntoa(info.addresses[0])
            print(f"Service {name} added, IP address: {device_ip}")
            print(f"Device properties are: {info.properties}")


zeroconf = Zeroconf()
listener = MyListener()
browser = ServiceBrowser(zeroconf, "_labthing._tcp.local.", listener)
try:
    input("Press enter to exit...\n\n")
finally:
    zeroconf.close()
