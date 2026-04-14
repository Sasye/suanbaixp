"""
策略模块：期望值计算、自适应翻牌策略。
"""

import logging
from itertools import combinations

from config import ARROW_TO_LINE, REWARD_TABLE, ALL_NUMBERS

logger = logging.getLogger(__name__)


def calculate_line_ev(line: list[int], revealed: dict[int, int]) -> float:
    """
    计算某条线的期望奖励值。
    
    参数:
        line: 线上的3个格子索引 [pos1, pos2, pos3]
        revealed: 所有已翻开的卡牌 {position: number}
    
    返回:
        该线的期望奖励（星砂数量）
    """
    known_sum = 0
    unknown_count = 0
    
    for pos in line:
        if pos in revealed:
            known_sum += revealed[pos]
        else:
            unknown_count += 1
    
    used_numbers = set(revealed.values())
    remaining = [n for n in ALL_NUMBERS if n not in used_numbers]
    
    if unknown_count == 0:
        return float(REWARD_TABLE.get(known_sum, 0))
    
    total_reward = 0.0
    count = 0
    
    for combo in combinations(remaining, unknown_count):
        total = known_sum + sum(combo)
        reward = REWARD_TABLE.get(total, 0)
        total_reward += reward
        count += 1
    
    if count == 0:
        return 0.0
    
    return total_reward / count


def choose_best_arrow(revealed: dict[int, int]) -> tuple[int, float]:
    """
    选择期望值最高的箭头（线）。
    
    返回:
        (最佳箭头索引, 期望值)
    """
    best_arrow = -1
    best_ev = -1.0
    
    all_evs = {}
    for arrow_idx, line in ARROW_TO_LINE.items():
        ev = calculate_line_ev(line, revealed)
        all_evs[arrow_idx] = ev
        if ev > best_ev:
            best_ev = ev
            best_arrow = arrow_idx
    
    logger.info('各线期望值:')
    for arrow_idx in sorted(all_evs.keys()):
        line = ARROW_TO_LINE[arrow_idx]
        line_nums = [str(revealed.get(p, '?')) for p in line]
        ev = all_evs[arrow_idx]
        marker = ' ★' if arrow_idx == best_arrow else ''
        logger.info(f'  l{arrow_idx} [{",".join(line_nums)}] EV={ev:.1f}{marker}')
    
    return best_arrow, best_ev


def choose_next_flip(revealed: dict[int, int]) -> int:
    """
    自适应选择下一张要翻的牌。
    
    对每个未翻开的格子，模拟所有可能的数字，
    计算翻开后的最佳线期望值的平均值。
    选择平均期望值最高的格子。
    """
    known_digits = set(revealed.values())
    unknown_digits = [d for d in ALL_NUMBERS if d not in known_digits]
    unknown_positions = [p for p in range(9) if p not in revealed]
    
    if not unknown_positions:
        return -1
    
    best_pos = unknown_positions[0]
    best_avg_ev = -1.0
    
    for candidate_pos in unknown_positions:
        total_ev = 0.0
        
        for digit in unknown_digits:
            # 模拟翻开这个格子为这个数字
            simulated = dict(revealed)
            simulated[candidate_pos] = digit
            
            # 计算模拟后的最佳线 EV
            max_ev = 0.0
            for line in ARROW_TO_LINE.values():
                ev = calculate_line_ev(line, simulated)
                if ev > max_ev:
                    max_ev = ev
            total_ev += max_ev
        
        avg_ev = total_ev / len(unknown_digits)
        
        if avg_ev > best_avg_ev:
            best_avg_ev = avg_ev
            best_pos = candidate_pos
    
    logger.info(f'自适应翻牌: 选择格子 {best_pos} (预期最佳EV={best_avg_ev:.1f})')
    return best_pos
