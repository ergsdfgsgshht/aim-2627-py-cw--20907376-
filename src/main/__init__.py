# aim-py-cw
# -*- coding: utf-8 -*-
"""AIM 2627 Python Coursework —— 哨兵 Sentry 控制模块（学生骨架）。

你的全部作业都在本文件里：按题面（题面.pdf）各题的规范补全每个标有 TODO 的函数。
- 骨架已提供：Facing / SentryState 枚举、SentryGrid 的构造与只读属性、
  渲染函数 render_frame（demo 用，不进测试）。
- 你要实现：Q1-Q6 与 Bonus 的全部 TODO，以及 SentryGrid 的
  四个方法（current_pos 的 setter、move_forward、turn_left、turn_right）。
- 未实现的函数 raise NotImplementedError：可见测试会自动 skip，
  CI 一开始就是绿的；实现一个，对应测试亮一个。
- `python main.py`（或 PYTHONPATH=src python -m main）可看 ASCII 演示。
"""
import json
from enum import Enum
from decimal import Decimal


# ---------------------------------------------------------------------------
# 仿真世界基础（已提供，勿改）
# ---------------------------------------------------------------------------
class Facing(Enum):
    """朝向枚举。世界坐标 (x, y)：x 向右增长，y 向上增长（数学系）。"""

    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def delta(self):
        """该朝向的单位位移向量 (dx, dy)。"""
        return self.value[0], self.value[1]


# ---------------------------------------------------------------------------
# Q1 机器人自检（题面 Q1·自检状态计算与报告生成）
# ---------------------------------------------------------------------------
def hp_ratio(hp, max_hp):
    """TODO(Q1)：血量百分比，返回 0-100 的 int；计算与边界规则见题面 Q1 规范。"""
    hp = Decimal(hp)
    max_hp = Decimal(max_hp)
    return int((hp/max_hp)*100)
    raise NotImplementedError("Q1 hp_ratio：题面 Q1·血量百分比与精度保障")


def status_report(name, robot_type, hp, max_hp, battery):
    """TODO(Q1)：一行自检报告字符串；档位判定与逐字符格式见题面 Q1 规范。"""
    percentage = hp_ratio(hp, max_hp)
    if percentage < 0 or percentage > 100:
        result = "error"
        return result
    if battery > 40:
        level = "OK"
    elif battery >= 20:
        level = "WARNING"
    else:
        level = "LOW"
    result = f"{name:<10}|{robot_type:^10}|HP {percentage:>3}%|BAT {battery:>3}%|{level}"
    return result
    raise NotImplementedError("Q1 status_report：题面 Q1·电量映射与报告格式")


# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------
_SENSOR_TO_ARMOR = {"F": "front", "L": "left", "R": "right"}


def _parse_sensor_line(line):
    """解析传感器行 "F:32,L:5,R:12"，返回 [(armor, damage), ...]。

    每段必须形如 "字母:正整数"（F/L/R 对应 front/left/right，段允许缺失）；
    任一段非法则整行按脏行处理，返回 None。
    """
    hits = []
    for seg in line.split(","):
        letter, sep, value = seg.partition(":")
        if sep != ":" or letter not in _SENSOR_TO_ARMOR:
            return None
        if not (value.isascii() and value.isdigit()):
            return None
        damage = int(value)
        if damage <= 0:
            return None
        hits.append((_SENSOR_TO_ARMOR[letter], damage))
    return hits


def analyze_damage_log(lines):
    """解析混合格式伤害日志，返回固定契约的统计 dict（题面 Q2 规范）。

    有效行两种：
    - 传感器行 "F:32,L:5,R:12"：一行记一个事件；
    - JSON 行 '{"armor": ..., "damage": ..., "id": ...}'：armor 须为
      front/left/right 之一，damage 须为严格正整数（排除 bool/float），
      id 可选；带 id 的行按 id 去重，同一 id 只计第一次出现。

    其余输入（空行、# 注释、缺字段、字段非法、任何无法解析的行）
    一律跳过且不计入任何统计；解析全程不得抛出异常。

    输出口径：total 为有效事件伤害总和；by_armor 三键恒存在；
    most_hit 为伤害最大的部位（并列时按 front/left/right 顺序取先者），
    无有效事件时为 None；avg = round(total/有效事件数, 2)，空日志为 0.0。
    """
    by_armor = {"front": 0, "left": 0, "right": 0}
    total = 0
    events = 0
    seen_ids = set()

    for raw in lines:
        if not isinstance(raw, str):
            continue
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        hits = _parse_sensor_line(line)
        if hits is not None:
            for armor, damage in hits:
                by_armor[armor] += damage
                total += damage
            events += 1
            continue

        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        armor = obj.get("armor")
        damage = obj.get("damage")
        if not isinstance(armor, str) or armor not in by_armor:
            continue
        ok_damage = (isinstance(damage, int)
                     and not isinstance(damage, bool)
                     and damage > 0)
        if not ok_damage:
            continue

        event_id = obj.get("id")
        if event_id is not None:
            try:
                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)
            except TypeError:
                pass  # id 不可哈希，视作无 id 独立计数

        by_armor[armor] += damage
        total += damage
        events += 1

    return {
        "total": total,
        "by_armor": by_armor,
        "most_hit": max(by_armor, key=by_armor.get) if events else None,
        "avg": round(total / events, 2) if events else 0.0,
    }


# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------
class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""

    def __init__(self, width, height, obstacles, enemy_pos,
                 start_pos=(0, 0), facing=Facing.UP, fuel=100):
        self._width = int(width)
        self._height = int(height)
        if self._width <= 0 or self._height <= 0:
            raise ValueError("地图尺寸必须为正")
        # 障碍坐标存入 set，查询 O(1)——已有实现，勿改。
        self._obstacles = set()
        for ob in obstacles:
            x, y = ob
            self._obstacles.add((int(x), int(y)))
        if not isinstance(enemy_pos, (tuple, list)) or len(enemy_pos) != 2:
            raise TypeError("enemy_pos 需要长度为 2 的 tuple/list")
        self._enemy_pos = self._clamp_cell(enemy_pos)
        if self._enemy_pos in self._obstacles:
            raise ValueError("enemy_pos 不能位于障碍物上")
        if not isinstance(facing, Facing):
            facing = Facing.UP
        self._facing = facing
        self._fuel = int(fuel)
        self._collision_count = 0
        self._pos = self._clamp_cell(start_pos)
        if self._pos in self._obstacles:
            raise ValueError("start_pos 不能位于障碍物上")

    def _clamp_cell(self, cell):
        """已提供：元素转 int 并夹回地图范围（供 __init__ 使用）。"""
        x = int(cell[0])
        y = int(cell[1])
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    # -- 只读属性（已提供，勿改） ------------------------------------------
    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def enemy_pos(self):
        return self._enemy_pos

    @property
    def facing(self):
        return self._facing

    @property
    def fuel(self):
        return self._fuel

    @property
    def collision_count(self):
        return self._collision_count

    @property
    def obstacles(self):
        """障碍集合的只读视图（内部 set 引用，不要修改它）。"""
        return self._obstacles

    @property
    def found_enemy(self):
        return self._pos == self._enemy_pos

    def is_blocked(self, x, y):
        """已提供：坐标是否为障碍或越界（O(1)）。"""
        return ((x, y) in self._obstacles
                or not (0 <= x < self._width and 0 <= y < self._height))

    # -- 你要实现的部分 ------------------------------------------------------
    @property
    def current_pos(self):
        """当前位置 (x, y) 的 tuple。"""
        return self._pos

    @current_pos.setter
    def current_pos(self, value):
        """TODO(Q3)：位置 setter；三重输入校验见题面 Q3 规范第 1 条。"""
        if len(value) == 2:
            self._pos = value
            return tuple(self._pos)
        else:
            raise TypeError
        raise NotImplementedError("Q3 current_pos.setter：题面 Q3·位置校验三步")

    def move_forward(self):
        """TODO(Q3)：朝当前 facing 前进一格，返回执行后的位置；
        碰撞、耗电与断电语义见题面 Q3 规范。"""
        if self._fuel <= 0:
            return self._pos
        dx, dy = self._facing.delta
        next_pos = (self._pos[0] + dx, self._pos[1] + dy)
        if self.is_blocked(*next_pos):
            self._collision_count += 1
            return self._pos
        self._pos = next_pos
        self._fuel -= 1
        return self._pos
        raise NotImplementedError("Q3 move_forward：题面 Q3·前进、碰撞与断电")

    def turn_left(self):
        """TODO(Q3)：原地左转 90°，返回新的 Facing（不耗电）。"""
        if self._facing == Facing.UP:
            self._facing = Facing.LEFT
            return self._facing
        elif self._facing == Facing.LEFT:
            self._facing = Facing.DOWN
            return self._facing
        elif self._facing == Facing.DOWN:
            self._facing = Facing.RIGHT
            return self._facing
        elif self._facing == Facing.RIGHT:
            self._facing = Facing.UP
            return self._facing
        else:
            raise TypeError
        raise NotImplementedError("Q3 turn_left")

    def turn_right(self):
        """TODO(Q3)：原地右转 90°，返回新的 Facing（不耗电）。"""
        if self._facing == Facing.UP:
            self._facing = Facing.RIGHT
            return self._facing
        elif self._facing == Facing.LEFT:
            self._facing = Facing.UP
            return self._facing
        elif self._facing == Facing.RIGHT:
            self._facing = Facing.DOWN
            return self._facing
        elif self._facing == Facing.DOWN:
            self._facing = Facing.LEFT
            return self._facing
        else:
            raise TypeError
        raise NotImplementedError("Q3 turn_right")


# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
def tpadd(tp1, tp2):
    """坐标加法：两个 (x, y) 逐轴相加，返回新 tuple。"""
    return (tp1[0] + tp2[0], tp1[1] + tp2[1])


def distance(pos1, pos2):
    """两点间的曼哈顿距离（|dx| + |dy|）。"""
    return abs(pos2[0] - pos1[0]) + abs(pos2[1] - pos1[1])


def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """返回下一步应朝向的 Facing（题面 Q4 规范）。

    用 Facing.delta 把每个候选方向换算成候选格，跳过障碍格；
    取到目标曼哈顿距离最小的候选方向，并列时按 Facing 定义顺序
    （UP/DOWN/LEFT/RIGHT）先到先得；没有任何候选能严格缩短
    距离时，回退返回 current_facing。
    """
    origin = distance(pos, target)
    candidates = []
    for direction in Facing:
        nxt = tpadd(pos, direction.delta)
        if nxt in obstacles:
            continue
        candidates.append((distance(nxt, target), direction))

    best_dist, best_dir = min(candidates, key=lambda c: c[0],
                              default=(origin, current_facing))
    return best_dir if best_dist < origin else current_facing


# ---------------------------------------------------------------------------
# Q5 哨兵决策机（题面 Q5·裁判系统决策规则表）
# ---------------------------------------------------------------------------
class SentryState(Enum):
    """哨兵状态机（已提供，勿改）。"""

    PATROL = "PATROL"
    SUSPECT = "SUSPECT"
    ENGAGE = "ENGAGE"
    RETREAT = "RETREAT"
    RETURN = "RETURN"


def decide(sensor, state, hp, heat):
    """纯函数决策：按题面 Q5 规范 R1-R7 顺序求值，首条命中即返回；
    契约外输入（缺字段 / 帧历史长度非法 / state 非枚举）raise ValueError，
    字段存在但取值非法的按防御式归一，不抛异常。"""
    for key in ("enemy_frames", "enemy_dist", "robot_type", "max_hp"):
        if key not in sensor:
            raise ValueError("sensor 缺少字段 " + key)
    frames = sensor["enemy_frames"]
    if (not isinstance(frames, (tuple, list))
            or not 1 <= len(frames) <= 6):
        raise ValueError("enemy_frames 须为长度 1-6 的 tuple/list")
    if not isinstance(state, SentryState):
        raise ValueError("state 必须是 SentryState 成员")

    frames = tuple(bool(f) for f in frames)   # 元素按真值解释，末位=当前帧
    dist = sensor["enemy_dist"]
    if isinstance(dist, bool) or not isinstance(dist, int):
        dist = None                           # 非法敌距按“未知”归一
    is_hero = sensor["robot_type"] == "HERO"  # 非 HERO（含非法值）按步兵侧
    max_hp = sensor["max_hp"]
    if isinstance(max_hp, bool) or not isinstance(max_hp, int) or max_hp <= 0:
        max_hp = 100
    hp_pct = max(0, min(100, hp * 100 // max_hp))
    visible = frames[-1]

    """R1"""
    if hp_pct <= 30:
        return ("RETREAT", SentryState.RETREAT)

    """R2"""
    if state is SentryState.RETREAT:
        if hp_pct > 30:
            return ("RETURN", SentryState.RETURN)
        return ("RETREAT", SentryState.RETREAT)

    """R3"""
    if state is SentryState.RETURN:
        return ("MOVE_BASE", SentryState.PATROL)

    """R4/R5"""
    if state is SentryState.ENGAGE:
        if visible:
            if dist is not None and dist <= 3:
                return ("SHOOT", SentryState.ENGAGE)
            if is_hero:
                return ("MOVE_RIGHT", SentryState.ENGAGE)
            return ("MOVE_LEFT", SentryState.ENGAGE)
        if any(frames[:-1]):                  # 短暂丢失：历史帧还见过
            return ("HOLD_FIRE", SentryState.ENGAGE)
        return ("SCAN", SentryState.SUSPECT)  # 持续丢失：整窗皆 False

    """R6/R7"""
    if visible:
        if len(frames) >= 2 and frames[-2]:   # 末两位均为真（末位已真）
            if dist is not None and dist <= 3:
                return ("SHOOT", SentryState.ENGAGE)
            if is_hero:
                return ("MOVE_RIGHT", SentryState.ENGAGE)
            return ("MOVE_LEFT", SentryState.ENGAGE)
        return ("SCAN", SentryState.SUSPECT)
    if state is SentryState.PATROL:
        return ("PATROL_MOVE", SentryState.PATROL)
    return ("SCAN", SentryState.SUSPECT)


# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
def run_patrol(grid, max_steps=500):
    """TODO(Q6)：sense → decide → act 主循环；
    循环结构、终止条件、脱困自由度与统计返回契约见题面 Q6 规范。"""
    raise NotImplementedError("Q6 run_patrol：题面 Q6·主循环与统计契约")


def report_to_json(stats):
    """TODO(Q6)：把 stats 序列化为确定性的 JSON 字符串，见题面 Q6 规范。"""
    raise NotImplementedError("Q6 report_to_json：题面 Q6·报告序列化")


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------
def bfs_path_length(start, target, obstacles):
    """TODO(Bonus)：BFS 全局最短路步数；返回语义与边界职责见题面 Bonus 规范。"""
    raise NotImplementedError("Bonus bfs_path_length")


# ---------------------------------------------------------------------------
# 渲染（已提供，demo 专用，不进测试）
# ---------------------------------------------------------------------------
def render_frame(grid, trail=()):
    """ASCII 渲染一帧战场；trail 为走过的格子集合。返回 list[str]。"""
    trail = set(trail)
    rows = []
    for y in range(grid.height - 1, -1, -1):
        row = []
        for x in range(grid.width):
            if (x, y) == grid.current_pos:
                row.append("◉")
            elif (x, y) == grid.enemy_pos:
                row.append("▲")
            elif (x, y) in grid.obstacles:
                row.append("█")
            elif (x, y) in trail:
                row.append("·")
            else:
                row.append(".")
        rows.append("".join(row))
    return rows
