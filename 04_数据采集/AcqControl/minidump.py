import ctypes
import win32com.client
import uuid,os
import sys
# 导入Windows API函数
dbghelp = ctypes.windll.dbghelp

def create_mini_dump(file_path, process_id):
    print(file_path,process_id)
    # 打开进程
    process_handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0800 | 0x0010 | 0x0040, False, process_id)
    dump_file = ctypes.windll.kernel32.CreateFileW(
        file_path,
        1073741824,
        0,
        None,
        2,
        0,
        None,
    )
    if process_handle:
        # 创建Dump文件
        result = dbghelp.MiniDumpWriteDump(
            process_handle,
            process_id,
            dump_file,
            0x00000002,  # MiniDumpWithFullMemory
            None,
            None,
            None
        )
        if result:
            print(f"Dump文件已生成：{file_path}")
        else:
            print("生成Dump文件失败",result)

        # 关闭进程句柄
        ctypes.windll.kernel32.CloseHandle(process_handle)
    else:
        print(f"无法打开进程 {process_id}")

def get_process_id_by_name(process_name):
    wmi = win32com.client.GetObject('winmgmts:')
    process_ids=[]
    for process in wmi.InstancesOf('Win32_Process'):
        if process.Properties_('Name').Value == process_name:
            process_ids.append(process.Properties_('ProcessId').Value)
    return process_ids

if __name__ == "__main__":
    if len(sys.argv)<2:
        print( "请输入应用程序名 ")
        exit()
    app_name=sys.argv[1]
    # 用于生成Dump文件的进程的进程ID
    target_process_ids=get_process_id_by_name(app_name)
    for i in target_process_ids:
        dump_file_path = f"{os.getcwd()}\\{uuid.uuid4()}.dmp"  
        create_mini_dump(dump_file_path, i)

    # input("回车结束")
