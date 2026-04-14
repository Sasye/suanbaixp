"""
300英雄 占卜自动化 - GUI 启动器
启动时自动请求管理员权限。
"""

import sys
import os
import ctypes


def is_admin():
    """检查当前是否以管理员权限运行。"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """以管理员权限重新启动当前脚本。"""
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
    
    # ShellExecuteW: 'runas' 会触发 UAC 提权
    ret = ctypes.windll.shell32.ShellExecuteW(
        None, 'runas', sys.executable, f'"{script}" {params}', None, 1
    )
    # 返回值 > 32 表示成功
    return ret > 32


def main():
    if not is_admin():
        print('正在请求管理员权限...')
        if run_as_admin():
            sys.exit(0)  # 原进程退出,提权后的新进程将接管
        else:
            print('获取管理员权限失败，尝试以普通权限继续...')
    
    # 管理员权限已获取（或用户拒绝但继续），启动 GUI
    from gui import DivinationGUI
    app = DivinationGUI()
    app.run()


if __name__ == '__main__':
    main()
