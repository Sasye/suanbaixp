"""
策略模块单元测试。
"""

from strategy import calculate_line_ev, choose_best_arrow, choose_next_flip
from config import ARROW_TO_LINE, REWARD_TABLE


def test_line_ev_known():
    """全部已知的线。"""
    # 行和为 6 → 500
    revealed = {0: 1, 1: 2, 2: 3}
    ev = calculate_line_ev([0, 1, 2], revealed)
    assert ev == 500.0, f'期望 500, 得到 {ev}'
    print(f'✓ 和=6 → EV={ev}')
    
    # 行和为 15 → 10
    revealed = {0: 4, 1: 5, 2: 6}
    ev = calculate_line_ev([0, 1, 2], revealed)
    assert ev == 10.0, f'期望 10, 得到 {ev}'
    print(f'✓ 和=15 → EV={ev}')


def test_line_ev_partial():
    """部分已知。"""
    revealed = {0: 1, 1: 2}
    ev = calculate_line_ev([0, 1, 2], revealed)
    print(f'✓ 已知[1,2,?] → EV={ev:.1f}')
    assert ev > 0


def test_all_lines_equal_no_info():
    """无任何信息时所有线 EV 应相等。"""
    revealed = {}
    evs = set()
    for arrow_idx, line in ARROW_TO_LINE.items():
        ev = calculate_line_ev(line, revealed)
        evs.add(round(ev, 2))
    assert len(evs) == 1, f'期望全部相等, 得到 {evs}'
    print(f'✓ 无信息时所有线 EV={evs.pop():.1f}')


def test_choose_best_arrow():
    """已知4张牌时选择最佳线。"""
    revealed = {0: 1, 3: 2, 4: 3, 6: 1}
    # l0 [6,4,2] → 格子6=1, 格子4=3 → 1+3+? 
    best_arrow, best_ev = choose_best_arrow(revealed)
    print(f'✓ choose_best_arrow → l{best_arrow}, EV={best_ev:.1f}')


def test_choose_next_flip():
    """自适应翻牌测试。"""
    # 只知道1张牌
    revealed = {4: 5}
    next_pos = choose_next_flip(revealed)
    assert next_pos not in revealed, f'不应翻已知格子 {next_pos}'
    print(f'✓ 已知 pos=4(5) → 选择翻 pos={next_pos}')
    
    # 知道2张牌
    revealed = {4: 5, 0: 1}
    next_pos = choose_next_flip(revealed)
    assert next_pos not in revealed
    print(f'✓ 已知 pos=4(5),0(1) → 选择翻 pos={next_pos}')
    
    # 知道3张牌
    revealed = {4: 5, 0: 1, 8: 9}
    next_pos = choose_next_flip(revealed)
    assert next_pos not in revealed
    print(f'✓ 已知 pos=4(5),0(1),8(9) → 选择翻 pos={next_pos}')


def test_no_crash_all_revealed():
    """所有牌都翻开时不应崩溃。"""
    revealed = {0:1, 1:2, 2:3, 3:4, 4:5, 5:6, 6:7, 7:8, 8:9}
    best_arrow, best_ev = choose_best_arrow(revealed)
    print(f'✓ 全部翻开 → l{best_arrow}, EV={best_ev:.1f}')


if __name__ == '__main__':
    print('=' * 50)
    test_line_ev_known()
    print()
    test_line_ev_partial()
    print()
    test_all_lines_equal_no_info()
    print()
    test_choose_best_arrow()
    print()
    test_choose_next_flip()
    print()
    test_no_crash_all_revealed()
    print()
    print('=' * 50)
    print('所有测试通过! ✓')
    print('=' * 50)
