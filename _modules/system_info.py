from __future__ import absolute_import
import wmi


class SystemDetail:
    def __init__(self):
        self.c = wmi.WMI()
        self.make_model = self.c.Win32_ComputerSystemProduct()
        self.memory = self.c.Win32_PhysicalMemory()
        self.os = self.c.Win32_OperatingSystem()
        self.base_board = self.c.Win32_BaseBoard()
        self.bios = self.c.Win32_BIOS()
        self.disk = self.c.Win32_DiskDrive()
        self.network_adapter = self.c.Win32_NetworkAdapter()
        self.network_config = self.c.Win32_NetworkAdapterConfiguration()
        self.desktop_monitor = self.c.Win32_DesktopMonitor()
        self.cpu = self.c.Win32_Processor()
        self.usb = self.c.Win32_USBController()

    def get_all(self, obj):
        ret = []
        for i in obj:
            tmp = [
                {j: getattr(i, j)}
                for j in list(i.properties)
                if getattr(i, j) is not None
            ]
            ret.append(tmp)

        return ret


def system_info():
    info = SystemDetail()
    return {
        "make_model": info.get_all(info.make_model),
        "mem": info.get_all(info.memory),
        "os": info.get_all(info.os),
        "base_board": info.get_all(info.base_board),
        "bios": info.get_all(info.bios),
        "disk": info.get_all(info.disk),
        "network_adapter": info.get_all(info.network_adapter),
        "network_config": info.get_all(info.network_config),
        "desktop_monitor": info.get_all(info.desktop_monitor),
        "cpu": info.get_all(info.cpu),
        "usb": info.get_all(info.usb),
    }
