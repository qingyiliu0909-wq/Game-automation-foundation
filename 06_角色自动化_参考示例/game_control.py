# 注意 因为所有的脚本基本都用到了 game_control 为了简化脚本 一些公共的库直接在这里导入
import requests
import json,sys,time,math,random,traceback
try:
    # Some environments only run PC UI automation and may not have iOS/Android dependencies
    # fully installed (or may have incompatible versions). DeviceOS is only used for simple
    # platform branching, so provide a tiny fallback to keep scripts runnable.
    from DeviceControl.Control import DeviceOS  # type: ignore
except Exception:  # noqa: BLE001
    from enum import Enum

    class DeviceOS(str, Enum):
        PC = "PC"
        IOS = "IOS"
        Android = "Android"
import uedriver
from uedriver import AltrunUnrealDriver
from loguru import logger
from pages.interface import scene
from pages.interface.scene import *

# syslist={}
udriver:AltrunUnrealDriver

def set_uedriver(Iudriver:AltrunUnrealDriver):
    global udriver
    if Iudriver!=None:
        udriver=Iudriver
        logger.warning("给脚本中全局udriver 赋值了")

def wait_in_dungeon_ready(udriver: AltrunUnrealDriver, timeout: float = 80) -> bool:
    """
    PC 委托进本：轮询局内小地图，出现即视为加载完成（不依赖 Loading 黑屏控件）。
    """
    path = common.get("局内小地图", "")
    if not path:
        logger.error("未配置 common['局内小地图']")
        return False
    deadline = time.time() + float(timeout)
    logger.info(f"等待局内小地图就绪（超时 {timeout}s）")
    while time.time() < deadline:
        try:
            if udriver.object_exist(path):
                logger.info("检测到局内小地图，进本加载完成")
                time.sleep(1)
                return True
        except Exception:
            pass
        time.sleep(0.5)
    logger.error("等待局内小地图超时")
    return False


def restart_entrust_challenge(udriver: AltrunUnrealDriver, timeout: float = 120) -> bool:
    """
    结算界面：再来一局 -> 再次挑战 -> 等待进本就绪（PC 等小地图）。
    """
    Auto_next_page(udriver)
    time.sleep(2)
    tapped_play_again = False
    for key in ("再来一局", "再次进行"):
        path = Entrust.get(key, "")
        if path and udriver.object_exist(path):
            udriver.find_object_and_tap(path)
            logger.info(f"结算：点击「{key}」")
            tapped_play_again = True
            time.sleep(2)
            break
    if not tapped_play_again:
        try:
            names = udriver.find_text("再来一局") or udriver.find_text("再次进行")
            if names:
                udriver.find_object_and_tap(names[0]["name"])
                logger.info("结算：按文本点击再来一局/再次进行")
                tapped_play_again = True
                time.sleep(2)
        except Exception:
            pass
    if not tapped_play_again:
        logger.error("结算界面未找到「再来一局」")
        return False

    confirm_key = "再次挑战" if Entrust.get("再次挑战") else "第二次开始挑战"
    deadline = time.time() + 30
    while time.time() < deadline:
        path = Entrust.get(confirm_key, "")
        if path and udriver.object_exist(path):
            udriver.find_object_and_tap(path)
            logger.info(f"结算：点击「{confirm_key}」确认再挑战")
            time.sleep(2)
            break
        try:
            names = udriver.find_text("再次挑战") or udriver.find_text("确认")
            if names:
                udriver.find_object_and_tap(names[0]["name"])
                time.sleep(2)
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        logger.warning("未检测到「再次挑战」确认框，尝试继续等待进本")

    if getattr(udriver, "platform", "") == "PC":
        return wait_in_dungeon_ready(udriver, timeout=timeout)
    Scene_loading(udriver, timeout=int(timeout))
    return True


def _object_exist_safe(udriver: AltrunUnrealDriver, path: str) -> bool:
    if not path:
        return False
    try:
        return bool(udriver.object_exist(path))
    except Exception:
        return False


def _tap_entrust_key(udriver: AltrunUnrealDriver, key: str) -> bool:
    path = Entrust.get(key, "")
    if path and _object_exist_safe(udriver, path):
        udriver.find_object_and_tap(path)
        logger.info(f"点击 Entrust「{key}」")
        return True
    return False


def is_in_entrust_prep_ui(udriver: AltrunUnrealDriver) -> bool:
    """历练/委托选关界面（未进局内）。"""
    for key in ("开始挑战", "委托"):
        if _object_exist_safe(udriver, Entrust.get(key, "")):
            return True
    list_root = Entrust.get("委托列表", "").replace("/SVerticalBox_0/SListPanel_0", "")
    return _object_exist_safe(udriver, list_root)


def is_on_main_city_hud(udriver: AltrunUnrealDriver) -> bool:
    """主城 HUD（菜单按钮可见）。主城也有小地图控件，不能单靠小地图判断局内。"""
    return _object_exist_safe(udriver, Main.get("菜单", ""))


def _has_escort_dungeon_signals(udriver: AltrunUnrealDriver) -> bool:
    """委托护送局内的附加信号（主城一般不具备）。"""
    for key in ("放弃挑战", "再来一局"):
        if _object_exist_safe(udriver, Entrust.get(key, "")):
            return True
    try:
        locs = udriver.getIndicatorLoc() or []
        if locs:
            return True
    except Exception:
        pass
    return False


def is_in_target_escort_dungeon(udriver: AltrunUnrealDriver) -> bool:
    """
    护送目标副本局内：小地图 + 非选关 + 非主城 + 有局内信号。
    仅小地图在主城也会为真，必须排除主城并确认指引/放弃挑战等。
    """
    minimap = common.get("局内小地图", "")
    if not _object_exist_safe(udriver, minimap):
        return False
    if is_in_entrust_prep_ui(udriver) or is_on_main_city_hud(udriver):
        return False
    return _has_escort_dungeon_signals(udriver)


def is_in_foreign_dungeon(udriver: AltrunUnrealDriver) -> bool:
    """其他副本局内（非主城、非护送目标局内）。"""
    if (
        is_on_main_city_hud(udriver)
        or is_in_entrust_prep_ui(udriver)
        or is_in_target_escort_dungeon(udriver)
    ):
        return False
    if _object_exist_safe(udriver, Entrust.get("放弃挑战", "")):
        return True
    minimap = common.get("局内小地图", "")
    if not _object_exist_safe(udriver, minimap):
        return False
    try:
        return bool(udriver.getIndicatorLoc())
    except Exception:
        return True


def exit_entrust_dungeon_to_main(udriver: AltrunUnrealDriver, timeout: float = 90) -> bool:
    """
    局内退出链：放弃挑战 -> 确定 -> 退出委托 -> 历练界面退出。
  回到可重新 open 历练 的状态。
    """
    logger.info("从局内/历练界面退出，准备重新进本")
    Auto_next_page(udriver)
    deadline = time.time() + float(timeout)

    while time.time() < deadline:
        if is_in_entrust_prep_ui(udriver):
            logger.info("已到历练/委托选关界面")
            return True
        if _object_exist_safe(udriver, Main.get("菜单", "")) or _object_exist_safe(
            udriver, Main.get("打开历练", "")
        ):
            logger.info("已到主界面/可打开历练")
            return True

        _tap_entrust_key(udriver, "放弃挑战")
        time.sleep(1.0)
        if not _tap_entrust_key(udriver, "放弃挑战-确定"):
            _tap_entrust_key(udriver, "再次挑战")
            _tap_entrust_key(udriver, "第二次开始挑战")
            try:
                names = udriver.find_text("确定")
                if names:
                    udriver.find_object_and_tap(names[0]["name"])
                    logger.info("按文本点击「确定」")
            except Exception:
                pass
        time.sleep(1.5)
        if not _tap_entrust_key(udriver, "退出委托-局内"):
            _tap_entrust_key(udriver, "退出委托")
        time.sleep(2)
        if not _tap_entrust_key(udriver, "历练界面退出"):
            _tap_entrust_key(udriver, "返回")
        time.sleep(2)
        close_blank_space(udriver)

    logger.error("退出副本超时")
    return False


def ensure_entrust_run_state(
    udriver: AltrunUnrealDriver, ename: str, *, is_escort: bool
) -> str:
    """
    运行前检测当前 UI 状态。

    返回:
      in_dungeon  - 已在目标局内，跳过 join_entrust
      settlement  - 结算「再来一局」界面
      need_join   - 需走历练 UI 进本
    """
    if is_escort:
        if _object_exist_safe(udriver, Entrust.get("再来一局", "")):
            logger.info("当前在结算界面")
            return "settlement"
        if is_in_target_escort_dungeon(udriver):
            logger.info("已在护送局内（局内小地图），继续局内流程")
            return "in_dungeon"
        if is_in_foreign_dungeon(udriver):
            logger.warning("检测到其他副本局内，先退出再重新进护送")
            if not exit_entrust_dungeon_to_main(udriver):
                raise Exception("无法从其他副本退出")
            return "need_join"
    elif _object_exist_safe(udriver, common.get("局内小地图", "")) and not is_in_entrust_prep_ui(
        udriver
    ):
        logger.warning(f"已在其他局内（目标 {ename}），先退出")
        if not exit_entrust_dungeon_to_main(udriver):
            raise Exception("无法从当前副本退出")
        return "need_join"

    if is_in_entrust_prep_ui(udriver):
        logger.info("当前在历练/委托选关界面，直接选关进本")
    return "need_join"


def Scene_loading(udriver: AltrunUnrealDriver,timeout=80):
    LoadingUIPath=""
    loading_keys = ["加载中3", "加载中2", "加载中4", "加载中"]
    if getattr(udriver, "platform", "") == "PC":
        loading_keys = ["加载中PC", "加载中3", "加载中2", "加载中4", "加载中", "加载中New"]
    for i in range(int(timeout/2)):
        time.sleep(2)
        if LoadingUIPath=="":
            for pathitem in loading_keys:
                logger.info(f"{pathitem}")
                if udriver.object_exist(common[pathitem]):
                    logger.warning(f"使用{pathitem} 的路径")
                    LoadingUIPath=common[pathitem]
                    break
                time.sleep(0.5)
                continue
            if LoadingUIPath=="":
                logger.error("没有检测到加载界面")
                return False
        elif not udriver.object_exist(LoadingUIPath):
            time.sleep(2)
            if udriver.platform != "PC":
                udriver.GM("gm HideUI BattleMain.Btn_GM")
            return True
    raise TimeoutError("Scene_loading 超时")

def update_memory(udriver: AltrunUnrealDriver,parameters:dict,info):
    logger.info(info+"截取内存")
    url = "http://127.0.0.1:8101/upload_memreport"
    if udriver.platform ==DeviceOS.PC.name:
        path = udriver.memReport()
        with open(path, 'rb') as file:
            data = {
                "game_version": parameters["package_version"],
                "report_user": "UAUTO",
                "info": info
            }
            requests.post(url, files={'file': file}, data=data)
    elif udriver.platform ==DeviceOS.IOS.name: # 安卓不能用 ios无法pull文件
        # IOSControl:IOSDevice=parameters["device_control"]
        path = udriver.memReport()
        # IOSControl.pull(path)
        pass
    elif udriver.platform ==DeviceOS.Android.name: # 安卓不能用 ios无法pull文件
        # AndroidControl:AndroidDevice=parameters["device_control"]
        # path = udriver.memReport()
        # AndroidControl.pull(path)
        pass


#打开指定系统
def open_interface(udriver: AltrunUnrealDriver,Uname="铸造",refresh=False):
    # 系统入口列表有些版本只有“打开菜单”后才会挂载到控件树里；
    # 这里先尝试直取，失败则打开菜单后重试一次。
    udriver.custom_interface("switchExcludeNotVisible")
    try:
        sysnums=udriver.find_child(Main["系统父级"])
    except Exception:
        try:
            udriver.find_object_and_tap(Main["菜单"])
            time.sleep(2)
            udriver.custom_interface("switchExcludeNotVisible")
            sysnums=udriver.find_child(Main["系统父级"])
        except Exception:
            sysnums=[]
    syslist={}
    for i in sysnums[::-1]:
        # 不同版本/平台系统入口的 row 结构可能变化，这里按“尽力枚举”处理：
        # - 能取到文本就写入 syslist
        # - 取不到就跳过，后续走 find_text 的兜底路径
        try:
            name=udriver.find_object_and_get_text(f"{Main['系统父级']}/{i}/SBox_0/SConstraintCanvas_0/SVerticalBox_0/SWidgetSwitcher_0/SBorder_0/SHorizontalBox_0/STextBlock_0")
            if name:
                syslist[name]=f"{Main['系统父级']}/{i}/SBox_0/SConstraintCanvas_0/SOverlay_0/SButton_0"
        except Exception:
            continue
    udriver.custom_interface("switchExcludeNotVisible")
    if Uname not in syslist.keys():
        # 如果系统列表父级已存在，说明菜单/系统面板已经打开，无需再点“菜单”
        try:
            if not udriver.object_exist(Main["系统父级"]):
                try:
                    udriver.find_object_and_tap(Main["菜单"])
                except Exception:
                    # 有些状态下主界面按钮会隐藏（比如菜单已打开/被弹窗遮挡），这里不强求
                    pass
                time.sleep(2)
        except Exception:
            pass
        if Uname == "历练":
            # PC 版本常见：必须点“历练”入口后，才会出现“委托”等子页签
            try:
                if "打开历练" in Main:
                    udriver.find_object_and_tap(Main["打开历练"])
                    return True
            except Exception:
                pass
            # 兜底：按文本点
            udriver.find_text_mouse_tap(Uname)
            return True
        if Uname == "活动":
            udriver.find_text_mouse_tap(Uname)
        elif Uname == "商店":
            udriver.find_object_and_tap(Main["打开商店"])
        elif Uname == "任务":
            udriver.find_object_and_tap(Main["打开任务"])
        elif Uname == "教学":
            udriver.find_object_and_tap(Main["打开教学"])
        elif Uname == "成就":
            udriver.find_object_and_tap(Main["打开成就"])
        else:
            ret=udriver.find_text(Uname)
            if ret!=[]:
                udriver.find_object_and_tap(ret[0]["name"].replace("SScaleBox_0/STextBlock_0","SEMCustomButton_0"))
        return True
    else:
        udriver.find_object_and_tap(syslist[Uname])
        return True

def join_entrust(udriver: AltrunUnrealDriver,Ename="追缉", level = -1,CName="",wait_team=print):
    """["勘察/无尽", "避险", "驱逐","探险/无尽","调停","护送","扼守/无尽","迁移","竞逐","拆解"]"""
    if level == -1:
        raise Exception("没有配置副本等级，请检查")
    open_interface(udriver,"历练")
    time.sleep(4)
    try:
        udriver.object_exist_only_tap(Entrust["委托"])
    except Exception:
        # 兜底：UI 路径变动时按文本点“委托”
        try:
            udriver.find_text_mouse_tap("委托")
        except Exception:
            pass
    time.sleep(2)
    # 有些版本必须先点“历练”再点“委托”，否则委托列表控件树不会挂载
    try:
        udriver.find_object(Entrust["委托列表"].replace("/SVerticalBox_0/SListPanel_0",""))
    except Exception:
        try:
            udriver.object_exist_only_tap(Entrust["委托"])
            time.sleep(2)
        except Exception:
            pass
    if Ename == "竞逐":
        udriver.find_object_and_tap(Entrust["悬赏委托"])
        time.sleep(2)
        udriver.find_object_and_tap(Entrust["进入悬赏委托"])
        time.sleep(2)
    elif Ename == "拆解":
        udriver.find_object_and_tap(Entrust["委托密函"])
        time.sleep(2)
        names = udriver.find_text("拆解")
        if len(names) == 0:
            raise Exception("限时副本不存在拆解本")
        udriver.find_object_and_tap(names[0]["name"].replace("SConstraintCanvas_1/SBox_0/STextBlock_0","SEMCustomButton_0"))
        time.sleep(2)
        
    else:
         for i in range(0,3):
            try:
                udriver.find_object(Entrust["委托列表"].replace("/SVerticalBox_0/SListPanel_0","")).setScrollOffset(i*4)
            except Exception:
                # 如果委托列表控件树找不到，通常是“历练/委托”没真正打开成功
                raise Exception("委托列表路径找不到：请用 debug_mode 录制一次“历练入口按钮”和“委托列表”区域路径，并更新 scene.py 的 Entrust['委托列表']") 
            time.sleep(2)
            panel = udriver.find_text(Ename)
            if panel != []:
                name = ""
                
                if udriver.platform != "PC":
                    name = panel[0]["name"].replace("/SConstraintCanvas_0/STextBlock_0","/SEMCustomButton_0")
                else:
                    name = panel[0]["name"].replace("/SConstraintCanvas_0/SScaleBox_0/STextBlock_0","/SEMCustomButton_0")
                    
                logger.info(name)
                udriver.find_object_and_tap(name)
                time.sleep(2)
                break
    
    if Ename != "拆解":
        time.sleep(2)
        # 选择难度
        # level 兼容两种传法：
        # 1) 直接传 Entrust_Level[Ename] 的 key（例如 30/40/50...）
        # 2) 传 0/1/2... 表示按升序 levels 的序号（0-based）
        level_key = level
        try:
            level_map = Entrust_Level[Ename]
            if level_key not in level_map:
                levels_sorted = sorted(level_map.keys())
                if isinstance(level_key, int) and 0 <= level_key < len(levels_sorted):
                    level_key = levels_sorted[level_key]
        except Exception:
            level_key = level
        try:
            widget_idx = Entrust_Level[Ename][level_key] - 1
            level_btn = (
                Entrust["难度等级"]
                + f"/SObjectWidget_{widget_idx}/SConstraintCanvas_0/SConstraintCanvas_0/SObjectWidget_0/SConstraintCanvas_0/SButton_0"
            )
            logger.info(
                f"选择难度：副本={Ename} 游戏等级={level_key} -> SObjectWidget_{widget_idx}"
            )
            udriver.find_object_and_tap(level_btn)
            time.sleep(2)
        except Exception:
            try:
                udriver.find_object_and_tap(Entrust["难度等级"]+f"/SObjectWidget_0/SConstraintCanvas_0/SConstraintCanvas_0/SObjectWidget_0/SConstraintCanvas_0/SButton_0")
                logger.warning("难度选择失败，已尝试默认第一个难度")
                time.sleep(2)
            except Exception:
                # UI 结构变动时难度区域可能找不到；继续走默认难度，避免用例直接失败
                logger.warning("难度选择控件找不到，继续使用当前默认难度")

    udriver.find_object_and_tap(Entrust["关闭召唤同伴辅助"])
    time.sleep(2)
    ButName='开始挑战'
    if "联机" in CName:
        wait_team()#组队同步调用
        ButName='匹配挑战'

    udriver.find_object_and_tap(Entrust[ButName])
    time.sleep(2)
    if Ename != "拆解":
        udriver.find_object_and_tap(Entrust["第二次开始挑战"])
    else:
        udriver.find_object_and_tap(Entrust["确认密函"])
    for i in range(7):
        if not udriver.object_exist(Entrust[ButName]):break
        if i >= 6:raise Exception("进入 副本失败")
        time.sleep(5)
    if getattr(udriver, "platform", "") == "PC":
        if not wait_in_dungeon_ready(udriver, timeout=120):
            raise Exception("进本后未检测到局内小地图")
    else:
        Scene_loading(udriver)
    time.sleep(4)
    return True

def join_entrust_yehanag(udriver: AltrunUnrealDriver, monsterName, lv):
    open_interface(udriver,"历练")
    time.sleep(4)
    udriver.object_exist_only_tap(Entrust["委托"])
    time.sleep(2)
    #夜航
    udriver.find_object_and_tap(Entrust_yehang["夜航手册"])
    time.sleep(2)
    level = -1
    if udriver.platform == "PC":
        lvLis = [30,40,50,55,60,65,70,80]
    else:
        lvLis = [40,50,55,60,65,70,80]
    for i in range(len(lvLis)):
        if lvLis[i] == lv:
            level = i
            break
    if level == -1:
        logger.error("等级选择有误")
        return
    levelTab = ""
    if udriver.platform == "PC":
        levelTab = f"/SConstraintCanvas_0/SConstraintCanvas_1/SObjectWidget_0/SConstraintCanvas_0/SHorizontalBox_0/SConstraintCanvas_0/SOverlay_0/SObjectWidget_0/SConstraintCanvas_0/SConstraintCanvas_0/SConstraintCanvas_0/ListViewT<ItemType>_0/SHorizontalBox_0/SListPanel_0/ObjectTableRowT_{level}/SConstraintCanvas_0/SConstraintCanvas_0/SEMCustomButton_0"         
                    
    else:
        if len(udriver.find_child("/SConstraintCanvas_0/SSafeZone_0/SConstraintCanvas_0/SConstraintCanvas_1/SObjectWidget_0/SConstraintCanvas_0/SConstraintCanvas_0/SHorizontalBox_0/SConstraintCanvas_0/SOverlay_0/SObjectWidget_0/SConstraintCanvas_0/SVerticalBox_0/SConstraintCanvas_0/SConstraintCanvas_0/SVerticalBox_0/ListViewT<ItemType>_0/SHorizontalBox_0/SListPanel_0")) == 10:
            level+=2
        levelTab = f"/SConstraintCanvas_0/SSafeZone_0/SConstraintCanvas_0/SConstraintCanvas_1/SObjectWidget_0/SConstraintCanvas_0/SConstraintCanvas_0/SHorizontalBox_0/SConstraintCanvas_0/SOverlay_0/SObjectWidget_0/SConstraintCanvas_0/SVerticalBox_0/SConstraintCanvas_0/SConstraintCanvas_0/SVerticalBox_0/ListViewT<ItemType>_0/SHorizontalBox_0/SListPanel_0/ObjectTableRowT_{level}/SConstraintCanvas_0/SConstraintCanvas_0/SEMCustomButton_0"
    udriver.find_object_and_tap(levelTab)
    time.sleep(2)
    for i in range(2):
        udriver.find_object(Entrust_yehang["怪物列表"]).setScrollOffset(i*6)
        panel = udriver.find_text(monsterName)
        if panel :
            break
    if panel == []:
        raise Exception("该等级中不存在该怪物")
        # logger.error("该等级中不存在该怪物")
        # return
    time.sleep(3)
    name = panel[0]["name"].replace("SConstraintCanvas_1/SVerticalBox_0/STextBlock_0","SWidgetSwitcher_0/SObjectWidget_0/SConstraintCanvas_0/SConstraintCanvas_0/SButton_0")
    udriver.find_object_and_tap(name)
    time.sleep(2)
    udriver.find_object_and_tap(Entrust["关闭召唤同伴辅助"])
    time.sleep(2)
    
    #是否要选择手册
    udriver.find_object_and_tap(Entrust_yehang["确认选择"])
    time.sleep(2)
    udriver.find_object_and_tap(Entrust_yehang["开始挑战"])
    time.sleep(2)
    Scene_loading(udriver)
    time.sleep(2)
    if udriver.platform!="PC":
        udriver.GM("gm HideUI BattleMain.Btn_GM")

def join_entrust_world(udriver: AltrunUnrealDriver, Ename=""):
    logger.info("解锁东国的历练活动")
    time.sleep(2)
    Auto_next_page(udriver)
    if "枯荣阁" in Ename:
        udriver.GM ("gm skipregion 1 104106 4")
    elif "尘漠石海" in Ename:
        udriver.GM ("gm skipregion 1 104105 2")
    elif "蓼风岭西侧" in Ename:
        udriver.GM ("gm skipregion 1 104107 6")
    elif "蓼风岭" in Ename:
        udriver.GM ("gm skipregion 1 104107 7")
    elif "潮声岩穴" in Ename:
        udriver.GM ("gm skipregion 1 104103 3")
    elif "浮星埠" in Ename:
        udriver.GM ("gm skipregion 1 104108 7")
    else:
        raise Exception(f"找不到需要的关卡-{Ename}")
    time.sleep(5)
    Scene_loading(udriver)
    udriver.GM("gm completeCondition 120106")
    time.sleep(4)
    TeleportMechanisms=udriver.getMechanismMaps("HardBossOpenMechanism")
    if TeleportMechanisms==[]:
            raise Exception("找不到坐标点")
    RunToCoordinate(udriver,{"x":TeleportMechanisms[0]["x"]-100,"y":TeleportMechanisms[0]["y"]-80,"z":TeleportMechanisms[0]["z"]})
    if "蓼风岭西侧" in Ename:
        udriver.setLocation({'x': 6656.65, 'y': 22952, 'z': 11325.6})
    Auto_next_page(udriver)
    time.sleep(4)
    Select_message(udriver,"开启挑战") #开启挑战
    time.sleep(2)
    if udriver.object_exist_only_tap(common["弹窗"]["关闭"]):time.sleep(1)
    if udriver.object_exist_only_tap(common["操作提示"]):time.sleep(1)
    udriver.object_exist_only_tap(Entrust["东国开启挑战"])
    time.sleep(2)
    if udriver.object_exist_only_tap(common["弹窗"]["关闭"]):time.sleep(1)
    if udriver.object_exist_only_tap(Entrust["第二次开始挑战"]):
        logger.info("开启挑战成功")
        time.sleep(2)
    else:
        udriver.find_text("开始挑战")
        raise Exception("开启任务失败")
    Scene_loading(udriver)
    Auto_next_page(udriver)



def Auto_next_page(udriver: AltrunUnrealDriver):
    biswindow=False
    for _ in range(5):
        if udriver.object_exist("/SConstraintCanvas_0/SConstraintCanvas_0"): #这个是弹窗的层级
            if udriver.object_exist_only_tap(common["弹窗"]["关闭"]) or udriver.object_exist_only_tap(common["弹窗"]["下一页"]):
                time.sleep(1)
                biswindow=True
                continue
            elif udriver.object_exist(common["复苏"]):
                if udriver.platform=="PC":
                    udriver.inputKeys("X","click",1)
                else:
                    udriver.object_exist_only_tap(common["复苏"])
                time.sleep(3)
                biswindow=True
        if udriver.platform != "PC":
            udriver.GM("gm HideUI BattleMain.Btn_GM")
        if udriver.object_exist_only_tap(common["空白区域"]):
            time.sleep(1)
            biswindow=True
            continue
        break
    return biswindow

def TurnTargetByDict(udriver: AltrunUnrealDriver,point1,point2):
    radian = math.atan2(point2["y"]-point1["y"], point2["x"]-point1["x"])
    angle = math.degrees(radian)
    udriver.setPRotation(0,angle,0)#因为可能会开启角色视角跟随 所以需要设置角色旋转和镜头旋转
    udriver.setCRotation(0,angle,0)
    return angle

def TargetDistByDict(point1,point2,is3D=False):
    try:
        point1,point2=(point1["x"],point1["y"],point1["z"]),(point2["x"],point2["y"],point2["z"])
        if is3D:
            squared_diff = sum((p1 - p2) ** 2 for p1, p2 in zip(point1, point2))
        else:
            squared_diff = (point1[0]-point2[0])**2+(point1[1]-point2[1])**2
        # 返回平方和的平方根，即欧几里得距离
        # print("距离为",math.sqrt(squared_diff))
        return math.sqrt(squared_diff)
    except:
        logger.error("距离计算错误"+traceback.format_exc())
        return 0

def before_after_log(func):
    def wrapper(*args, **kwargs):
        udriver = args[0] if args else None
        if udriver:
            udriver.cameraFollow(1)
            # udriver.GM("gm maxhp")
        result = func(*args, **kwargs)
        if udriver:
            udriver.cameraFollow(0)
        return result
    return wrapper

data_history = []
excluded_names = set()
last_data = None

def get_name_key(coord: dict):
    return coord.get("name")  # 只用 name 字段作为排除依据

@before_after_log
def TaskAutoinLoc(udriver: AltrunUnrealDriver,
                  special_names=[],
                  blacklist_names={}):
    global last_data
    commons=[common["交流文本父类"], common["消息选择父类2"]]
    for i in commons:
        if udriver.find_text("请选择任务模式"):
            return False
        if udriver.object_exist(i):
            print(f"当前还在交流界面中")
            return False
    current = udriver.getIndicatorLoc() or udriver.getTaskIndicatorLoc()

    if not isinstance(current, list) or not current:
        return False

    # 剔除黑名单中 name 的坐标
    current = [coord for coord in current if get_name_key(coord) not in excluded_names and get_name_key(coord) not in blacklist_names]
    if not current:
        return False

    data = current[-1]
    data_history.append(get_name_key(data))  # 记录 name

    # 保留最近3个
    if len(data_history) > 3:
        data_history.pop(0)

    # 连续三次 name 一样
    if len(data_history) == 5 and all(name == data_history[0] for name in data_history):
        repeated_name = data_history[0]
        excluded_names.add(repeated_name)
        print(f"[INFO] 节点名 '{repeated_name}' 连续三次重复，已加入排除列表")

        # 重新从 current 中移除该 name
        current = [coord for coord in current if get_name_key(coord) != repeated_name]
        if not current:
            return  False
        data = current[-1]
        data_history.clear()

    if last_data and data == last_data:
        try:
            if udriver.getIndicatorLoc():
                return False
        except:
            pass
        udriver.setLocation(data)
        time.sleep(1)
        udriver.inputKeys("W", "press", 1)
        time.sleep(0.1)
        udriver.inputKeys("W", "release", 1)
        time.sleep(0.1)
        time.sleep(1)
        return look_and_move_towards(udriver, data)

    last_data = data  # 更新缓存
    if  data["name"] in special_names:
        offset = random.randint(6, 30)
        udriver.setLocation(data["x"] + offset, data["y"] + offset, data["z"])
        time.sleep(1)
        udriver.inputKeys("W", "press", 1)
        time.sleep(0.1)
        udriver.inputKeys("W", "release", 1)
        time.sleep(1)
        return look_and_move_towards(udriver, data)
    elif  data["name"] in ["QuestTrigger0113"]:
        udriver.setLocation(data["x"], data["y"], data["z"])

        return udriver.behavior("螺旋跳")
    elif  data["name"] in ["TargetPoint_Kuangkeng","Mechanism_QuestTrigger_1180084"]:
        Mechanism= {"name": "Mechanism_QuestTrigger_1180082", "distance": 9.01498, "x": -33157, "y": -11253, "z": -6048}
        udriver.setLocation(Mechanism["x"], Mechanism["y"], Mechanism["z"])
        offset = random.randint(10, 30)
        return Go2TaskLoc(udriver, task_data={"x": data["x"] + offset, "y": data["y"] + offset, "z": data["z"]})
    elif  data["name"] in ["QuestPoint101"]:
        offset = random.randint(6, 30)
        udriver.setLocation(data["x"] + offset, data["y"] + offset, data["z"])
        time.sleep(1)
        look_and_move_towards(udriver, data)
        time.sleep(3)
        Select_message(udriver, "追忆的残影")
        auto_jump_over(udriver)
        Auto_next_page(udriver)
        time.sleep(3)
        return udriver.setLocation({"x":1857.01,"y":3660.65,"z":-2144.28})
    elif "Bomb" in  data["name"] or data['name'] in ['TargetPoint_kuangkeng_part01_door']:
        offset = random.randint(10, 30)
        udriver.cameraFollow(0)
        udriver.aimMonster(0)
        Go2TaskLoc(udriver, task_data={"x":data["x"] - offset - 10, "y":data["y"] - offset, "z":data["z"]})
        look_and_move_towards(udriver, data)
        time.sleep(3)
        udriver.setAimRotation(data)  # 瞄准障碍物
        fighting(udriver)
        return Go2TaskLoc(udriver, task_data={"x": data["x"] + offset, "y": data["y"] + offset, "z": data["z"]})

    else:
        data["x"] += random.randint(-10, -5) if random.random() < 0.5 else random.randint(5, 20)
        data["y"] += random.randint(-10, -5) if random.random() < 0.5 else random.randint(5, 20)
        CANNOT_TELEPORT_NAMES = [
            "LeaveCave",
            # 你遇到的不需要传送的 name 全部加进来
        ]
        if not Go2TaskLoc(udriver, task_data=data,CANNOT_TELEPORT_NAMES=CANNOT_TELEPORT_NAMES) and data["name"] not in CANNOT_TELEPORT_NAMES:

            return udriver.setLocation(data["x"],data["y"],data["z"])
        else:
            look_and_move_towards(udriver, data)



def look_and_move_towards(udriver, target_loc, stop_distance=300, max_attempts=10):
    for _ in range(max_attempts):
        current_loc = udriver.getLocation()
        TurnTargetByDict(udriver, current_loc, target_loc)
        dist = TargetDistByDict(current_loc, target_loc)
        if dist <= stop_distance:
            return True  # 到达或足够接近目标
        udriver.inputKeys("W", "press", 1)
        time.sleep(0.1)
        udriver.inputKeys("W", "release", 1)
    return False  # 超出最大尝试次数仍未达到目标


_failed_task_point_map = {}

def dict_hash(d):
    """将坐标 dict 转换为 hash key"""
    return f"{round(d['x'])}_{round(d['y'])}_{round(d['z'])}"

def Go2TaskLoc(udriver: AltrunUnrealDriver, isIndicator=False, task_data=None,CANNOT_TELEPORT_NAMES={}):
    udriver.GM("gm maxhp")

    if isIndicator:
        data = udriver.getIndicatorLoc()
        if isinstance(data, list) and data:
            data = data[-1]
        else:
            return False
    elif task_data:
        data = task_data
    else:
        data = udriver.getTaskIndicatorLoc()
        if isinstance(data, list) and data:
            data = data[-1]
        else:
            return False

    if data == {"x": 0, "y": 0, "z": 0}:
        logger.warning("获取任务坐标失败, 可能没有追踪任务")
        return False

    point_key = dict_hash(data)
    fail_count = _failed_task_point_map.get(point_key, 0)

    try:
        udriver.runToLocation(data["x"], data["y"], data["z"])
    except Exception as e:
        logger.warning(f"runToLocation 执行失败: {e}")
        return False

    max_wait_time = 60
    check_interval = 1.5
    start_time = time.time()

    last_loc = None
    stuck_count = 0
    max_stuck = 3
    reroute_count = 0
    max_reroute = 2

    while time.time() - start_time < max_wait_time:
        try:
            current_loc = udriver.getLocation()
            if not current_loc:
                return False
            dist_to_target = TargetDistByDict(current_loc, data)

            if dist_to_target < 80:
                logger.info(f"已到达任务目标点，距离：{dist_to_target:.2f}")
                _failed_task_point_map.pop(point_key, None)  # 到达则清除失败记录
                return True

            if last_loc:
                dist_moved = TargetDistByDict(current_loc, last_loc)
                if dist_moved < 5:
                    stuck_count += 1
                    logger.debug(f"疑似卡住，当前位置变化距离为 {dist_moved:.2f}，卡住次数 {stuck_count}")
                    if auto_jump_over(udriver):
                        break
                    if stuck_count >= max_stuck:
                        if reroute_count < max_reroute:
                            reroute_count += 1
                            logger.warning(f"第 {reroute_count} 次重新寻路...")
                            try:
                                udriver.inputKeys("W", "press")
                                time.sleep(0.5)
                                udriver.behavior("跳")
                                time.sleep(0.5)
                                udriver.inputKeys("W", "release")
                                udriver.runToLocation(data["x"], data["y"], data["z"])
                            except Exception as e:
                                logger.warning(f"重新 runToLocation 失败: {e}")
                            stuck_count = 0
                        else:
                            fail_count += 1
                            _failed_task_point_map[point_key] = fail_count
                            logger.warning(f"第 {fail_count} 次尝试失败去点 {point_key}")

                            if fail_count >= 3:
                                if data["name"] in CANNOT_TELEPORT_NAMES:
                                    return True
                                try:
                                    logger.warning("连续3次尝试失败，执行 setLocation 强制传送")
                                    udriver.setLocation(data["x"], data["y"], data["z"])
                                    udriver.inputKeys("W", "press")
                                    time.sleep(0.5)
                                    udriver.behavior("跳")
                                    time.sleep(0.5)
                                    udriver.inputKeys("W", "release")
                                    look_and_move_towards(udriver, data)
                                    _failed_task_point_map.pop(point_key, None)  # 成功后清除失败记录
                                    return True
                                except Exception as e:
                                    logger.error(f"setLocation 失败: {e}")
                                    return False
                            else:
                                return False
                else:
                    stuck_count = 0

            last_loc = current_loc
        except Exception as e:
            logger.warning(f"获取当前位置失败: {e}")
            return False

        time.sleep(check_interval)

    logger.warning("超时未能到达任务目标点")
    return False

def Select_message(udriver:AltrunUnrealDriver,select_msg="",random_select=False,not_select=["坐下"]):
    if not random_select and select_msg=="": #如果 
        if udriver.platform == "PC":
            udriver.inputKeys("F","click",1)
            return True
        else:
            return(try_tap_sequential_button(udriver, "跳过剧情", "跳过剧情文本","跳过剧情按钮") or
             try_tap_sequential_button(udriver, "自动播放", "跳过剧情文本","跳过剧情按钮") or
             try_tap_sequential_button(udriver, "消息选择", "消息选择文本", "消息选择按钮") or
             try_tap_sequential_button(udriver, "交流文本父类", "消息文本","消息按钮"))
    else:
        for _ in range(2):
            try:
                if udriver.platform == "PC":
                    configs = [
                        (scene.common["消息选择"], scene.common["消息选择文本"], scene.common["消息选择按钮"]),
                        (scene.common["消息选择父类2"], scene.common["消息文本2"], scene.common["消息按钮2"]) # 不要删除，Ex01有一章有这个选择
                    ]
                else:
                    # 非 PC 支持多个 UI 组合
                    configs = [
                        (scene.common["消息选择"], scene.common["消息选择文本"], scene.common["消息选择按钮"]),
                        (scene.common["交流文本父类"], scene.common["消息文本"], scene.common["消息按钮"]),
                        (scene.common["自动播放"], scene.common["跳过剧情文本"], scene.common["跳过剧情按钮"]),
                        (scene.common["消息选择父类2"], scene.common["消息文本2"], scene.common["消息按钮2"])
                    ]

                for base_path, text_key, button_key in configs:
                    if not udriver.object_exist(base_path):
                        continue
                    filtered_msgs = []
                    for i in udriver.find_child(base_path):
                        msg_path = f"{base_path}/{i}"
                        msg_text = udriver.find_object_and_get_text(msg_path + text_key)
                        if  msg_text not in not_select:
                            if select_msg!="" and select_msg in msg_text:#选择指定消息
                                return udriver.object_exist_only_tap(msg_path + button_key)
                            filtered_msgs.append((msg_path, msg_text)) 
                    if filtered_msgs!=[] and random_select:
                        msg_path, _ = random.choice(filtered_msgs)
                        return udriver.object_exist_only_tap(msg_path + button_key)
                    time.sleep(1)
            except:
                logger.warning(traceback.format_exc())
                logger.warning("消息选择失败")
                return False
    return False

def RideElevator(udriver:AltrunUnrealDriver,Ploc=None):
    """ 乘坐电梯 """
    if Ploc==None:Ploc=udriver.getLocation()
    ElevatorLoc=None
    EndControllerLoc=None
    for item in udriver.getMechanismLoc():# 1.先找电梯位置
        if "ElevatorInCharacter" in item["name"]:
            logger.info(f"找到了电梯开关: {item}")
            ElevatorLoc=item
            break
    if ElevatorLoc==None:return False

    for Citem in udriver.getMechanismMaps("Controller"):# 2.如果有电梯 就获取电梯控制器位置
        HDist=abs(Ploc["z"]-Citem["z"])
        if HDist<1500:
            Dist=TargetDistByDict(Ploc,Citem,True)
            logger.info(f"距离电梯开关 {Dist} 米")
            udriver.runToLocation(Citem)
            time.sleep(Dist/300)
            if abs(Ploc["z"]-ElevatorLoc["z"])>2000:# 3. 判断电梯是否在我这一层 不在的话就互换电梯
                logger.info("电梯不在我这一层 需要呼唤电梯")
                Select_message(udriver)
                for i in range(10): 
                    Ploc=udriver.getLocation()
                    Dist=TargetDistByDict(Ploc,ElevatorLoc)
                    if Dist<150:break
                    time.sleep(1.5)
                continue
        else:
            EndControllerLoc=Citem #电梯的另一端控制器
    for i in range(10): #4. 这里前往和电梯交互(因为电梯里面没有导航 所有只能每秒判断一下位置并移动过去)
        Ploc=udriver.getLocation()
        if abs(Ploc["z"]-EndControllerLoc["z"])<200:return True
        TurnTargetByDict(udriver,Ploc,ElevatorLoc)
        Dist=TargetDistByDict(Ploc,ElevatorLoc)
        if Dist>300:
            udriver.inputKeys("W","press",1)
            time.sleep(1)
            udriver.inputKeys("W","release",1)
            continue
        time.sleep(2)
        Select_message(udriver,"启动升降机")
        time.sleep(3)
        break
    for i in range(6):
        Ploc=udriver.getLocation()
        if abs(Ploc["z"]-EndControllerLoc["z"])<200:
            time.sleep(1)
            TurnTargetByDict(udriver,Ploc,EndControllerLoc)
            udriver.inputKeys("W","press",1)
            time.sleep(1)
            udriver.inputAction("Jump")
            time.sleep(1)
            udriver.inputKeys("W","release",1)
            break
        time.sleep(2)
    return True


def unlock_the_door(udriver:AltrunUnrealDriver,Ploc=None):
    """解锁门"""
    if Ploc==None:Ploc=udriver.getLocation()
    ElevatorLoc=None
    for item in udriver.getMechanismMaps("ConditionalGate"):# 条件门位置
        if "Quarry" in item["name"]:
            continue
        elif "ConditionalGate" in item["name"]:
            logger.info(f"找到了条件门: {item}")
            Dist = TargetDistByDict(Ploc, item, True)
            ElevatorLoc=item
            # udriver.setLocation(item)
            # time.sleep(3)
            RunToCoordinate(udriver,item)
            time.sleep(Dist/400)
            Select_message(udriver)
            unlock_mini_game(udriver)
            break
    if ElevatorLoc==None:return False



def RunToCoordinate(udriver:AltrunUnrealDriver,Coordinate,scope=1):
    """副本里面 或者单纯的寻路到指定坐标使用"""
    lastloc=udriver.getLocation()
    if not Coordinate:
        return False
    if abs(lastloc["z"]-Coordinate["z"])>4500:
        logger.info("这里要乘坐电梯")
        RideElevator(udriver,lastloc)
    udriver.runToLocation(Coordinate)
    time.sleep(1)
    cnum=2
    for i in range(80):
        loc=udriver.getLocation()
        distnum=TargetDistByDict(loc,Coordinate)
        logger.info(f"距离目标点还有：{distnum}")
        if distnum<scope*100:#到达指定范围之后
            return True
        else:
            move_dist=TargetDistByDict(loc,lastloc)
            if move_dist<80:#移动的距离小于70 说明没有动
                if distnum>350 and cnum>=0: #如果寻路没到终点 就往前走一点 跳一下（可能是有台阶）或者有弹窗
                    if cnum==2:
                        udriver.runToLocation(Coordinate)
                        time.sleep(1)
                    elif not Auto_next_page(udriver):
                        udriver.inputAction("Attack")# 这个主要处理可破坏物会挡路
                        time.sleep(1)
                        udriver.inputKeys("W","press","1")
                        time.sleep(0.3)
                        udriver.inputKeys("SpaceBar","click","1")
                        time.sleep(1)
                        udriver.inputKeys("W","release","1")
                    cnum=cnum-1
                else:
                    return True
            if cnum==0:
                return False
        lastloc=loc
        time.sleep(1.5)

def fighting(udriver:AltrunUnrealDriver):
    """攻击"""
    if random.randint(0,3)==1:
        udriver.behavior("换子弹")
    udriver.behavior("开枪",4)
    if random.randint(0,2)==1:
        udriver.behavior("重击")
    udriver.inputKeys("W","press")
    udriver.behavior("挥刀",4)
    udriver.inputKeys("W","release")
    if random.randint(0,4)==1:
        udriver.behavior("Q技能")
        time.sleep(1)
    if random.randint(0,2)==1:
        udriver.behavior("E技能")
        time.sleep(1)
        udriver.behavior("E技能")
    time.sleep(0.25)


def Auto_fighting(udriver:AltrunUnrealDriver,rounds=3,square=0):
    """副本里面用 square 是米(距离单位*100)"""
    udriver.aimMonster(1)
    for i in range(rounds):
        Auto_next_page(udriver)
        mloc = udriver.findMonsterLocation()
        if mloc==[]or mloc=={}:break
        ploc=udriver.getLocation()
        pm_Dist=TargetDistByDict(ploc,mloc)
        if square!=0 and pm_Dist>=square*100:break #超出攻击范围
        if pm_Dist>=500:
            udriver.runToLocation(mloc["x"]-15, mloc["y"]-15, mloc["z"])
            for i in range(int(pm_Dist/400/0.5)):
                udriver.inputAction("Fire")
                time.sleep(0.5)

        udriver.behavior("震地")
        time.sleep(0.5)
        fighting(udriver)
    udriver.aimMonster(0)

def Task_Auto_fighting(udriver:AltrunUnrealDriver,rounds=1):
    udriver.GM("gm addbuff 301 -1") # 上一个无敌和免控的buff
    udriver.GM("gm maxhp") # 防止上述指令没有用
    udriver.GM("gm maxsp")
    udriver.GM("gm attr ATK_Smash 100000")
    if Auto_next_page(udriver):
        time.sleep(3)
    Auto_fighting(udriver,rounds)

def jump_over(udriver:AltrunUnrealDriver):
    """跳过一次对话"""
    if udriver.platform == "PC":
        udriver.inputKeys("SpaceBar","click")
        time.sleep(1)
        udriver.inputKeys("SpaceBar","press")
        time.sleep(1.2)
        udriver.inputKeys( "SpaceBar","release")
        time.sleep(1)
    else:
        def click_jump_button(parent_key="跳过剧情"):
            children = udriver.find_child(common[parent_key])
            if children:
                for child in children:
                    path = common[parent_key] + "/" + child + common["跳过剧情文本"]
                    try:
                        child_text = udriver.find_object(path).get_text()
                    except:
                        continue

                    if child_text == "跳过":
                        click_path = common[parent_key] + "/" + child + common["跳过剧情按钮"]
                        success = udriver.find_object_and_tap(click_path)
                        return success
                return False
            else:
                return False
        click_res = click_jump_button("跳过剧情")
        if not click_res:
            click_res = click_jump_button("第一章跳过剧情")
        if not click_res:
            if udriver.find_text_mouse_tap("跳过"):
                time.sleep(0.5)
                udriver.object_exist_only_tap(common["确定"])
        else:
            time.sleep(0.5)
            udriver.object_exist_only_tap(common["确定"])


_last_clicked_text = None
_repeat_count = 0
def try_tap_sequential_button(udriver: AltrunUnrealDriver, parent_key: str, button_key: str, button=None) -> bool:
    global _last_clicked_text, _repeat_count
    if udriver.object_exist(common[parent_key]):
        children = udriver.find_child(common[parent_key])
        if children:
            if button:
                for child in children:
                    path = common[parent_key] + "/" + child + common[button_key]
                    try:
                        child_text = udriver.find_object(path).get_text()
                    except:
                        continue

                    print("候选文本:", child_text)

                    # 黑名单跳过
                    if child_text in ["查阅词条", "剧情回顾", "坐下", "贝蕾妮卡", "启动升降机", "卡米拉", "探查达顿",
                                      "播放中", "沙海冥想"]:
                        continue
                    # 连续点击限制
                    if child_text == _last_clicked_text and _repeat_count >= 4 and child_text != "跳过":
                        continue
                    click_path = common[parent_key] + "/" + child + common[button]
                    success = udriver.find_object_and_tap(click_path)
                    if success:
                        if child_text == "跳过":
                            time.sleep(2)
                            udriver.find_text_mouse_tap("确定")
                        if child_text == _last_clicked_text:
                            _repeat_count += 1
                        else:
                            _last_clicked_text = child_text
                            _repeat_count = 1
                    return success
                return False
            else:
                index = random.randint(0, len(children) - 1)
                path = common[parent_key] + "/" + children[index] + common[button_key]
                udriver.find_object_and_tap(path)
                return True
    return False


def auto_jump_over(udriver: AltrunUnrealDriver,pace=1):
    '''自动跳过对话'''
    for _ in range(pace):
        success_flag = False  # 记录是否有任何一次成功点击
        if udriver.platform == "PC":
            try:
                Auto_next_page(udriver)
                success = (
                    try_tap_sequential_button(udriver, "消息选择", "消息选择文本", "消息选择按钮") or
                    try_tap_sequential_button(udriver, "交流文本父类", "消息按钮") or
                    try_tap_sequential_button(udriver, "消息选择父类2", "消息按钮2")
                )

                if success:
                    success_flag = True

                # 判断立即返回的条件（跳过剧情或确认按钮）
                if udriver.object_exist(Story["空格"]) or \
                   udriver.object_exist(Story["空格One"]) or \
                   udriver.object_exist(Story["空格-序章"]):
                    jump_over(udriver)
                    time.sleep(3)
                time.sleep(2)

                if udriver.find_text_mouse_tap("确认") or udriver.find_text_mouse_tap("确定"):
                    time.sleep(2)
                    udriver.find_text_mouse_tap("取消")
                elif udriver.find_text("自动"):
                    udriver.inputKeys("Tab")
                    time.sleep(2)

            except Exception:
                pass

            time.sleep(1)

        else:
            try:
                Auto_next_page(udriver)

                success = (
                    try_tap_sequential_button(udriver, "第一章跳过剧情", "跳过剧情文本", "跳过剧情按钮") or
                    try_tap_sequential_button(udriver, "跳过剧情", "跳过剧情文本", "跳过剧情按钮") or
                    try_tap_sequential_button(udriver, "自动播放", "跳过剧情文本", "跳过剧情按钮") or
                    try_tap_sequential_button(udriver, "消息选择", "消息选择文本", "消息选择按钮") or
                    try_tap_sequential_button(udriver, "交流文本父类", "消息文本", "消息按钮") or
                    try_tap_sequential_button(udriver, "消息选择父类2", "消息文本2", "消息按钮2")
                )

                if success:
                    success_flag = True

                jump_over(udriver)

                if udriver.object_exist(common["确定"]):
                    udriver.find_object_and_tap(common["确定"])
                    time.sleep(3)

                if udriver.find_text_mouse_tap("确认"):
                    time.sleep(2)
                    udriver.find_text_mouse_tap("取消")


            except Exception:
                pass

            time.sleep(1)
    return success_flag



def tap_object_by_path(udriver:AltrunUnrealDriver,path):
    if isinstance(path, list):
        for p in path:
            if udriver.object_exist( p):
                udriver.find_object_and_tap( p)
                time.sleep(0.5)
                return True  # 如果找到一个并成功点击，返回 True
        return False  # 如果列表遍历完都没有找到，返回 False
    elif isinstance(path, str):
        if udriver.object_exist( path):
            udriver.find_object_and_tap( path)
            time.sleep(3)
            return True
        return False
    else:
        raise ValueError("The 'path' parameter should be either a string or a list of strings.")

def check_meiying(udriver: AltrunUnrealDriver, parameters: dict):
    # return
    if "name" in parameters and "联机" in parameters["name"]:
        return
    
    # 魅影
    Phantom = { '贝蕾妮卡': '1101', 
               '幻景': '1103', 
               '妮弗尔夫人': '1502',
            #    '刻舟': '1503', 
               '菲娜': '1801',
            '丽蓓卡': '2101',   
            '塔比瑟': '2301',
            # '扶疏': '2401',
              '琳恩': '3101', 
            #   '希尔妲': '3102',
            '耶尔与奥利弗': '3103', 
            '海尔法': '3201', 
            '玛尔洁': '3301', 
            '黎瑟': '4101', 
            # '止流': '4102',
            # '煜明': '4201', 
            '兰迪': '4202', 
            '西比尔': '4301', 
            '松露与榛子': '5101', 
            '奥特赛德': '5102',
            '赛琪': '5301', 
            '达芙涅': '5401'
            }

    meiying_one = ""
    meiying_two = ""
    
    if "meiying_one" in parameters and "meiying_two" in parameters:
        meiying_one = parameters["meiying_one"]
        logger.info("使用指定魅影：{}",meiying_one)
        meiying_two = parameters["meiying_two"]
        logger.info("使用指定魅影：{}",meiying_two)
    else: #随机
        hasPicked = []
        if "role" in parameters:
            hasPicked.append(parameters["role"])
        keys = list(Phantom.keys())
       
        for _ in range(10):
            key = keys[random.randint(0,len(keys) - 1)]
            if key in hasPicked:
                continue
            if meiying_one == "":
                meiying_one = key
                logger.info("使用随机魅影：{}",meiying_one)
                parameters["meiying_one"] = meiying_one
                hasPicked.append(key)
                continue
            if meiying_two == "":
                meiying_two = key
                logger.info("使用随机魅影：{}",meiying_two)
                parameters["meiying_two"] = meiying_two
                break

    # udriver.clickScreen(800, 800)
    time.sleep(2)
    meiyingdiaoyong(udriver, Phantom[meiying_one])
    time.sleep(2)
    meiyingdiaoyong(udriver, Phantom[meiying_two])
    time.sleep(3)




def pick_config(udriver: AltrunUnrealDriver, parameters: dict):
    if 'skip_pick' in parameters and parameters['skip_pick'] == 1:
        return
    # return
    melee_weapons = [[],
                      ['惩戒的炼火', '焦渴', '铸铁者'], 
                      ['幽鲨眼', '鎏金岁月', '失乡的獠牙'], 
                      ['蒙恩御礼', '凋零', '红叶一滴'],
                        ['希冀的丰稔', '塞壬的拥吻', '枯朽', '春玦戟','未来之鸽'],
                          ['辉珀刃', '慧谋的攻守', '孤子的缚锁', '流浪的蔷薇', '追忆的残影', '辉珀刃'],
                            ['苍瑚凝碧', '缠结', '不渝的梦海','泽世的慈雨']]




    
    ranged_weapons = [[], 
                      ['裂魂', '茵布拉花序', '弧光百劫', '烈焰孤沙'], 
                      ['群星无意赦免', '归墟棘轮', '崩解','银白敕令'],
                      ['蓝色脉动', '告谕圣音', '赘生'], 
                      ['引浪小调', '破晓赞美诗', '放逐怒雷', '祈请净火', '销骨','若华的飞光','雀舞云屏'],
                      ['告谕圣言', '剥离', '无序奇点'], 
                      ['嘶鸣', '爆破艺术', '缄默育种者', '圣裁日']]

    RolesByProperty=[[],
    ["扶疏","丽蓓卡","塔比瑟"],
    ['琳恩','玛尔洁','海尔法','耶尔与奥利弗'],
    ['赛琪','松露与榛子','达芙涅', '奥特赛德'],
    ['西比尔','兰迪', '黎瑟' ],
    ['妮弗尔夫人','莉兹贝尔','菲娜','刻舟'],
    ['贝蕾妮卡', '幻景']]


    open_interface(udriver,"整备")
    time.sleep(2)
    # 选角色
    udriver.find_object_and_tap(Servicing[f"查看所有"])  # 整备
    time.sleep(2)
    
    role = ""
    if "role" in parameters:
        role = parameters["role"]
        logger.info("使用指定角色: {}",role)
    else:
        role = random_name(RolesByProperty)
        logger.info("使用随机角色：{}",role)
        parameters["role"] = role
    
    pick_tab_by_name(udriver,role,RolesByProperty)
    
    # 选近战武器
    udriver.find_object_and_tap(Servicing["近战武器"])
    time.sleep(3)
    udriver.find_object_and_tap(Servicing[f"查看所有"])  # 整备
    time.sleep(2)

    melee_weapon = ""
    if "melee_weapon" in parameters:
        melee_weapon = parameters["melee_weapon"]
        logger.info("使用指定近战武器：{}",melee_weapon)
    else:
        melee_weapon = random_name(melee_weapons)
        logger.info("使用随机近战武器：{}",melee_weapon)
        parameters["melee_weapon"] = melee_weapon
        
    pick_tab_by_name(udriver,melee_weapon,melee_weapons)
    
    #选远程武器
    udriver.find_object_and_tap(Servicing["远程武器"])
    time.sleep(3)
    udriver.find_object_and_tap(Servicing[f"查看所有"])  # 整备
    time.sleep(2)
    
    ranged_weapon = ""
    if "ranged_weapon" in parameters:
        ranged_weapon = parameters["ranged_weapon"]
        logger.info("使用指定远程武器：{}",ranged_weapon)
    else:
        ranged_weapon = random_name(ranged_weapons)
        logger.info("使用随机远程武器：{}",ranged_weapon)
        parameters["ranged_weapon"] = ranged_weapon
        
    pick_tab_by_name(udriver,ranged_weapon,ranged_weapons)

    #TODO 选宠物
    # 贝蕾妮卡会有个同律武器tab
    if role in ["贝蕾妮卡","赛琪","琳恩"]:            
        udriver.object_exist_only_tap(Servicing["魔灵"])
    else:
        udriver.object_exist_only_tap(Servicing["同律-魔灵"])
    time.sleep(3)
    udriver.object_exist_only_tap(Servicing["魔灵-出战"])
    time.sleep(3)
    udriver.object_exist_only_tap(Servicing["返回"])
    time.sleep(2)

def random_name(property):
    try:
        row=random.randint(1,len(property) - 1)
        col=random.randint(0,len(property[row]) - 1)
        return property[row][col]
    except:
        logger.error("随机选择一个名字出错，请检查")

def pick_tab_by_name(udriver:AltrunUnrealDriver,name,property):
    for i,v in enumerate(property):
        if name in v:
            udriver.find_object_and_tap(f"{Servicing['角色属性列表']}/ObjectTableRowT_{i}")
    time.sleep(2)
    for j in udriver.find_child(Servicing["角色栏"]):
        udriver.find_object_and_tap(Servicing["角色栏"] + "/" + j)
        time.sleep(2)
        if udriver.find_text(name):
            udriver.find_object_and_tap(Servicing["出战"])
            time.sleep(2)
            # 魔之锲坏了 
            # # 进入魔之楔
            # udriver.find_object_and_tap(Servicing["魔之楔"])
            # time.sleep(2)
            # # 自动装配
            # udriver.find_object_and_tap(Servicing["魔之楔自动装配"])
            # time.sleep(4)
            # udriver.find_object_and_tap(Servicing["退出魔之楔界面"])
            # time.sleep(2)
            udriver.find_object_and_tap(Servicing["返回"])  # 整备
            time.sleep(2)
            return
    raise Exception(f"未找到该角色or武器：{name}")
    
def check_entrust(udriver: AltrunUnrealDriver, parameters: dict,entrust_name,level):
    # 数据库中指定的level等级优先级高
    if "level" in parameters:
        level = int(parameters["level"])
    join_entrust(udriver,entrust_name,level,parameters["name"],parameters["wait_team_sync"] if "wait_team_sync" in parameters else print)
    if udriver.platform!="PC":
        udriver.GM("gm HideUI BattleMain.Btn_GM")
        

def Re_Casename(parameters: dict):
    try:
        requests.post("http://127.0.0.1:8101/scheduler/send_me_preview", json={"email": "qa@example.com",
                                                                                 "msg": parameters["rename"]+"开始时间"+str(time.time()),
                                                                                 "msg_type": "text",
                                                                                 "robot": "QAPlatform"})
        parameters["name"] = parameters["rename"]
        logger.info(f"casename修改: {parameters['rename']}")
    except:
        pass

def Go_Level(udriver: AltrunUnrealDriver,parameters: dict):
    Ename = parameters['Ename']
    level = parameters['Level'] 
    join_entrust(udriver,Ename=f"{Ename}",level=level,CName="联机")

def meiyingdiaoyong(udriver: AltrunUnrealDriver, names):
    logger.info(f"创建魅影 {names} 进入场景")
    udriver.GM(f"gm cp {names} 1 1 60 6 0")

def execute_common_gm(udriver:AltrunUnrealDriver,parameters: dict):
    # udriver.GM("gm MockAllSystemCondition")
    udriver.GM("gm CompleteSystemConditionWithoutGuide")
    logger.info("解锁所有系统")
    time.sleep(2)
    if "SkipGM" in parameters:
        return
    udriver.GM("gm SuccessAllSystemGuide")
    logger.info("解锁所有系统教学")
    time.sleep(2)
    
    udriver.GM("gm UnLockAllDungeonLevels")
    logger.info("解锁所有副本")
    time.sleep(2)
    
    udriver.GM("gm UnLockAllDungeonSelectLevels")
    logger.info("解锁所有副本入口")
    time.sleep(2)
    close_blank_space(udriver)
    
    udriver.GM("gm UnlockMonsterGallery")
    logger.info("解锁所有怪物教学")
    time.sleep(2)
    
    # udriver.GM("gm succquestchain 100103")
    # logger.info("解锁教学")
    # time.sleep(2)

    udriver.GM("sgm aac")
    logger.info("获得所有角色")
    time.sleep(2)

    udriver.GM("sgm aas")
    logger.info("获得所有角色皮肤")
    time.sleep(2)
    
    udriver.GM("sgm aaw")
    logger.info("获得所有武器")
    time.sleep(3)

    udriver.GM("sgm aaws")
    logger.info("获得所有武器皮肤")
    time.sleep(3)
    
    udriver.GM("sgm aad")
    logger.info("获得所有饰品")
    time.sleep(3)
    
    udriver.GM("sgm aamd")
    logger.info("获得所有坐骑")
    time.sleep(3)

    udriver.GM("sgm aar")
    logger.info("获得大量的材料")
    time.sleep(2)

    udriver.GM("sgm ar 101 100000000")
    logger.info("获得大量铜币")
    
    udriver.GM("sgm aam 10")
    logger.info("等级提升至满级，且获得所有魔之楔")
    time.sleep(2)
    
    udriver.GM("sgm aab")
    logger.info("获取很多铸造材料")
    time.sleep(2)

    udriver.GM("sgm macml")
    logger.info("角色升至满级")
    time.sleep(2)

    udriver.GM("sgm sacsl 10")
    logger.info("技能全满级")
    udriver.GM("sgm sl 65")
    logger.info("历练等级满级")
    udriver.GM("sgm mawml")
    logger.info("武器升至满级")
    time.sleep(2)
  
    udriver.GM("gm CompleteCondition 4380")
    logger.info("解锁整容预设")
    time.sleep(3)

    udriver.GM("sgm CompleteCondition 4220")
    logger.info("解锁活动")

    time.sleep(2)
    udriver.GM("sgm WikiEntryUnlockAll")
    logger.info("解锁百科词条")
    time.sleep(1)
    
    # 等下弹窗
    pet_id = random.randint(0,len(pet_list) - 1)
    udriver.GM(f"sgm GMGetTestPet 1 {pet_list[pet_id]} 1 10161")
    close_blank_space(udriver)
    time.sleep(1)
    if udriver.platform == "PC":
        time.sleep(10)
    else:
        # if "device_perf" in parameters :
        #     if parameters["device_perf"]>=4:time.sleep(60)
        #     elif parameters["device_perf"]>=2:time.sleep(100)
        #     else:time.sleep(180)
        # else:
        time.sleep(180)
    close_blank_space(udriver)

def close_blank_space(udriver:AltrunUnrealDriver):
    logger.info("空白区域检查开始")
    try:
        for i in range(15):
            if udriver.object_exist_only_tap(common["空白区域"]):
                time.sleep(2.5)
                continue
            break
        # 手机端点空白区域会进到GM页面
        udriver.object_exist_only_tap(common["关闭GM"])
        logger.info("空白区域检查结束")
    except:
        logger.error("空白区域检查失败")

def unlock_mini_game(udriver:AltrunUnrealDriver):
    res = False
    is_open = udriver.object_exist_only_tap(common["操作提示"])
    time.sleep(0.5)
    udriver.unlockMiniGames()
    time.sleep(0.5)
    if udriver.object_exist_only_tap(Task["调停-快速破解"]):
        res=True
        time.sleep(2)
    if udriver.object_exist_only_tap(Task["避险-快速破解"]):
        res=True
        time.sleep(2)
    
    is_close = udriver.object_exist_only_tap(common["关闭小游戏"])#这个是副本里面的关闭小游戏
    if not is_close:
       is_close = udriver.object_exist_only_tap(Task["关闭小游戏"])
    
    if not res :
        res = is_open and is_close
    time.sleep(1)
    return res

def prepare_fighting(udriver:AltrunUnrealDriver,parameters: dict,attack=400,is_god=False,move_speed=1):
    """
    attack 攻击力
    is_god 是否是神
    move_speed 移动速度
    """
    if move_speed != 1:
        udriver.custom_interface("setMoveSpeed",move_speed)
    if is_god:
        udriver.GM("gm god")
        return
    time.sleep(0.2)
    udriver.GM("gm maxsp")
    time.sleep(0.2)
    udriver.GM("gm maxhp")
    time.sleep(0.2)
    udriver.GM(f"gm attr ATK_Smash {attack}")
    time.sleep(0.2)


def Trace_Task(udriver:AltrunUnrealDriver,task_name):#打开指定任务
    for i in udriver.find_child(Task['任务界面描述']):
        print(udriver.find_object(Task['任务界面描述']+'/'+i+Task['任务界面描述一级文本']).get_text())
        if task_name in udriver.find_object(Task['任务界面描述']+'/'+i+Task['任务界面描述一级文本']).get_text():
            print(Task['任务界面描述']+'/'+i+Task["任务界面描述二级按钮"])
            time.sleep(2)
            udriver.find_object(Task['任务界面描述']+'/'+i+Task["任务界面描述二级按钮"]).tap()
            time.sleep(2)
            udriver.find_object(Task['追踪任务']).tap()
            time.sleep(2)
            break

    for _ in  range(10):
        if udriver.find_text("世界地图"):
            udriver.inputKeys("Escape")
            time.sleep(2)
        elif udriver.object_exist(Task["返回"]):
            udriver.find_object_and_tap(Task["返回"])
            udriver.inputKeys("Escape")
            time.sleep(2)
        elif udriver.object_exist(common["关闭游戏"]):
            udriver.inputKeys("Escape")
            time.sleep(2)
        else:
            time.sleep(0.5)
    return False

# 根据动态事件id开启动态事件 
def open_dynquest_dystory(udriver: AltrunUnrealDriver,DynQuestId):
    udriver.GM(f"sgm ForceStartDynQuest {DynQuestId}")
    udriver.GM("sgm ResetDynQuestProbability 1 1")
    udriver.GM(f"gm ForceStartDynQuest {DynQuestId}")
    time.sleep(4)
    Scene_loading(udriver)
    time.sleep(2)

def RunToLocAndJumpDialog(udriver: AltrunUnrealDriver, loc, space=2):
    RunToCoordinate(udriver,loc)
    time.sleep(2)
    TurnTargetByDict(udriver,udriver.getLocation(),loc)
    auto_jump_over(udriver,space)


def go_to_Loc(udriver: AltrunUnrealDriver):
    # 获取任务点或当前位置
    data = udriver.getTaskIndicatorLoc()
    if data:
        data = data[0]
    else:
        data = udriver.getLocation()

    offset_x = random.randint(-800, 800)
    offset_y = random.randint(-800, 800)

    udriver.runToLocation(
        data["x"] + offset_x,
        data["y"] + offset_y,
        data["z"]
    )

    time.sleep(random.uniform(1.5, 2.5))

