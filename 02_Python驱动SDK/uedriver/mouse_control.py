import mouse,time
from loguru import logger
def ClickScreen(x,y,ClickType=1,duration=0):
    """点击屏幕
    ClickType 1:left,2:middle,3:right
    duration:持续时间
    """
    if x==0 and y==0:
        return False
    if ClickType==1:
        ClickType="left"
    elif ClickType==2:
        ClickType="middle"
    elif ClickType==3:
        ClickType="right"
    mouse.move(x,y)
    time.sleep(0.2)
    mouse.press(ClickType)
    time.sleep(duration)
    mouse.release(ClickType)
    logger.info(f"点击屏幕 {x,y}")

def SlideScreen(x,y,x1,x2,duration=0):
    """左键滑动屏幕"""
    if x==0 and y==0:
        return False
    mouse.move(x,y)
    time.sleep(0.2)
    mouse.press()
    mouse.move(x1,x2,duration=duration)
    mouse.release()
    logger.info(f"鼠标滑屏 {x,y,x1,x2}")


def MoveAndScroll(x,y,delta):
    """移动的指定位置并滚动滚轮 delta 方向"""
    if x==0 and y==0:
        return False
    mouse.move(x,y)
    time.sleep(0.5)
    mouse.wheel(delta)
    time.sleep(0.5)
    logger.info(f"鼠标 移动并滚动 {x,y} {delta}")



def MouseScreen(x,y):
    """移动鼠标至指定位置
    """
    mouse.move(x.split(".")[0],y.split(".")[0])
    time.sleep(0.2)