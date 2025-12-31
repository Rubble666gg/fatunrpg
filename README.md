# fatunrpg
RPG Battle Telegram Bot
Описание (Russian)

пошаговый RPG-бот для Telegram, написанный на Python.
Игроки создают персонажей, выбирая расу и класс, и участвуют в тактических пошаговых боях с использованием атак, защиты и уникальных способностей.

Проект реализует полноценную боевую систему с критическими ударами, эффектами, оглушением, лечением и воскрешением.

 Основные возможности

Создание персонажа (раса + класс)

Пошаговая боевая система

Расовые способности (например, уклонение у эльфов)

Классовые активные навыки (атакующие и защитные)

Критические удары и модификаторы урона

Статусы: блок, оглушение, усиления, порча, воскрешение

Профиль игрока (уровень, победы, поражения)
Тестовый бой (игра против самого себя)
Telegram Inline-кнопки
Хранение данных в JSON

 Расы

Эльф — уклонение 20%, ↑ атака, ↓ HP

Человек — сбалансированные характеристики, ↑ защита

Тролль — ↑ HP, ↓ атака

 Классы

Воин

Паладин

Маг

Лучник

Чернокнижник

Каждый класс имеет уникальный атакующий и защитный навык.
Description (English)

Turn-based RPG Telegram bot written in Python.
Players create characters by choosing a race and a class, then fight in tactical turn-based battles using attacks, defense, and unique abilities.

The project features a full combat system with critical hits, status effects, stuns, healing, and resurrection mechanics.
 Features

Character creation (race + class)

Turn-based combat system

Racial abilities (e.g. elf dodge chance)

Class active skills (offensive & defensive)

Critical hits and damage modifiers

Status effects: block, stun, buffs, corruption, resurrection

Player profile (level, wins, losses)

Test battle mode (fight yourself)

Telegram inline keyboards

JSON-based data storage

Races

Elf — 20% dodge chance, ↑ attack, ↓ HP

Human — balanced stats, ↑ defense

Troll — ↑ HP, ↓ attack

Classes

Warrior

Paladin

Mage

Archer

Warlock

Each class has unique offensive and defensive abilities.

Tech Stack

Python 3.10+
python-telegram-bot
dataclasses
JSON storage
