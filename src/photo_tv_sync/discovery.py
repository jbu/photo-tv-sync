import socket

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_TIMEOUT = 3  # seconds to wait for responses per search target

# Try multiple service types — Samsung TVs advertise different ones depending on model/firmware
SEARCH_TARGETS = [
    "urn:samsung.com:device:RemoteControlReceiver:1",
    "urn:dial-multiscreen-org:service:dial:1",
    "urn:schemas-upnp-org:device:MediaRenderer:1",
    "upnp:rootdevice",
]

SAMSUNG_HINTS = ("samsung", "tizen", "smarttv", "smart-tv", "remotecontrolreceiver")


def _msearch(target: str) -> str:
    return (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 2\r\n"
        f"ST: {target}\r\n"
        "\r\n"
    )


def _local_ip() -> str:
    """Return the IP of the interface that routes to the LAN."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def discover_tv() -> str | None:
    """Return the IP address of the first Samsung TV found via SSDP, or None."""
    local_ip = _local_ip()

    for target in SEARCH_TARGETS:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(SSDP_TIMEOUT)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_IF,
            socket.inet_aton(local_ip),
        )
        try:
            sock.sendto(_msearch(target).encode(), (SSDP_ADDR, SSDP_PORT))
            while True:
                try:
                    data, addr = sock.recvfrom(4096)
                    response = data.decode(errors="ignore").lower()
                    if any(hint in response for hint in SAMSUNG_HINTS):
                        return addr[0]
                except TimeoutError:
                    break
        except OSError:
            break
        finally:
            sock.close()

    return None
