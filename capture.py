"""
屏幕截图和模板匹配功能（基于 OpenCV）。
"""

import os
import sys
import logging
import ctypes
import ctypes.wintypes

import cv2
import numpy as np
import mss

from config import TEMPLATE_DIR

logger = logging.getLogger(__name__)

# Windows API
user32 = ctypes.windll.user32


def get_template_path(filename: str) -> str:
    """获取模板文件的路径，兼容 PyInstaller 打包。"""
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, TEMPLATE_DIR, filename)


def find_game_window() -> dict | None:
    """
    查找 300英雄 游戏窗口，返回 mss 格式的区域字典。
    """
    game_titles = ['300英雄', '300Heroes']
    
    found_hwnd = None
    
    def enum_callback(hwnd, _):
        nonlocal found_hwnd
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        for gt in game_titles:
            if gt in title:
                # 检查窗口是否最小化或隐藏 (位置 -32000 = 最小化)
                rect = ctypes.wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left
                h = rect.bottom - rect.top
                if rect.left <= -30000 or rect.top <= -30000 or w < 200 or h < 200:
                    logger.debug(f'跳过无效窗口: "{title}" at ({rect.left},{rect.top}) size {w}x{h}')
                    return True  # 继续枚举，跳过这个无效窗口
                found_hwnd = hwnd
                return False  # 停止枚举
        return True
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    
    if found_hwnd is None:
        return None
    
    rect = ctypes.wintypes.RECT()
    user32.GetWindowRect(found_hwnd, ctypes.byref(rect))
    
    region = {
        'left': rect.left,
        'top': rect.top,
        'width': rect.right - rect.left,
        'height': rect.bottom - rect.top,
    }
    logger.info(f'找到游戏窗口: {region}')
    return region


# 缓存游戏窗口区域
_cached_game_region: dict | None = None


def get_window_offset() -> tuple[int, int]:
    """
    返回游戏窗口左上角的屏幕绝对坐标 (x, y)。
    截图中的坐标 + offset = 屏幕绝对坐标（用于 pyautogui.click）。
    """
    if _cached_game_region:
        return (_cached_game_region['left'], _cached_game_region['top'])
    region = find_game_window()
    if region:
        return (region['left'], region['top'])
    return (0, 0)


def screenshot() -> np.ndarray:
    """
    截取游戏窗口区域。
    优先查找游戏窗口，找不到则截取整个虚拟屏幕（所有显示器）。
    """
    global _cached_game_region
    
    with mss.mss() as sct:
        # 尝试用缓存的窗口区域
        if _cached_game_region:
            try:
                img = sct.grab(_cached_game_region)
                frame = np.array(img)
                return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            except Exception:
                _cached_game_region = None
        
        # 查找游戏窗口
        region = find_game_window()
        if region and region['width'] > 100 and region['height'] > 100:
            _cached_game_region = region
            img = sct.grab(region)
            frame = np.array(img)
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        
        # 回退：截取整个虚拟屏幕（monitors[0] = 所有显示器合并）
        logger.warning('未找到游戏窗口，截取全部屏幕')
        monitor = sct.monitors[0]
        img = sct.grab(monitor)
        frame = np.array(img)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


def screenshot_region(x: int, y: int, w: int, h: int) -> np.ndarray:
    """截取指定区域，返回 BGR numpy 数组。"""
    with mss.mss() as sct:
        region = {'left': x, 'top': y, 'width': w, 'height': h}
        img = sct.grab(region)
        frame = np.array(img)
        return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


def load_template(filename: str) -> np.ndarray:
    """加载模板图片为 BGR numpy 数组。"""
    path = get_template_path(filename)
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f'模板文件不存在: {path}')
    return img


def find_template(screen: np.ndarray, template: np.ndarray,
                  threshold: float = 0.8) -> tuple[int, int] | None:
    """
    在截图中搜索模板，返回匹配中心坐标或 None。
    使用 OpenCV TM_CCOEFF_NORMED（归一化互相关）。
    """
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    
    if max_val >= threshold:
        th, tw = template.shape[:2]
        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        return (cx, cy)
    return None


def find_template_score(screen: np.ndarray, template: np.ndarray
                        ) -> tuple[float, tuple[int, int]]:
    """
    在截图中搜索模板，返回 (最大分数, 匹配中心坐标)。
    """
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    th, tw = template.shape[:2]
    cx = max_loc[0] + tw // 2
    cy = max_loc[1] + th // 2
    return (max_val, (cx, cy))


def find_all_matches(screen: np.ndarray, template: np.ndarray,
                     threshold: float = 0.8, min_distance: int = 30
                     ) -> list[tuple[int, int]]:
    """
    在截图中搜索所有匹配位置。
    返回所有匹配的中心坐标列表。
    """
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)
    
    th, tw = template.shape[:2]
    points = []
    
    for pt in zip(*locations[::-1]):  # (x, y)
        cx = pt[0] + tw // 2
        cy = pt[1] + th // 2
        
        # 去重：检查是否与已有点太近
        too_close = False
        for px, py in points:
            if abs(cx - px) < min_distance and abs(cy - py) < min_distance:
                too_close = True
                break
        if not too_close:
            points.append((cx, cy))
    
    return points
