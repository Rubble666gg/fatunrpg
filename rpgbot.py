# -------------------- GAME ENGINE --------------------
import datetime
import json
import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from dataclasses import dataclass, asdict
from typing import Optional

current_datetime = datetime.datetime.now()
version = 0.10


# ==================== РАСЫ ====================
class Race:
    """Базовый класс расы"""
    base_health_modifier = 1.0
    base_attack_modifier = 1.0
    base_defence_modifier = 1.0
    race_name = "Раса"
    emoji = "👤"

    def on_damage_taken(self, damage: int) -> tuple[int, str | None]:
        """Обработка получения урона (для расовых способностей)"""
        return damage, None


class Elf(Race):
    race_name = "Эльф"
    emoji = "🧝"
    base_health_modifier = 0.9
    base_attack_modifier = 1.1
    dodge_chance = 0.20

    def on_damage_taken(self, damage: int) -> tuple[int, str | None]:
        if random.random() < self.dodge_chance:
            return 0, "Уклонение!"
        return damage, None


class Human(Race):
    race_name = "Человек"
    emoji = "⚔️"
    base_health_modifier = 1.0
    base_attack_modifier = 1.0
    base_defence_modifier = 1.1


class Troll(Race):
    race_name = "Тролль"
    emoji = "👹"
    base_health_modifier = 1.3
    base_attack_modifier = 0.9


# ==================== КЛАССЫ ====================
class CharacterClass:
    """Базовый класс персонажа"""
    base_health_points = 100
    base_attack_power = 10
    base_defence = 20
    class_name = "Класс"
    emoji = "⚔️"

    crit_chance = 0.10
    crit_multiplier = 2.0

    offensive_skill_name = "Атакующий навык"
    defensive_skill_name = "Защитный навык"


class Warrior(CharacterClass):
    class_name = "Воин"
    emoji = "🛡️"
    base_health_points = 120
    base_attack_power = 12
    base_defence = 30
    crit_chance = 0.15
    crit_multiplier = 1.8

    offensive_skill_name = "Молот грома"
    defensive_skill_name = "Поднять щиты"


class Paladin(CharacterClass):
    class_name = "Паладин"
    emoji = "✨"
    base_health_points = 110
    base_attack_power = 11
    base_defence = 25
    crit_chance = 0.12
    crit_multiplier = 2.0

    offensive_skill_name = "Правосудие света"
    defensive_skill_name = "Божественная защита"


class Mage(CharacterClass):
    class_name = "Маг"
    emoji = "🔮"
    base_health_points = 80
    base_attack_power = 18
    base_defence = 10
    crit_chance = 0.25
    crit_multiplier = 2.5

    offensive_skill_name = "Искажение реальности"
    defensive_skill_name = "Альтертайм"


class Archer(CharacterClass):
    class_name = "Лучник"
    emoji = "🏹"
    base_health_points = 90
    base_attack_power = 14
    base_defence = 15
    crit_chance = 0.35
    crit_multiplier = 2.2

    offensive_skill_name = "Град стрел"
    defensive_skill_name = "Ловкость охотника"


class Warlock(CharacterClass):
    class_name = "Чернокнижник"
    emoji = "🔥"
    base_health_points = 85
    base_attack_power = 16
    base_defence = 12
    crit_chance = 0.20
    crit_multiplier = 2.3

    offensive_skill_name = "Порча"
    defensive_skill_name = "Камень души"


# ==================== ПЕРСОНАЖ ====================
@dataclass
class CharacterState:
    """Состояние персонажа в бою"""
    blocking: bool = False  # Защита активна
    shield_wall_turns: int = 0  # Количество оставшихся ходов "Поднять щиты"
    stunned: bool = False  # Оглушен
    divine_shield_active: bool = False  # Божественная защита активна
    holy_charged: bool = False  # Правосудие света активно
    reality_distortion_active: bool = False  # Искажение реальности активно
    dodge_boost_active: bool = False  # Ловкость охотника активна
    corruption_active: bool = False  # Порча активна
    soulstone_active: bool = False  # Камень души активен

    skill_used: bool = False  # Использован ли специальный навык
    hp_history: list = None  # История HP для Альтертайма

    def __post_init__(self):
        if self.hp_history is None:
            self.hp_history = []


class Character:
    max_level = 5

    def __init__(self, race: Race, char_class: CharacterClass, level: int = 1):
        self.race = race
        self.char_class = char_class
        self.level = level

        # Применяем расовые модификаторы
        self.base_health_points = int(char_class.base_health_points * race.base_health_modifier)
        self.base_attack_power = int(char_class.base_attack_power * race.base_attack_modifier)
        self.base_defence = int(char_class.base_defence * race.base_defence_modifier)

        self.health_points = self.base_health_points * level
        self.max_hp = self.health_points
        self.attack_power = self.base_attack_power * level

        self.crit_chance = char_class.crit_chance
        self.crit_multiplier = char_class.crit_multiplier

        self.state = CharacterState()

    @property
    def character_name(self):
        return f"{self.race.emoji} {self.char_class.emoji}"

    @property
    def full_name(self):
        return f"{self.race.race_name} {self.char_class.class_name}"

    def deal_damage(self) -> tuple[int, bool]:
        is_crit = random.random() < self.crit_chance
        damage = self.attack_power * (self.crit_multiplier if is_crit else 1.0)
        return round(damage), is_crit

    @property
    def defence(self) -> int:
        base_def = self.base_defence * self.level

        # Блок дает +50%
        if self.state.blocking:
            base_def = int(base_def * 1.5)

        # Щиты воина дают +100%
        if self.state.shield_wall_turns > 0:
            base_def = int(base_def * 2)

        return base_def

    @property
    def max_health_points(self) -> int:
        return self.max_hp

    def health_points_percent(self):
        return 100 * self.health_points / self.max_health_points

    def is_alive(self) -> bool:
        return self.health_points > 0

    def is_dead(self) -> bool:
        return self.health_points <= 0

    def level_up(self):
        if self.level < self.max_level:
            self.level += 1
            self.health_points = self.max_health_points

    def __str__(self):
        return f"{self.full_name} (ур.{self.level}, {self.health_points}/{self.max_health_points} HP)"


# ==================== БОЕВАЯ СИСТЕМА ====================
class BattleAction:
    ATTACK = "attack"
    BLOCK = "block"
    SKILL_OFFENSIVE = "skill_off"
    SKILL_DEFENSIVE = "skill_def"


class Battle:
    def __init__(self, char1: Character, char2: Character):
        self.char1 = char1
        self.char2 = char2
        self.current_turn = 1
        self.log = []

        # Случайный выбор первого игрока
        self.current_player = random.choice([1, 2])

        self.log.append(f"=== НАЧАЛО БИТВЫ ===")
        self.log.append(f"{char1.full_name} (ур.{char1.level}) VS {char2.full_name} (ур.{char2.level})")
        self.log.append(f"Первым ходит игрок {self.current_player}")
        self.log.append("")

    def get_current_character(self) -> Character:
        return self.char1 if self.current_player == 1 else self.char2

    def get_opponent(self) -> Character:
        return self.char2 if self.current_player == 1 else self.char1

    def switch_turn(self):
        """Переключение хода"""
        attacker = self.get_current_character()

        # Сброс блока
        attacker.state.blocking = False

        # Уменьшение счетчиков
        if attacker.state.shield_wall_turns > 0:
            attacker.state.shield_wall_turns -= 1

        # Сброс разовых эффектов
        if attacker.state.holy_charged:
            attacker.state.holy_charged = False

        if attacker.state.dodge_boost_active:
            attacker.state.dodge_boost_active = False

        # Переключение игрока
        self.current_player = 2 if self.current_player == 1 else 1

        # Проверка оглушения
        new_attacker = self.get_current_character()
        if new_attacker.state.stunned:
            new_attacker.state.stunned = False
            self.log.append(f"Ход {self.current_turn}: Игрок {self.current_player} оглушен и пропускает ход")
            self.current_turn += 1
            self.switch_turn()
            return

        self.current_turn += 1

    def execute_action(self, action: str) -> str:
        """Выполнение действия и возврат результата"""
        attacker = self.get_current_character()
        defender = self.get_opponent()

        # Сохранение HP в историю для Альтертайма
        attacker.state.hp_history.append(attacker.health_points)
        if len(attacker.state.hp_history) > 3:
            attacker.state.hp_history.pop(0)

        result = []
        result.append(f"--- Ход {self.current_turn}: Игрок {self.current_player} ---")

        if action == BattleAction.ATTACK:
            result.extend(self._execute_attack(attacker, defender))
        elif action == BattleAction.BLOCK:
            result.extend(self._execute_block(attacker))
        elif action == BattleAction.SKILL_OFFENSIVE:
            result.extend(self._execute_offensive_skill(attacker, defender))
        elif action == BattleAction.SKILL_DEFENSIVE:
            result.extend(self._execute_defensive_skill(attacker, defender))

        # Проверка смерти и камня души
        if defender.is_dead() and defender.state.soulstone_active:
            defender.health_points = int(defender.max_health_points * 0.2)
            defender.state.soulstone_active = False
            result.append(f"!!! КАМЕНЬ ДУШИ СРАБОТАЛ! {defender.full_name} воскрес с {defender.health_points} HP")

        result.append("")

        battle_log = "\n".join(result)
        self.log.append(battle_log)

        self.switch_turn()

        return battle_log

    def _execute_attack(self, attacker: Character, defender: Character) -> list[str]:
        result = []
        result.append(f"{attacker.full_name} атакует!")

        raw_damage, is_crit = attacker.deal_damage()

        # Правосудие света - всегда крит, игнорирует броню
        if attacker.state.holy_charged:
            is_crit = True
            final_damage = raw_damage
            attacker.state.holy_charged = False
            result.append(f">>> ПРАВОСУДИЕ СВЕТА! Критический урон, игнорирует броню")
        else:
            # Обычная атака
            final_damage, event = self._apply_damage(defender, raw_damage)
            if event:
                result.append(f">>> {event}")

        # Порча чернокнижника
        if attacker.state.corruption_active:
            corruption_dmg = int(final_damage * 0.3)
            defender.health_points -= corruption_dmg
            attacker.health_points = min(attacker.health_points + corruption_dmg, attacker.max_health_points)
            result.append(
                f">>> ПОРЧА: +{corruption_dmg} урона (игнорирует броню), чернокнижник излечен на {corruption_dmg} HP")

        crit_text = " [КРИТИЧЕСКИЙ УДАР!]" if is_crit else ""
        result.append(f"Урон: {raw_damage}{crit_text} -> {final_damage} (после защиты)")
        result.append(f"{defender.full_name}: {defender.health_points}/{defender.max_health_points} HP")

        return result

    def _execute_block(self, attacker: Character) -> list[str]:
        attacker.state.blocking = True
        return [
            f"{attacker.full_name} встает в блок!",
            f"Защита повышена на 50% до следующего хода"
        ]

    def _execute_offensive_skill(self, attacker: Character, defender: Character) -> list[str]:
        if attacker.state.skill_used:
            return ["Специальный навык уже использован!"]

        attacker.state.skill_used = True
        result = []

        if isinstance(attacker.char_class, Paladin):
            # Правосудие света
            attacker.state.holy_charged = True
            result.append(f">>> {attacker.full_name} использует ПРАВОСУДИЕ СВЕТА!")
            result.append(f"Следующая атака будет критической и проигнорирует броню")

        elif isinstance(attacker.char_class, Mage):
            # Искажение реальности
            attacker.state.reality_distortion_active = True
            result.append(f">>> {attacker.full_name} использует ИСКАЖЕНИЕ РЕАЛЬНОСТИ!")
            result.append(f"Весь входящий урон увеличен на 35%")
            result.append(f"При использовании противником навыка - взрыв!")

        elif isinstance(attacker.char_class, Warrior):
            # Молот грома
            raw_damage = int(attacker.attack_power * 0.5)
            final_damage, _ = self._apply_damage(defender, raw_damage)
            defender.state.stunned = True
            result.append(f">>> {attacker.full_name} использует МОЛОТ ГРОМА!")
            result.append(f"Урон: {final_damage}")
            result.append(f"Противник оглушен на 1 ход!")
            result.append(f"{defender.full_name}: {defender.health_points}/{defender.max_health_points} HP")

        elif isinstance(attacker.char_class, Archer):
            # Град стрел - 3 атаки по 70%
            result.append(f">>> {attacker.full_name} использует ГРАД СТРЕЛ!")
            total_damage = 0
            for i in range(3):
                raw_damage, is_crit = attacker.deal_damage()
                raw_damage = int(raw_damage * 0.7)
                final_damage, event = self._apply_damage(defender, raw_damage)
                total_damage += final_damage
                crit_text = " [КРИТ!]" if is_crit else ""
                result.append(f"Стрела {i + 1}: {final_damage} урона{crit_text}")
                if defender.is_dead() and not defender.state.soulstone_active:
                    break
            result.append(f"Общий урон: {total_damage}")
            result.append(f"{defender.full_name}: {defender.health_points}/{defender.max_health_points} HP")

        elif isinstance(attacker.char_class, Warlock):
            # Порча
            attacker.state.corruption_active = True
            result.append(f">>> {attacker.full_name} использует ПОРЧУ!")
            result.append(f"Все атаки теперь накладывают порчу: +30% урона, игнорирует броню")
            result.append(f"Чернокнижник лечится на размер дополнительного урона")

        return result

    def _execute_defensive_skill(self, attacker: Character, defender: Character) -> list[str]:
        if attacker.state.skill_used:
            return ["Специальный навык уже использован!"]

        attacker.state.skill_used = True
        result = []

        if isinstance(attacker.char_class, Paladin):
            # Божественная защита
            attacker.state.divine_shield_active = True
            result.append(f">>> {attacker.full_name} использует БОЖЕСТВЕННУЮ ЗАЩИТУ!")
            result.append(f"Следующий входящий урон излечит паладина")

        elif isinstance(attacker.char_class, Mage):
            # Альтертайм
            if len(attacker.state.hp_history) >= 2:
                old_hp = attacker.state.hp_history[-2]
                healed = old_hp - attacker.health_points
                attacker.health_points = min(old_hp, attacker.max_health_points)
                result.append(f">>> {attacker.full_name} использует АЛЬТЕРТАЙМ!")
                result.append(f"HP восстановлено до {attacker.health_points} (+{healed} HP)")
            else:
                result.append(f">>> {attacker.full_name} использует АЛЬТЕРТАЙМ!")
                result.append(f"Недостаточно истории для отката")

        elif isinstance(attacker.char_class, Warrior):
            # Поднять щиты
            attacker.state.shield_wall_turns = 2
            result.append(f">>> {attacker.full_name} использует ПОДНЯТЬ ЩИТЫ!")
            result.append(f"Весь входящий урон уменьшен на 60% на следующие 2 хода")

        elif isinstance(attacker.char_class, Archer):
            # Ловкость охотника
            attacker.state.dodge_boost_active = True
            result.append(f">>> {attacker.full_name} использует ЛОВКОСТЬ ОХОТНИКА!")
            result.append(f"Шанс уклонения повышен на 80% на следующий ход")

        elif isinstance(attacker.char_class, Warlock):
            # Камень души
            attacker.state.soulstone_active = True
            result.append(f">>> {attacker.full_name} использует КАМЕНЬ ДУШИ!")
            result.append(f"При получении смертельного урона - воскрешение с 20% HP")

        return result

    def _apply_damage(self, defender: Character, raw_damage: int) -> tuple[int, Optional[str]]:
        """Применение урона с учетом всех эффектов"""
        event = None

        # Искажение реальности - увеличение урона на 35%
        if defender.state.reality_distortion_active:
            raw_damage = int(raw_damage * 1.35)
            event = "Искажение реальности: урон увеличен на 35%"

        # Божественная защита - превращает урон в лечение
        if defender.state.divine_shield_active:
            defender.health_points = min(defender.health_points + raw_damage, defender.max_health_points)
            defender.state.divine_shield_active = False
            return 0, f"БОЖЕСТВЕННАЯ ЗАЩИТА! Урон превращен в {raw_damage} HP лечения"

        # Ловкость охотника - 80% шанс уклонения
        if defender.state.dodge_boost_active and random.random() < 0.8:
            return 0, "ЛОВКОСТЬ ОХОТНИКА! Уклонение!"

        # Расовое уклонение эльфа
        racial_damage, racial_event = defender.race.on_damage_taken(raw_damage)
        if racial_event:
            return 0, racial_event

        # Применение защиты
        final_damage = racial_damage * (100 - defender.defence) / 100
        final_damage = max(1, round(final_damage))  # Минимум 1 урон

        defender.health_points -= final_damage

        return final_damage, event

    def get_battle_status(self) -> str:
        """Текущее состояние боя"""
        lines = []
        lines.append("=== СОСТОЯНИЕ БОЯ ===")
        lines.append(f"Ход: {self.current_turn}")
        lines.append("")

        for i, char in enumerate([self.char1, self.char2], 1):
            lines.append(f"Игрок {i}: {char.full_name}")
            lines.append(f"HP: {char.health_points}/{char.max_health_points}")
            lines.append(f"Защита: {char.defence}")

            effects = []
            if char.state.blocking:
                effects.append("Блок активен")
            if char.state.shield_wall_turns > 0:
                effects.append(f"Щиты ({char.state.shield_wall_turns} хода)")
            if char.state.divine_shield_active:
                effects.append("Божественная защита")
            if char.state.holy_charged:
                effects.append("Правосудие света готово")
            if char.state.reality_distortion_active:
                effects.append("Искажение реальности")
            if char.state.dodge_boost_active:
                effects.append("Ловкость охотника")
            if char.state.corruption_active:
                effects.append("Порча активна")
            if char.state.soulstone_active:
                effects.append("Камень души готов")
            if char.state.stunned:
                effects.append("Оглушен")

            if effects:
                lines.append(f"Эффекты: {', '.join(effects)}")

            if char.state.skill_used:
                lines.append(f"Навык использован: ДА")
            else:
                lines.append(f"Навык доступен: ДА")

            lines.append("")

        return "\n".join(lines)

    def get_winner(self) -> Optional[int]:
        """Возвращает номер победителя или None"""
        if self.char1.is_dead():
            return 2
        elif self.char2.is_dead():
            return 1
        return None

    def get_full_log(self) -> str:
        """Полный лог боя"""
        result = "\n".join(self.log)

        winner = self.get_winner()
        if winner:
            result += f"\n\n=== ПОБЕДИТЕЛЬ: Игрок {winner} ==="
            winner_char = self.char1 if winner == 1 else self.char2
            result += f"\n{winner_char.full_name} побеждает!"

        return result


PLAYERS_FILE = "players.json"
BATTLES_FILE = "active_battles.json"


@dataclass
class PlayerProfile:
    tg_id: int
    username: str | None
    name: str
    race: str
    char_class: str
    level: int = 1
    wins: int = 0
    losses: int = 0


def load_players() -> dict[str, dict]:
    try:
        with open(PLAYERS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        if os.path.exists(PLAYERS_FILE):
            backup_name = f"players_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.rename(PLAYERS_FILE, backup_name)
            print(f"Поврежденный файл сохранен как {backup_name}")
        return {}


def save_players(players: dict[str, dict]) -> None:
    with open(PLAYERS_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)


def get_profile(players: dict[str, dict], tg_id: int) -> PlayerProfile | None:
    data = players.get(str(tg_id))
    if not data:
        return None

    # Миграция со старого формата
    if "char_class" in data and "race" not in data:
        old_class = data["char_class"]
        if old_class == "elf":
            data["race"] = "elf"
            data["char_class"] = "warrior"
        elif old_class == "human":
            data["race"] = "human"
            data["char_class"] = "warrior"
        elif old_class == "troll":
            data["race"] = "troll"
            data["char_class"] = "warrior"
        else:
            data["race"] = "human"
            data["char_class"] = "warrior"

        players[str(tg_id)] = data
        save_players(players)

    return PlayerProfile(**data)


def set_profile(players: dict[str, dict], profile: PlayerProfile) -> None:
    players[str(profile.tg_id)] = asdict(profile)


def find_profile_by_username(players: dict[str, dict], username: str) -> PlayerProfile | None:
    username = username.lstrip("@").lower()
    for data in players.values():
        u = (data.get("username") or "").lower()
        if u == username:
            return PlayerProfile(**data)
    return None


def get_race(race_name: str) -> Race:
    race_name = race_name.lower()
    if race_name == "elf":
        return Elf()
    elif race_name == "human":
        return Human()
    elif race_name == "troll":
        return Troll()
    raise ValueError("Unknown race")


def get_class(class_name: str) -> CharacterClass:
    class_name = class_name.lower()
    if class_name == "warrior":
        return Warrior()
    elif class_name == "paladin":
        return Paladin()
    elif class_name == "mage":
        return Mage()
    elif class_name == "archer":
        return Archer()
    elif class_name == "warlock":
        return Warlock()
    raise ValueError("Unknown class")


def make_character_from_profile(profile: PlayerProfile) -> Character:
    race = get_race(profile.race)
    char_class = get_class(profile.char_class)
    return Character(race, char_class, profile.level)


def stats_to_text(c: Character) -> str:
    hp_bar = "█" * int(c.health_points_percent() / 10) + "░" * (10 - int(c.health_points_percent() / 10))

    lines = []
    lines.append(f"Характеристики")
    lines.append(f"{c.race.race_name} | {c.char_class.class_name}")
    lines.append(f"{'─' * 35}")
    lines.append(f"Уровень: {c.level}/{c.max_level}")
    lines.append(f"HP: {c.health_points}/{c.max_health_points}")
    lines.append(f"   [{hp_bar}] {c.health_points_percent():.1f}%")
    lines.append(f"Атака: {c.attack_power}")
    lines.append(f"Защита: {c.defence}")
    lines.append(f"Шанс крита: {c.crit_chance:.0%}")
    lines.append(f"Множитель крита: x{c.crit_multiplier}")

    # Расовые способности
    if isinstance(c.race, Elf):
        lines.append(f"\nРасовая способность:")
        lines.append(f"   Уклонение: {c.race.dodge_chance:.0%}")
    elif isinstance(c.race, Human):
        lines.append(f"\nРасовая способность:")
        lines.append(f"   Баланс характеристик")
        lines.append(f"   +10% защиты")
    elif isinstance(c.race, Troll):
        lines.append(f"\nРасовая способность:")
        lines.append(f"   +30% HP, -10% атаки")

    # Классовые навыки
    lines.append(f"\nКлассовые навыки:")
    lines.append(f"   Атакующий: {c.char_class.offensive_skill_name}")
    lines.append(f"   Защитный: {c.char_class.defensive_skill_name}")

    return "\n".join(lines)


# Хранилище активных боев
active_battles = {}
user_creation_state = {}


# -------------------- TELEGRAM BOT --------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("Создать персонажа", callback_data="create_menu"),
            InlineKeyboardButton("Мой профиль", callback_data="me")
        ],
        [
            InlineKeyboardButton("PvP битва", callback_data="pvp_menu"),
            InlineKeyboardButton("Тестовый бой", callback_data="fight_menu")
        ],
        [
            InlineKeyboardButton("Информация", callback_data="info_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "ДОБРО ПОЖАЛОВАТЬ В RPG BATTLE BOT!\n\n"
        "Выбери расу и класс персонажа, сражайся с другими игроками "
        "в пошаговых боях и поднимайся в рейтинге!\n\n"
        "Выбери действие:"
    )

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    tg_id = query.from_user.id

    # ========== СОЗДАНИЕ ПЕРСОНАЖА ==========
    if query.data == "create_menu":
        players = load_players()
        existing_profile = get_profile(players, tg_id)

        if existing_profile:
            keyboard = [
                [InlineKeyboardButton("Удалить персонажа", callback_data="delete_confirm")],
                [InlineKeyboardButton("Назад", callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            race = get_race(existing_profile.race)
            char_class = get_class(existing_profile.char_class)

            text = (
                "У ТЕБЯ УЖЕ ЕСТЬ ПЕРСОНАЖ!\n\n"
                f"Имя: {existing_profile.name}\n"
                f"Раса: {race.race_name}\n"
                f"Класс: {char_class.class_name}\n"
                f"Уровень: {existing_profile.level}\n"
                f"Побед: {existing_profile.wins}\n"
                f"Поражений: {existing_profile.losses}\n\n"
                "Чтобы создать нового персонажа, нужно сначала удалить текущего."
            )
            await query.edit_message_text(text, reply_markup=reply_markup)
            return

        keyboard = [
            [InlineKeyboardButton("Эльф", callback_data="race_elf")],
            [InlineKeyboardButton("Человек", callback_data="race_human")],
            [InlineKeyboardButton("Тролль", callback_data="race_troll")],
            [InlineKeyboardButton("Назад", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "СОЗДАНИЕ ПЕРСОНАЖА - Шаг 1/2\n\n"
            "Выбери расу:\n\n"
            "ЭЛЬФ\n"
            "   Уклонение 20%, +10% атаки, -10% HP\n\n"
            "ЧЕЛОВЕК\n"
            "   +10% защиты, сбалансированные характеристики\n\n"
            "ТРОЛЛЬ\n"
            "   +30% HP, -10% атаки"
        )
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif query.data.startswith("race_"):
        race = query.data.replace("race_", "")
        user_creation_state[tg_id] = {"race": race}

        keyboard = [
            [InlineKeyboardButton("Воин", callback_data="class_warrior")],
            [InlineKeyboardButton("Паладин", callback_data="class_paladin")],
            [InlineKeyboardButton("Маг", callback_data="class_mage")],
            [InlineKeyboardButton("Лучник", callback_data="class_archer")],
            [InlineKeyboardButton("Чернокнижник", callback_data="class_warlock")],
            [InlineKeyboardButton("Назад", callback_data="create_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "СОЗДАНИЕ ПЕРСОНАЖА - Шаг 2/2\n\n"
            "Выбери класс:\n\n"
            "ВОИН - Танк, высокий HP\n"
            "ПАЛАДИН - Баланс, исцеление\n"
            "МАГ - Высокий урон, низкая защита\n"
            "ЛУЧНИК - Высокий крит\n"
            "ЧЕРНОКНИЖНИК - Порча и вампиризм"
        )
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif query.data.startswith("class_"):
        char_class = query.data.replace("class_", "")

        if tg_id not in user_creation_state:
            await query.edit_message_text("Ошибка! Начни создание персонажа заново.")
            return

        race = user_creation_state[tg_id]["race"]
        username = query.from_user.username
        name = query.from_user.first_name or "Игрок"

        players = load_players()
        profile = PlayerProfile(
            tg_id=tg_id,
            username=username,
            name=name,
            race=race,
            char_class=char_class
        )
        set_profile(players, profile)
        save_players(players)

        del user_creation_state[tg_id]

        race_obj = get_race(race)
        class_obj = get_class(char_class)

        keyboard = [[InlineKeyboardButton("В главное меню", callback_data="back_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            f"ПЕРСОНАЖ СОЗДАН!\n\n"
            f"{name}\n"
            f"Раса: {race_obj.race_name}\n"
            f"Класс: {class_obj.class_name}\n"
            f"Уровень: {profile.level}\n\n"
            f"Теперь ты можешь сражаться с другими игроками!"
        )
        await query.edit_message_text(text, reply_markup=reply_markup)

    # ========== ПРОФИЛЬ ==========
    elif query.data == "me":
        players = load_players()
        profile = get_profile(players, tg_id)

        if not profile:
            keyboard = [[InlineKeyboardButton("Создать персонажа", callback_data="create_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "У тебя еще нет персонажа!\n\nСоздай его, чтобы начать играть:",
                reply_markup=reply_markup
            )
            return

        c = make_character_from_profile(profile)
        winrate = (profile.wins / (profile.wins + profile.losses) * 100) if (profile.wins + profile.losses) > 0 else 0

        keyboard = [
            [InlineKeyboardButton("Удалить персонажа", callback_data="delete_confirm")],
            [InlineKeyboardButton("В главное меню", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            f"ПРОФИЛЬ ИГРОКА\n\n"
            f"Имя: {profile.name}\n"
            f"Раса: {c.race.race_name}\n"
            f"Класс: {c.char_class.class_name}\n"
            f"Уровень: {profile.level}/{Character.max_level}\n"
            f"Побед: {profile.wins}\n"
            f"Поражений: {profile.losses}\n"
            f"Винрейт: {winrate:.1f}%\n\n"
            f"{stats_to_text(c)}"
        )
        await query.edit_message_text(text, reply_markup=reply_markup)

    # ========== ТЕСТОВЫЙ БОЙ ==========
    elif query.data == "fight_menu":
        players = load_players()
        profile = get_profile(players, tg_id)

        if not profile:
            keyboard = [[InlineKeyboardButton("Создать персонажа", callback_data="create_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "Сначала создай персонажа!",
                reply_markup=reply_markup
            )
            return

        # Создаем бой с самим собой
        c1 = make_character_from_profile(profile)
        c2 = make_character_from_profile(profile)

        battle = Battle(c1, c2)
        active_battles[tg_id] = battle

        keyboard = [
            [InlineKeyboardButton("Атаковать", callback_data=f"battle_action_{BattleAction.ATTACK}")],
            [InlineKeyboardButton("Встать в блок", callback_data=f"battle_action_{BattleAction.BLOCK}")],
        ]

        if not battle.get_current_character().state.skill_used:
            keyboard.append([InlineKeyboardButton(
                f"Навык: {battle.get_current_character().char_class.offensive_skill_name}",
                callback_data=f"battle_action_{BattleAction.SKILL_OFFENSIVE}"
            )])
            keyboard.append([InlineKeyboardButton(
                f"Навык: {battle.get_current_character().char_class.defensive_skill_name}",
                callback_data=f"battle_action_{BattleAction.SKILL_DEFENSIVE}"
            )])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = battle.get_battle_status()
        text += f"\n\nСейчас ходит: Игрок {battle.current_player}"
        text += f"\nВыбери действие:"

        await query.edit_message_text(text, reply_markup=reply_markup)

    elif query.data.startswith("battle_action_"):
        if tg_id not in active_battles:
            await query.edit_message_text("Бой не найден! Начни новый бой.")
            return

        battle = active_battles[tg_id]
        action = query.data.replace("battle_action_", "")

        # Выполняем действие
        action_log = battle.execute_action(action)

        # Проверяем победу
        winner = battle.get_winner()
        if winner:
            del active_battles[tg_id]

            keyboard = [[InlineKeyboardButton("В главное меню", callback_data="back_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            full_log = battle.get_full_log()

            # Отправляем лог частями
            chunk_size = 3500
            for i in range(0, len(full_log), chunk_size):
                if i == 0:
                    await query.edit_message_text(full_log[i:i + chunk_size])
                else:
                    await query.message.reply_text(full_log[i:i + chunk_size])

            await query.message.reply_text("Выбери действие:", reply_markup=reply_markup)
            return

        # Продолжаем бой
        keyboard = [
            [InlineKeyboardButton("Атаковать", callback_data=f"battle_action_{BattleAction.ATTACK}")],
            [InlineKeyboardButton("Встать в блок", callback_data=f"battle_action_{BattleAction.BLOCK}")],
        ]

        current_char = battle.get_current_character()
        if not current_char.state.skill_used:
            keyboard.append([InlineKeyboardButton(
                f"Навык: {current_char.char_class.offensive_skill_name}",
                callback_data=f"battle_action_{BattleAction.SKILL_OFFENSIVE}"
            )])
            keyboard.append([InlineKeyboardButton(
                f"Навык: {current_char.char_class.defensive_skill_name}",
                callback_data=f"battle_action_{BattleAction.SKILL_DEFENSIVE}"
            )])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = action_log
        text += "\n" + battle.get_battle_status()
        text += f"\n\nСейчас ходит: Игрок {battle.current_player}"
        text += f"\nВыбери действие:"

        await query.edit_message_text(text, reply_markup=reply_markup)

    # ========== ИНФОРМАЦИЯ ==========
    elif query.data == "info_menu":
        keyboard = [
            [InlineKeyboardButton("Расы", callback_data="info_races")],
            [InlineKeyboardButton("Классы", callback_data="info_classes")],
            [InlineKeyboardButton("Назад", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = "ИНФОРМАЦИЯ\n\nВыбери раздел:"
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif query.data == "info_races":
        text = (
            "РАСЫ\n\n"
            "ЭЛЬФ\n"
            "Ловкие воины с острым зрением\n"
            "+10% атаки, -10% HP\n"
            "Способность: Уклонение (20%)\n\n"
            "ЧЕЛОВЕК\n"
            "Универсальные бойцы\n"
            "+10% защиты\n"
            "Сбалансированные характеристики\n\n"
            "ТРОЛЛЬ\n"
            "Могучие танки\n"
            "+30% HP, -10% атаки\n"
            "Высокая живучесть"
        )

        keyboard = [[InlineKeyboardButton("Назад", callback_data="info_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif query.data == "info_classes":
        keyboard = [
            [InlineKeyboardButton("Воин", callback_data="class_info_warrior")],
            [InlineKeyboardButton("Паладин", callback_data="class_info_paladin")],
            [InlineKeyboardButton("Маг", callback_data="class_info_mage")],
            [InlineKeyboardButton("Лучник", callback_data="class_info_archer")],
            [InlineKeyboardButton("Чернокнижник", callback_data="class_info_warlock")],
            [InlineKeyboardButton("Назад", callback_data="info_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = "КЛАССЫ\n\nВыбери класс для просмотра:"
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif query.data.startswith("class_info_"):
        class_name = query.data.replace("class_info_", "")
        char_class = get_class(class_name)
        temp_char = Character(Human(), char_class, level=1)

        text = stats_to_text(temp_char)
        text += f"\n\nНАВЫКИ:\n"
        text += f"Атакующий: {char_class.offensive_skill_name}\n"
        text += f"Защитный: {char_class.defensive_skill_name}"

        keyboard = [[InlineKeyboardButton("Назад", callback_data="info_classes")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    # ========== УДАЛЕНИЕ ==========
    elif query.data == "delete_confirm":
        keyboard = [
            [InlineKeyboardButton("Да, удалить", callback_data="delete_yes")],
            [InlineKeyboardButton("Отмена", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ\n\n"
            "Ты уверен, что хочешь удалить своего персонажа?\n\n"
            "Все достижения, уровень и статистика будут потеряны!\n\n"
            "Это действие нельзя отменить."
        )
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif query.data == "delete_yes":
        players = load_players()

        if str(tg_id) in players:
            del players[str(tg_id)]
            save_players(players)

        keyboard = [[InlineKeyboardButton("Создать нового персонажа", callback_data="create_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "ПЕРСОНАЖ УДАЛЕН\n\n"
            "Твой персонаж успешно удален.\n"
            "Теперь ты можешь создать нового!"
        )
        await query.edit_message_text(text, reply_markup=reply_markup)

    # ========== ГЛАВНОЕ МЕНЮ ==========
    elif query.data == "back_main":
        keyboard = [
            [
                InlineKeyboardButton("Создать персонажа", callback_data="create_menu"),
                InlineKeyboardButton("Мой профиль", callback_data="me")
            ],
            [
                InlineKeyboardButton("PvP битва", callback_data="pvp_menu"),
                InlineKeyboardButton("Тестовый бой", callback_data="fight_menu")
            ],
            [
                InlineKeyboardButton("Информация", callback_data="info_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "RPG BATTLE BOT\n\n"
            "Выбери действие:"
        )
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif query.data == "pvp_menu":
        await query.edit_message_text("PvP режим в разработке! Пока доступен только тестовый бой с самим собой.")


def main() -> None:
    token = os.getenv("BOT_TOKEN") or "8571129347:AAFMWWPwsRBBQBWjy-mT25DHTY8XdA2SngY"
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()