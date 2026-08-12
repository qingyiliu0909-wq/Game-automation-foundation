from scapy.layers.l2 import Ether
from scapy.layers.inet import IP
from scapy.layers.inet6 import IPv6


def find_ip(packet, info):
    # packet 是 scapy 已解析好的包
    if not packet.haslayer(Ether):
        return
    eth = packet[Ether]

    # 注意比较MAC格式：scapy的 eth.src 是 xx:xx:xx:xx:xx:xx 格式
    # info.mac 可能格式不一样，统一一下比较
    def normalize_mac(mac):
        return mac.lower().replace("-", ":")
    # print(eth.src)
    # print(info.mac)
    if normalize_mac(eth.src) == normalize_mac(info.mac):
        # IPv4
        if packet.haslayer(IP):
            info.ipv4 = packet[IP].src
        # IPv6
        if packet.haslayer(IPv6):
            info.ipv6 = packet[IPv6].src
