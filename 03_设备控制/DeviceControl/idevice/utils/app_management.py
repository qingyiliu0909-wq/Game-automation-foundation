import shlex
from pymobiledevice3.services.installation_proxy import InstallationProxyService
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from pymobiledevice3.services.dvt.instruments.process_control import ProcessControl
import logging
from DeviceControl.idevice.utils.download import download_file, is_hyperlink

#app的操作
def app_install(service_provider, path_or_url: str, download_callback=None):
    """安装ipa（根据url或本地path）"""

    if is_hyperlink(path_or_url):
        ipa_path = download_file(path_or_url)
    else:
        ipa_path = path_or_url
    installer = InstallationProxyService(lockdown=service_provider)
    return installer.install(ipa_path, handler=download_callback)

def app_uninstall(service_provider, bundle_identifier: str):
    """卸载ipa根据bundle_id"""
    InstallationProxyService(lockdown=service_provider).uninstall(bundle_identifier)

def app_launch(service_provider, arguments: str, kill_existing=True, suspended=False, env=None, stream=False):
    """运行ipa根据bundle_id返回pid"""
    if env is None:
        env = []
    with DvtSecureSocketProxyService(lockdown=service_provider) as dvt:
        process_control = ProcessControl(dvt)
        parsed_arguments = shlex.split(arguments)
        pid = process_control.launch(
            bundle_id=parsed_arguments[0],
            arguments=parsed_arguments[1:],
            kill_existing=kill_existing,
            start_suspended=suspended,
            environment=dict(env),
        )
        print(f"Process launched with pid {pid}")
        while stream:
            for output_received in process_control:
                logging.getLogger(f"PID:{output_received.pid}").info(output_received.message.strip())

def app_info(service_provider, bundle_identifier: str):
    """获取ipa详细信息根据bundle_id"""
    with InstallationProxyService(lockdown=service_provider) as iproxy:
        return iproxy.get_apps(bundle_identifiers=[bundle_identifier])

def get_running_pid(service_provider, app_bundle_identifier: str) -> str:
    """获取正在运行的ipa根据bundle_id"""
    with DvtSecureSocketProxyService(lockdown=service_provider) as dvt:
        process_control = ProcessControl(dvt)
        return process_control.process_identifier_for_bundle_identifier(app_bundle_identifier)

def kill_running_from_pid(service_provider, pid: int):
    """关闭正在运行的ipa根据pid"""
    with DvtSecureSocketProxyService(lockdown=service_provider) as dvt:
        process_control = ProcessControl(dvt)
        process_control.kill(pid)


def get_app_list(service_provider, app_type: str = "User", calculate_sizes: bool = False):
    """获取 App 列表"""
    from pymobiledevice3.services.installation_proxy import InstallationProxyService


    with InstallationProxyService(lockdown=service_provider) as iproxy:
        app_dict = iproxy.get_apps(app_type, calculate_sizes=calculate_sizes)
        apps = list(app_dict.values())
        for app in apps:
            short = app.get("CFBundleShortVersionString", "")
            build = app.get("CFBundleVersion", "")
            app["version"] = f'{short}.{build}',
        build = app.get("CFBundleVersion", "")

        return apps