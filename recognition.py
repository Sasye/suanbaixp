"""
识别模块：数字卡牌、按钮、箭头的检测。
"""

import logging
import cv2
import numpy as np

from config import (
    MATCH_THRESHOLD_DIGIT, MATCH_THRESHOLD_BUTTON, MATCH_THRESHOLD_ARROW,
)
from capture import load_template, find_template, find_template_score, find_all_matches

logger = logging.getLogger(__name__)


class TemplateManager:
    """管理所有模板图片的加载和缓存。"""
    
    def __init__(self):
        self.digit_templates: dict[int, np.ndarray] = {}
        self.arrow_templates: dict[int, np.ndarray] = {}
        self.arrow_selected_templates: dict[int, np.ndarray] = {}
        self.button_templates: dict[str, np.ndarray] = {}
        self._load_all()
    
    def _load_all(self):
        """加载所有模板。"""
        for i in range(1, 10):
            self.digit_templates[i] = load_template(f'{i}.png')
            logger.info(f'加载数字模板 {i}: {self.digit_templates[i].shape}')
        
        for i in range(8):
            self.arrow_templates[i] = load_template(f'l{i}.png')
            self.arrow_selected_templates[i] = load_template(f'sl{i}.png')
        logger.info('加载箭头模板完成')
        
        for name in ['start', 'confirm', 'left', 'choose']:
            self.button_templates[name] = load_template(f'{name}.png')
        logger.info('加载按钮模板完成')


def find_button(screen: np.ndarray, templates: TemplateManager, 
                button_name: str) -> tuple[int, int] | None:
    """搜索按钮位置，返回按钮中心坐标或 None。"""
    template = templates.button_templates.get(button_name)
    if template is None:
        logger.error(f'未找到按钮模板: {button_name}')
        return None
    
    pos = find_template(screen, template, MATCH_THRESHOLD_BUTTON)
    if pos:
        logger.debug(f'找到按钮 {button_name}: {pos}')
    return pos


def find_arrows(screen: np.ndarray, templates: TemplateManager,
                selected: bool = False) -> dict[int, tuple[int, int]]:
    """
    搜索所有可见箭头，返回 {arrow_index: (cx, cy)}。
    
    策略：
    1. 对角线箭头 (l0, l4) 形状独特，单独搜索
    2. 行箭头 (→) 用 l1/l2/l3 三个模板各搜索所有匹配，合并去重，按 y 排序
    3. 列箭头 (↓) 用 l5/l6/l7 三个模板各搜索所有匹配，合并去重，按 x 排序
    """
    arrow_tmpls = templates.arrow_selected_templates if selected else templates.arrow_templates
    result = {}
    
    # === 对角线箭头：独特形状，单独搜索 ===
    for idx in [0, 4]:
        pos = find_template(screen, arrow_tmpls[idx], MATCH_THRESHOLD_ARROW)
        if pos:
            result[idx] = pos
    
    # === 行箭头 (→): l3(row0), l2(row1), l1(row2) ===
    row_positions = _collect_group_matches(
        screen, [arrow_tmpls[1], arrow_tmpls[2], arrow_tmpls[3]],
        MATCH_THRESHOLD_ARROW, min_distance=40
    )
    if len(row_positions) >= 3:
        row_positions.sort(key=lambda p: p[1])
        result[3] = row_positions[0]
        result[2] = row_positions[1]
        result[1] = row_positions[2]
    elif row_positions:
        logger.warning(f'只找到 {len(row_positions)} 个行箭头(→), 期望3个')
        row_positions.sort(key=lambda p: p[1])
        for i, pos in enumerate(row_positions):
            idx = [3, 2, 1][i]
            result[idx] = pos
    
    # === 列箭头 (↓): l5(col0), l6(col1), l7(col2) ===
    col_positions = _collect_group_matches(
        screen, [arrow_tmpls[5], arrow_tmpls[6], arrow_tmpls[7]],
        MATCH_THRESHOLD_ARROW, min_distance=40
    )
    if len(col_positions) >= 3:
        col_positions.sort(key=lambda p: p[0])
        result[5] = col_positions[0]
        result[6] = col_positions[1]
        result[7] = col_positions[2]
    elif col_positions:
        logger.warning(f'只找到 {len(col_positions)} 个列箭头(↓), 期望3个')
        col_positions.sort(key=lambda p: p[0])
        for i, pos in enumerate(col_positions):
            idx = [5, 6, 7][i]
            result[idx] = pos
    
    if result:
        logger.debug(f'找到 {len(result)} 个箭头: {sorted(result.keys())}')
        for idx in sorted(result.keys()):
            logger.debug(f'  l{idx}: {result[idx]}')
    
    return result


def _collect_group_matches(screen: np.ndarray, group_templates: list[np.ndarray],
                           threshold: float, min_distance: int = 40
                           ) -> list[tuple[int, int]]:
    """用多个模板分别搜索，合并所有匹配位置并去重。"""
    all_points: list[tuple[int, int]] = []
    
    for tmpl in group_templates:
        matches = find_all_matches(screen, tmpl, threshold=threshold,
                                   min_distance=min_distance)
        for pt in matches:
            too_close = False
            for existing in all_points:
                if abs(pt[0] - existing[0]) < min_distance and \
                   abs(pt[1] - existing[1]) < min_distance:
                    too_close = True
                    break
            if not too_close:
                all_points.append(pt)
    
    return all_points


# ==================== 网格坐标 ====================

def compute_grid_from_arrows(arrows: dict[int, tuple[int, int]]
                             ) -> dict[int, tuple[int, int]]:
    """
    从箭头位置直接计算所有 9 个格子的点击坐标。
    行箭头 (l3/l2/l1) 的 y 坐标 ≈ 卡牌行中心 y
    列箭头 (l5/l6/l7) 的 x 坐标 ≈ 卡牌列中心 x
    
    返回 {grid_pos(0-8): (x, y)}
    """
    row_ys = {}
    for arrow_idx, row_idx in [(3, 0), (2, 1), (1, 2)]:
        if arrow_idx in arrows:
            row_ys[row_idx] = arrows[arrow_idx][1]
    
    col_xs = {}
    for arrow_idx, col_idx in [(5, 0), (6, 1), (7, 2)]:
        if arrow_idx in arrows:
            col_xs[col_idx] = arrows[arrow_idx][0]
    
    grid = {}
    
    INWARD_OFFSET = 15  # 边缘格子向中心偏移像素数
    
    for r in range(3):
        for c in range(3):
            if r in row_ys and c in col_xs:
                x = int(col_xs[c])
                y = int(row_ys[r])
                # 只偏移边缘行列，中心行列(1)不动
                if c == 0:
                    x += INWARD_OFFSET
                elif c == 2:
                    x -= INWARD_OFFSET
                if r == 0:
                    y += INWARD_OFFSET
                elif r == 2:
                    y -= INWARD_OFFSET
                grid[r * 3 + c] = (x, y)
    
    if len(grid) == 9:
        logger.info(f'通过箭头计算出全部 9 个格子坐标')
    else:
        logger.warning(f'只计算出 {len(grid)}/9 个格子坐标')
    
    return grid


# ==================== 数字识别 ====================

def scan_cell_digit(screen: np.ndarray, templates: TemplateManager,
                    cell_center: tuple[int, int],
                    cell_half_size: int = 60) -> int | None:
    """
    在指定格子区域内识别数字。
    返回识别到的数字 (1-9) 或 None。
    """
    cx, cy = cell_center
    h, w = screen.shape[:2]
    
    x1 = max(0, cx - cell_half_size)
    y1 = max(0, cy - cell_half_size)
    x2 = min(w, cx + cell_half_size)
    y2 = min(h, cy + cell_half_size)
    
    region = screen[y1:y2, x1:x2]
    if region.size == 0:
        return None
    
    best_digit = None
    best_score = 0.0
    
    for digit, tmpl in templates.digit_templates.items():
        if tmpl.shape[0] > region.shape[0] or tmpl.shape[1] > region.shape[1]:
            continue
        result = cv2.matchTemplate(region, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        if max_val > best_score:
            best_score = max_val
            best_digit = digit
    
    if best_score >= MATCH_THRESHOLD_DIGIT:
        return best_digit
    return None


def scan_all_cells(screen: np.ndarray, templates: TemplateManager,
                   grid_positions: dict[int, tuple[int, int]]
                   ) -> dict[int, int]:
    """
    扫描所有格子，识别已翻开卡牌的数字。
    返回 {grid_pos(0-8): digit(1-9)}。
    """
    revealed = {}
    for pos, center in grid_positions.items():
        digit = scan_cell_digit(screen, templates, center)
        if digit is not None:
            revealed[pos] = digit
            logger.debug(f'格子 {pos}: 数字 {digit}')
    
    return revealed
