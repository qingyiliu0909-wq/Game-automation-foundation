from PIL import Image
import io
from pymobiledevice3.services.dvt.dvt_secure_socket_proxy import DvtSecureSocketProxyService
from pymobiledevice3.services.dvt.instruments.screenshot import Screenshot
from pymobiledevice3.services.screenshot import ScreenshotService


#截图相关
def iter_screenshot(service_provider):
    """"一直截图留着后续做录屏用"""
    if int(service_provider.product_version.split(".")[0]) >= 17:
        with DvtSecureSocketProxyService(lockdown=service_provider) as dvt:
            screenshot_service = Screenshot(dvt)
            while True:
                yield screenshot_service.get_screenshot()
    else:
        screenshot_service = ScreenshotService(service_provider)
        while True:
            yield screenshot_service.take_screenshot()

def screenshot_png(service_provider):
    """"截图返回字符格式"""
    it = iter_screenshot(service_provider)
    png_data = next(it)
    it.close()
    return png_data

def screenshot(service_provider):
    """"截图"""
    png_data = screenshot_png(service_provider)
    return Image.open(io.BytesIO(png_data)).convert("RGB")
