
from pymobiledevice3.lockdown import LockdownClient
from pymobiledevice3.services.afc import AfcService
from pymobiledevice3.services.house_arrest import HouseArrestService
from typing import List
from pydantic import BaseModel
import datetime
import posixpath
import pathlib
from pathlib import Path
from pymobiledevice3.exceptions import AfcException, AfcFileNotFoundError


#文件操作
class FileInfo(BaseModel):
    name: str
    size: int
    mtime: datetime.datetime
    ifmt: str

    def is_dir(self) -> bool:
        return self.ifmt == "S_IFDIR"

def stat_file(afc: AfcService, path: str) -> FileInfo:
    info = afc.stat(path)
    info['st_name'] = posixpath.basename(path)
    return stat2fileinfo(info)

def stat2fileinfo(info: dict) -> FileInfo:
    # {'st_size': 326, 'st_blocks': 8, 'st_nlink': 1, 'st_ifmt': 'S_IFREG',
    #  'st_mtime': datetime.datetime(2023, 7, 7, 18, 55, 10, 755297),
    #  'st_birthtime': datetime.datetime(2023, 7, 7, 18, 55, 10, 754835),
    #  'st_name': 'com.apple.ibooks-sync.plist'}
    return FileInfo(
        name=info["st_name"],
        size=info["st_size"],
        ifmt=info["st_ifmt"],
        mtime=info["st_mtime"],
    )


class AFCFileClient:
    """文件操作类"""
    def __init__(self, lockdown: LockdownClient, bundle_id: str = None, documents_only: bool = False):
        if bundle_id:
            #根据传入包名对具体的包进行操作（应用沙盒内）
            self.afc = HouseArrestService(lockdown=lockdown, bundle_id=bundle_id, documents_only=documents_only)
        else:
            # 对手机内部文件进行操作
            self.afc = AfcService(lockdown=lockdown)

    def __enter__(self):
        self.afc.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.afc.__exit__(exc_type, exc_val, exc_tb)

    def list_dir(self, remote_path: str) -> List[FileInfo]:
        """返回所有列表"""
        items: List[FileInfo] = []
        for name in self.afc.listdir(remote_path):
            try:
                file_info = stat_file(self.afc, posixpath.join(remote_path, name))
                items.append(file_info)
            except AfcException:
                continue
        items.sort(key=lambda x: [x.is_dir(), x.mtime], reverse=True)
        return items

    def remove(self, path: str):
        """删除文件"""
        self.afc.rm(path)

    def push(self, local_file_path: str, remote_path: str):
        """
            往手机里面塞文件
            local_file_path： 本地文件地址
            remote_path：手机内文件地址
        """
        local_file = Path(local_file_path)
        if not local_file.exists():
            raise FileNotFoundError(f"Local file not found: {local_file_path}")

        remote_info = None
        try:
            remote_info = stat_file(self.afc, remote_path)
        except AfcFileNotFoundError:
            pass

        if remote_info and remote_info.is_dir():
            remote_path = posixpath.join(remote_path, local_file.name)

        with local_file.open("rb") as f:
            self.afc.set_file_contents(remote_path, f.read())

    def pull(self, remote_path: str, local_path: str, force: bool = False):
        """
            从手机里面把文件取出来
            local_file_path： 本地文件地址
            remote_path：手机内文件地址
        """
        local_file = pathlib.Path(local_path)

        if local_file.is_dir():
            local_file /= posixpath.basename(remote_path)

        if local_file.exists() and not force:
            raise FileExistsError(f"{local_file} already exists. Use force=True to overwrite.")

        if not local_file.parent.exists():
            raise FileNotFoundError(f"Parent folder does not exist: {local_file.parent}")

        finfo = stat_file(self.afc, remote_path)
        if finfo.is_dir():
            raise IsADirectoryError("remote_path is a directory")

        local_file.write_bytes(self.afc.get_file_contents(remote_path))
        return str(local_file)
