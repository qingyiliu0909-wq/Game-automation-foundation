import psutil
import pythoncom
import wmi
import socket
import os
import uuid

class WinUtils:
    """
    WinUtils用于获取设备硬件参数信息,如CPU型号,GPU型号等.
    """
    def __init__(self):
        pass

    @staticmethod
    def get_Unique_id():
        return str(uuid.getnode())

    def get_cpu_type(self):
        pythoncom.CoInitialize()
        _wmi = wmi.WMI()
        return _wmi.Win32_Processor()[0].name

    def get_gpu_type(self):
        gpu_type_list = []
        pythoncom.CoInitialize()
        _wmi = wmi.WMI()
        for item in _wmi.Win32_VideoController():
            gpu_type_list.append(item.name)
        gpu_type_list.sort()
        return ", ".join(gpu_type_list)

    def get_device_memory(self):
        return "%.1f GB" % (int(psutil.virtual_memory().total) / 1024.0 / 1024.0 / 1024.0)

    def get_memory_speed(self):
        pythoncom.CoInitialize()
        _wmi = wmi.WMI()
        return "%s MHz" % _wmi.Win32_PhysicalMemory()[0].ConfiguredClockSpeed

    def get_cpu_core_num(self):
        return psutil.cpu_count()

    def get_user_domain(self):
        return os.environ['userdomain']
    
    @staticmethod
    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        # print(s.getsockname()[0])
        return s.getsockname()[0]

    def get_physical_memory_number(self):
        pythoncom.CoInitialize()
        _wmi = wmi.WMI()
        PhysicalMemoryList = _wmi.Win32_PhysicalMemory()
        return str(len(PhysicalMemoryList))

    def get_physical_memory_speed(self):
        pythoncom.CoInitialize()
        _wmi = wmi.WMI()
        PhysicalMemoryList = _wmi.Win32_PhysicalMemory()
        speed_list = []
        for PhysicalMemory in PhysicalMemoryList:
            speed_list.append(str(PhysicalMemory.Speed) + " MHz")
        return ",".join(speed_list)

    def get_physical_memory_data_width(self):
        pythoncom.CoInitialize()
        _wmi = wmi.WMI()
        PhysicalMemoryList = _wmi.Win32_PhysicalMemory()
        data_width_list = []
        for PhysicalMemory in PhysicalMemoryList:
            data_width_list.append(str(PhysicalMemory.DataWidth))
        return ",".join(data_width_list)
    def get_disk_info(self):
        pythoncom.CoInitialize()
        _wmi = wmi.WMI()
        tmplist = []
        for physical_disk in _wmi.Win32_DiskDrive():
            for partition in physical_disk.associators("Win32_DiskDriveToDiskPartition"):
                for logical_disk in partition.associators("Win32_LogicalDiskToPartition"):
                    tmpdict = {}
                    tmpdict["Caption"] = logical_disk.Caption#磁盘名
                    tmpdict["DiskTotal"] = int(int(logical_disk.Size) / 1024 / 1024 / 1024) #磁盘大小 单位G
                    tmpdict["FreeSpace"] = int(int(logical_disk.FreeSpace) / 1024 / 1024 / 1024)#剩余可用磁盘大小 单位G
                    tmpdict["Percent"] = int(
                        100.0 * (tmpdict["DiskTotal"]  - tmpdict["FreeSpace"]) / tmpdict["DiskTotal"] )
                    tmplist.append(tmpdict)
        return tmplist
    def get_device_info(self):
        device_info={
        "cpu_type":self.get_cpu_type(),
        "gpu_type":self.get_gpu_type(),
        "device_memory":self.get_device_memory(),
        "memory_speed":self.get_memory_speed(),
        "cpu_core_num":self.get_cpu_core_num(),
        "user_domain":self.get_user_domain(),
        "physical_memory_number":self.get_physical_memory_number(),
        "physical_memory_speed":self.get_physical_memory_speed(),
        "physical_memory_data_width":self.get_physical_memory_data_width(),
        }
        return device_info
        

if __name__=="__main__":
    import platform
    Utils=WinUtils()
    print("设备信息: ")
    print(platform.processor())
    print("cpu_type: ",Utils.get_cpu_type())
    print("gpu_type: ",Utils.get_gpu_type())
    print("device_memory: ",Utils.get_device_memory())
    print("memory_speed: ",Utils.get_memory_speed())
    print("cpu_core_num: ",Utils.get_cpu_core_num())
    print("user_domain: ",Utils.get_user_domain())
    print("ip: ",Utils.get_ip())
    print("physical_memory_number: ",Utils.get_physical_memory_number())
    print("physical_memory_speed: ",Utils.get_physical_memory_speed())
    print("physical_memory_data_width: ",Utils.get_physical_memory_data_width())
    print("disk_info: ",Utils.get_disk_info())

