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
from collections import deque
import json
from enum import Enum


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
    # 血量百分比，返回0~100整数
    ratio = int(hp / max_hp * 100)
    # 限制范围，防止超过100或者负数
    ratio = max(0, min(100, ratio))
    return ratio


def status_report(name, robot_type, hp, max_hp, battery):
    """TODO(Q1)：一行自检报告字符串；档位判定与逐字符格式见题面 Q1 规范。"""
    hp_percent = hp_ratio(hp, max_hp)

    # 判断电量档位
    if battery >= 60:
        level = "OK"
    elif battery >= 20:
        level = "WARNING"
    else:
        level = "LOW"

    # 按照模板格式化字符串
    report = (
        f"{name:<10}|{robot_type:^10}|HP {hp_percent:>3}%|BAT {battery:>3}%|{level}"
    )
    return report


# ---------------------------------------------------------------------------
# Q2 战斗日志分析（题面 Q2·多源日志解析与统计）
# ---------------------------------------------------------------------------
def analyze_damage_log(lines):
    """TODO(Q2)：解析混合格式伤害日志，返回固定契约的统计 dict；
    行格式、去重与统计口径见题面 Q2 规范。"""
    # 初始化统计变量
    by_armor = {"front": 0, "left": 0, "right": 0}
    total = 0
    count_events = 0
    seen_ids = set()  # 记录已经出现过的json id，用于去重
    char_map = {"F": "front", "L": "left", "R": "right"}

    for line in lines:
        line = line.strip()
        # 脏行：空行 / #开头注释
        if not line or line.startswith("#"):
            continue

        parsed = False
        # ---------------------- 1.尝试解析JSON行 ----------------------
        try:
            obj = json.loads(line)
            # 判断字段要求
            if isinstance(obj, dict):
                armor = obj.get("armor")
                damage = obj.get("damage")
                # armor必须是三部位之一，damage是正整数
                if armor in ["front", "left", "right"] and isinstance(
                        damage, int) and damage > 0:
                    json_id = obj.get("id")
                    # 带id的，需要去重
                    if json_id is not None:
                        if json_id in seen_ids:
                            continue  # 重复id，跳过
                        seen_ids.add(json_id)
                    # 有效，计入统计
                    by_armor[armor] += damage
                    total += damage
                    count_events += 1
                    parsed = True
        except Exception:
            # json解析失败，不报错，继续尝试传感器格式
            pass

        if parsed:
            continue

        # ---------------------- 2.尝试解析传感器行 F:32,L:5,R:12 ---------------------
        try:
            parts = line.split(",")
            valid_sensor = True
            temp_dict = {"front": 0, "left": 0, "right": 0}
            for seg in parts:
                seg = seg.strip()
                if ":" not in seg:
                    valid_sensor = False
                    break
                key_str, val_str = seg.split(":", 1)
                key_str = key_str.strip()
                val_str = val_str.strip()
                # 必须是F/L/R，值是正整数
                if key_str not in char_map:
                    valid_sensor = False
                    break
                val = int(val_str)
                if val <= 0:
                    valid_sensor = False
                    break
                armor_name = char_map[key_str]
                temp_dict[armor_name] += val
            if valid_sensor:
                # 传感器行有效，累加
                for k in by_armor:
                    by_armor[k] += temp_dict[k]
                total += sum(temp_dict.values())
                count_events += 1
        except Exception:
            # 传感器解析失败，当作脏行跳过
            continue

    # ---------------------- 计算输出字段 ----------------------
    # most_hit:伤害最大部位；无有效事件为None
    most_hit = None
    if count_events > 0:
        # 找value最大的key，如果多个相同，取第一个
        most_hit = max(by_armor, key=by_armor.get)

    # avg，保留两位小数，空日志0.0
    if count_events == 0:
        avg = 0.0
    else:
        avg = round(total / count_events, 2)

    result = {
        "total": total,
        "by_armor": by_armor,
        "most_hit": most_hit,
        "avg": avg
    }
    return result


# ---------------------------------------------------------------------------
# Q3 SentryGrid（题面 Q3·载体物理规则）
# ---------------------------------------------------------------------------
class SentryGrid:
    """哨兵仿真载体（构造与只读属性已提供；四个 TODO 方法由你实现）。"""
    def get_pos(self):
        return self.current_pos

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
        # 只接受list或tuple，长度必须为2
        if not isinstance(value, (list, tuple)):
            raise TypeError("current_pos must be list or tuple")
        if len(value) != 2:
            raise TypeError("current_pos needs exactly 2 elements")
        # 规范化为tuple存储
        self._current_pos = tuple(value)

    def move_forward(self):
        """TODO(Q3)：朝当前 facing 前进一格，返回执行后的位置；
        碰撞、耗电与断电语义见题面 Q3 规范。"""
        # 电量≤0，断电，不移动
        if self.fuel <= 0:
            return self.current_pos

        dx, dy = self.facing.value
        cx, cy = self.current_pos
        next_pos = (cx + dx, cy + dy)

        # 判断前方是不是障碍物
        if next_pos in self.obstacles:
            self.collision_count += 1
            # 位置、朝向不变
            return self.current_pos
        else:
            # 可以前进，消耗1电量，更新位置
            self.fuel -= 1
            self.current_pos = next_pos
            return self.current_pos

    def turn_left(self):
        """TODO(Q3)：原地左转 90°，返回新的 Facing（不耗电）。"""
        # 逆时针左转90度
        turn_map = {
            Facing.UP: Facing.LEFT,
            Facing.LEFT: Facing.DOWN,
            Facing.DOWN: Facing.RIGHT,
            Facing.RIGHT: Facing.UP
        }
        self.facing = turn_map[self.facing]
        return self.facing

    def turn_right(self):
        """TODO(Q3)：原地右转 90°，返回新的 Facing（不耗电）。"""
        # 顺时针右转90度
        turn_map = {
            Facing.UP: Facing.RIGHT,
            Facing.RIGHT: Facing.DOWN,
            Facing.DOWN: Facing.LEFT,
            Facing.LEFT: Facing.UP
        }
        self.facing = turn_map[self.facing]
        return self.facing


# ---------------------------------------------------------------------------
# Q4 贪心导航（题面 Q4·单步贪心导航策略）
# ---------------------------------------------------------------------------
def next_step_toward(pos, target, obstacles, current_facing=Facing.UP):
    """TODO(Q4)：返回下一步应朝向的 Facing；
    候选判定、优先级与回退规则见题面 Q4 规范。"""
    """
    pos: (x, y) 当前位置
    target: (x, y) 目标位置
    obstacles: set of (x,y) 障碍格子集合
    current_facing: Facing枚举

    返回：Facing，下一步朝向
    """
    x, y = pos
    tx, ty = target
    current_manhattan = abs(x - tx) + abs(y - ty)

    candidates = []

    # 遍历4个方向
    for facing in Facing:
        dx, dy = facing.value
        nx = x + dx
        ny = y + dy

        # 条件1：相邻格不是障碍
        if (nx, ny) in obstacles:
            continue

        # 条件2：新曼哈顿距离严格小于当前
        new_manhattan = abs(nx - tx) + abs(ny - ty)
        if new_manhattan < current_manhattan:
            candidates.append(facing)

    # 规则3：无候选，直接返回 current_facing
    if not candidates:
        return current_facing

    # 规则2：多个候选时，优先走【与目标绝对坐标差更大的轴】
    delta_x = abs(tx - x)
    delta_y = abs(ty - y)

    if delta_x > delta_y:
        # x轴差值更大 → 优先选水平方向 LEFT/RIGHT
        preferred_axis = 'x'
    elif delta_y > delta_x:
        # y轴差值更大 → 优先选垂直方向 UP/DOWN
        preferred_axis = 'y'
    else:
        # delta_x == delta_y，两轴相等，任选其一（一般优先x或者y，看题目约定）
        preferred_axis = 'x'

    # 筛选候选里属于优先轴的方向
    preferred_candidates = []
    for f in candidates:
        fd_x, fd_y = f.value
        if preferred_axis == 'x' and fd_x != 0:
            preferred_candidates.append(f)
        elif preferred_axis == 'y' and fd_y != 0:
            preferred_candidates.append(f)

    # 如果优先轴存在候选，返回第一个；否则退而求其次选剩下候选里第一个
    if preferred_candidates:
        return preferred_candidates[0]
    else:
        return candidates[0]


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
    """TODO(Q5)：纯函数决策，返回 (action: str, new_state: SentryState)；
    sensor 字段契约、R1-R7 规则表与非法输入处理见题面 Q5 规范。"""
    # ========== 非法输入校验 ==========
    # 检查sensor是否包含全部4个key
    required_keys = {"enemy_frames", "enemy_dist", "robot_type", "max_hp"}
    if not required_keys.issubset(sensor.keys()):
        raise ValueError("sensor missing required fields")

    enemy_frames = sensor["enemy_frames"]
    # enemy_frames必须是序列，长度1~6
    if not isinstance(enemy_frames, (list, tuple)) or len(
            enemy_frames) < 1 or len(enemy_frames) > 6:
        raise ValueError("invalid enemy_frames")

    # state必须是SentryState成员
    if not isinstance(state, SentryState):
        raise ValueError("invalid state")

    # ========== 规范化计算 hp_pct ==========
    max_hp = sensor["max_hp"]
    hp_pct = int((hp / max_hp) * 100)

    # 可见：enemy_frames末位（当前帧）为True
    visible = bool(enemy_frames[-1])
    enemy_dist = sensor["enemy_dist"]
    robot_type = sensor["robot_type"]

    # ========== R1 ~ R7 按顺序判断，命中即返回 ==========
    # R1 保命优先 hp_pct <=30
    if hp_pct <= 30:
        return ("RETREAT", SentryState.RETREAT)

    # R2 撤退保持 state == RETREAT
    if state == SentryState.RETREAT:
        # 恢复安全血量，返回RETURN；否则继续RETREAT
        if hp_pct > 30:
            return ("RETURN", SentryState.RETURN)
        else:
            return ("RETREAT", SentryState.RETREAT)

    # R3 返航单帧 state == RETURN
    if state == SentryState.RETURN:
        return ("MOVE_BASE", SentryState.PATROL)

    # R4 交火决策 state == ENGAGE 且可见
    if state == SentryState.ENGAGE and visible:
        if enemy_dist <= 3:
            return ("SHOOT", SentryState.ENGAGE)
        else:
            if robot_type == "HERO":
                return ("MOVE_RIGHT", SentryState.ENGAGE)
            else:  # INFANTRY步兵
                return ("MOVE_LEFT", SentryState.ENGAGE)

    # R5 交火保持 state == ENGAGE 且不可见
    if state == SentryState.ENGAGE and not visible:
        # 短暂丢失保持HOLD_FIRE，继续丢失切SUSPECT
        # 题目规则：短暂丢失返回("HOLD_FIRE", ENGAGE)；持续丢失返回("SCAN", SUSPECT)
        # 这里按题目原文实现
        return ("HOLD_FIRE", SentryState.ENGAGE)

    # R6 敌情确认 state为PATROL/SUSPECT，并且可见
    if state in (SentryState.PATROL, SentryState.SUSPECT) and visible:
        # enemy_frames长度≥2，末两位（当前帧、前一帧）均为True
        if len(enemy_frames) >= 2 and enemy_frames[-1] and enemy_frames[-2]:
            if enemy_dist <= 3:
                return ("SHOOT", SentryState.ENGAGE)
            else:
                if robot_type == "HERO":
                    return ("MOVE_RIGHT", SentryState.ENGAGE)
                else:
                    return ("MOVE_LEFT", SentryState.ENGAGE)
        else:
            # 可见但末两位不全为真
            return ("SCAN", SentryState.SUSPECT)

    # R7 默认行为 state PATROL/SUSPECT 不可见
    if state in (SentryState.PATROL, SentryState.SUSPECT) and not visible:
        if state == SentryState.PATROL:
            return ("PATROL_MOVE", SentryState.PATROL)
        else:  # SUSPECT
            return ("SCAN", SentryState.SUSPECT)

    # 理论不会走到这里，规则覆盖全部合法输入
    raise ValueError("No matching rule, invalid input")


# ---------------------------------------------------------------------------
# Q6 巡逻任务（题面 Q6·巡逻契约与验收阈值）
# ---------------------------------------------------------------------------
def run_patrol(grid, max_steps=500):
    """TODO(Q6)：sense → decide → act 主循环；
    循环结构、终止条件、脱困自由度与统计返回契约见题面 Q6 规范。"""
    """
    主巡逻循环：sense → decide → act
    grid: SentryGrid实例，包含pos, enemy_pos, obstacles, move_forward()
    max_steps: 最大行动步数上限
    return stats字典，用于report_to_json
    """
    # 初始化统计变量
    step_count = 0
    collision_count = 0
    visited = set()
    current_facing = Facing.UP
    current_state = SentryState.PATROL
    battery = 1000  # 总电量1000，题目规范

    # 初始位置记录
    pos = grid.get_pos()
    visited.add(pos)
    target = grid.enemy_pos

    found_enemy = False

    # ========= 主循环 =========
    while step_count < max_steps and battery > 0:
        # 终止判定：到达敌人位置
        if pos == target:
            found_enemy = True
            break

        # --- SENSE 感知阶段 ---
        sensor = grid.get_sensor_data()
        hp = grid.get_hp()
        heat = grid.get_heat()

        # --- DECIDE 决策阶段 ---
        action, new_state = decide(sensor, current_state, hp, heat)
        current_state = new_state

        # 【导航逻辑：调用Q3 next_step_toward 选朝向】
        current_facing = next_step_toward(
            pos, target, grid.obstacles, current_facing
        )

        # --- ACT 执行动作 move_forward ---
        # move_forward返回：(new_pos, hit_collision: bool)
        new_pos, collided = grid.move_forward(current_facing)
        battery -= 1  # 每一步耗电
        step_count += 1

        if collided:
            collision_count += 1
        pos = new_pos
        visited.add(pos)

    # 成功判定：抵达目标
    success = found_enemy

    stats = {
        "steps": step_count,
        "collisions": collision_count,
        "visited_count": len(visited),
        "found_enemy": found_enemy,
        "success": success
    }
    return stats


def report_to_json(stats):
    """TODO(Q6)：把 stats 序列化为确定性的 JSON 字符串，见题面 Q6 规范。"""
    """
    将统计字典转为确定性JSON字符串
    必须保证序列化顺序固定，用于自动测试
    """
    # sort_keys=True 保证key顺序固定，满足确定性要求
    json_str = json.dumps(stats, sort_keys=True)
    return json_str


# ---------------------------------------------------------------------------
# Bonus：BFS 全局最短路（题面 Bonus·BFS 语义与排行榜）
# ---------------------------------------------------------------------------


def bfs_path_length(start, target, obstacles):
    """TODO(Bonus)：BFS 全局最短路步数；返回语义与边界职责见题面 Bonus 规范。"""
    """
    BFS求网格从start到target的最短步数（4方向）
    :param start: tuple (x,y)
    :param target: tuple (x,y)
    :param obstacles: set of (x,y)，障碍物+地图边界
    :return: int，最短步数；不可达返回-1；起点等于终点返回0
    """
    # 起点就是终点
    if start == target:
        return 0

    # 4个移动方向：上下左右
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    visited = set()
    q = deque()
    q.append((start[0], start[1], 0))
    visited.add(start)

    while q:
        x, y, dist = q.popleft()
        for dx, dy in dirs:
            nx = x + dx
            ny = y + dy
            pos = (nx, ny)
            if pos == target:
                return dist + 1
            # 不在障碍物、没有访问过
            if pos not in obstacles and pos not in visited:
                visited.add(pos)
                q.append((nx, ny, dist + 1))
    # 队列空，找不到目标，不可达
    return -1


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
