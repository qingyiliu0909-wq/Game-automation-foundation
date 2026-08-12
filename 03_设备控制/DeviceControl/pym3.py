from pymobiledevice3.lockdown import LockdownClient
from pymobiledevice3.services.installation_proxy import InstallationProxyService
from pymobiledevice3.services.house_arrest import HouseArrestService


class IOSDeviceController:
    def __init__(self, udid: str):
        self.udid = udid
        self.lockdown = LockdownClient(udid)
        self.install_proxy = InstallationProxyService(self.lockdown)

    def get_device_info(self):
        # 设备详细信息，包含多个字段
        return self.lockdown.all_values

    def get_installed_apps(self):
        # 获取已安装应用列表
        return self.install_proxy.browse()

    def start_app(self, bundle_id: str):
        # 启动应用
        self.install_proxy.installation_proxy.start(bundle_id)

    def stop_app(self, bundle_id: str):
        # 关闭应用，利用安装代理的停止功能
        self.install_proxy.installation_proxy.stop(bundle_id)

    def push_file(self, bundle_id: str, local_path: str, remote_path: str):
        # 通过 HouseArrest 服务推送文件
        with HouseArrestService(self.lockdown, bundle_id) as house_arrest:
            afc = house_arrest.afc_client
            with open(local_path, "rb") as f:
                content = f.read()
            afc.write_file(remote_path, content)

    def pull_file(self, bundle_id: str, remote_path: str, local_path: str):
        # 通过 HouseArrest 服务拉取文件
        with HouseArrestService(self.lockdown, bundle_id) as house_arrest:
            afc = house_arrest.afc_client
            content = afc.read_file(remote_path)
            with open(local_path, "wb") as f:
                f.write(content)

    def close(self):
        # 断开 lockdown 连接
        self.lockdown.close()

# 用法示例
if __name__ == "__main__":
    udid = "你的设备UDID"
    bundle_id = "com.example.YourApp"

    dev = IOSDeviceController(udid)
    print("设备信息:", dev.get_device_info())
    print("已安装应用:", dev.get_installed_apps())

    dev.start_app(bundle_id)
    # ...操作一段时间
    dev.stop_app(bundle_id)

    dev.push_file(bundle_id, "D:/Download/ue4commandline.txt", "/Documents/ue4commandline.txt")
    dev.pull_file(bundle_id, "/Documents/ue4commandline.txt", "D:/Download/copied_ue4commandline.txt")

    dev.close()
