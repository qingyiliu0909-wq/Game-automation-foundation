from packaging.version import Version
import logging
from pymobiledevice3.services.amfi import AmfiService
from pymobiledevice3.services.mobile_image_mounter import auto_mount
from pymobiledevice3.exceptions import AlreadyMountedError
from pymobiledevice3.common import get_home_folder



#开发者模式
def enable_developer_mode(service_provider):
    if Version(service_provider.product_version) >= Version("16"):
        if not service_provider.developer_mode_status:
            logging.info('enable developer mode')
            AmfiService(service_provider).enable_developer_mode()
        else:
            logging.info('developer mode already enabled')

    try:
        xcode = get_home_folder() / 'Xcode.app'
        xcode.mkdir(parents=True, exist_ok=True)
        auto_mount(service_provider, xcode=xcode)
        logging.info('mount developer image')
    except AlreadyMountedError:
        logging.info('developer image already mounted')
