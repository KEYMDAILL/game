from __future__ import annotations

import random
import sys
from typing import List, Tuple

import pygame

from settings import *
from models import GameState, InputState, LevelData, ShotEvent
from helpers import calculate_saved_stars, clamp, draw_centered, draw_glow, draw_star_icons, draw_text, format_time, make_font, tile_center
from save_manager import SaveManager
from sound_manager import SoundManager
from particles import ParticleSystem
from entities import Ghost, Player
from record_system import RecordSystem
from level import Level
from levels import make_levels

class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Echoes of Time")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_small = make_font(16)
        self.font = make_font(21)
        self.font_big = make_font(46, bold=True)
        self.font_title = make_font(62, bold=True)

        self.save_manager = SaveManager()
        self.sound = SoundManager(self.save_manager.settings)
        self.particles = ParticleSystem()
        self.levels = make_levels()

        self.state = GameState.MAIN_MENU
        self.running = True
        self.menu_index = 0
        self.level_select_index = 0
        self.settings_index = 0

        self.current_level_index = 0
        self.level = Level(self.levels[self.current_level_index])
        self.player = Player(tile_center(self.level.data.player_start))
        self.ghosts: List[Ghost] = []
        self.recorder = RecordSystem()
        self.elapsed = 0.0

        self.completed_time = 0.0
        self.completed_ghosts = 0
        self.completed_coins = 0
        self.completed_stars = 0
        self.last_improved = False
        self.coins_this_run = 0

        self.shake_timer = 0.0
        self.shake_strength = 0.0
        self.message_timer = 0.0
        self.message_text = ""

#ИГРОВОЙ ЦИКЛ
    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(FPS_LIMIT) / 1000.0, MAX_DT)
            input_state = self.handle_input()
            self.update(dt, input_state)
            self.render()
        pygame.quit()
        sys.exit()
#ОБРАБОТКА ВВОДА
    def handle_input(self) -> InputState:

        shoot_pressed = False
        restart_pressed = False
        next_level_pressed = False
        quit_pressed = False
        start_pressed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_pressed = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    quit_pressed = True
                elif event.key == pygame.K_RETURN:
                    start_pressed = True
                elif event.key == pygame.K_SPACE:
                    shoot_pressed = True
                elif event.key == pygame.K_r:
                    restart_pressed = True
                elif event.key == pygame.K_n:
                    next_level_pressed = True
                elif event.key in (pygame.K_w, pygame.K_UP):
                    self.menu_up()
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    self.menu_down()
                elif event.key in (pygame.K_a, pygame.K_LEFT):
                    self.menu_left()
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    self.menu_right()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                shoot_pressed = True

        if start_pressed:
            self.menu_confirm()

        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)
        if self.state == GameState.PLAYING:
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                move.x -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                move.x += 1
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                move.y -= 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                move.y += 1
        return InputState(move, shoot_pressed, restart_pressed, next_level_pressed, quit_pressed)

    def update(self, dt: float, input_state: InputState) -> None:
#Выход
        if input_state.quit_pressed:
            self.handle_escape()
#следующий уровень          
        if input_state.next_level_pressed and self.state == GameState.PLAYING:
            self.load_level((self.current_level_index + 1) % len(self.levels), reset_progress=True)
            self.sound.play("menu")

        self.message_timer = max(0.0, self.message_timer - dt)
        self.shake_timer = max(0.0, self.shake_timer - dt)
        self.particles.update(dt)

        if self.state != GameState.PLAYING:
            return
        
        self.elapsed += dt
        ghost_shots: List[ShotEvent] = []
        for ghost in self.ghosts:
            ghost_shots.extend(ghost.update(dt, self.elapsed))

        player_shot = self.player.update(dt, input_state, self.level)
        shot_events = ghost_shots + ([player_shot] if player_shot is not None else [])
        for shot_event in shot_events:
            self.process_shot(shot_event)

        collected, door_changed = self.level.update(dt, self.elapsed, self.player, self.ghosts)
        if collected:
            self.coins_this_run += collected
            self.sound.play("coin")
            self.particles.spawn_burst(self.player.rect.center, COLOR_COIN, 14, 95, 0.22)
        if door_changed:
            self.sound.play("door")
            self.add_shake(0.08, 2.0)

        self.recorder.update(self.elapsed, self.player)
#УСЛОВИЯ
        if self.level.player_touched_guard(self.player):
            self.show_message("Тебя убили. Время откатилось.")
            self.restart_run(save_player_echo=True)
            return

        if input_state.restart_pressed:
            self.show_message("Откат времени: прошлый забег стал эхо.")
            self.restart_run(save_player_echo=True)
            return

        if self.elapsed >= self.level.data.duration:
            self.show_message("Время вышло. Запись сохранена как эхо.")
            self.restart_run(save_player_echo=True)
            return

        if self.player.rect.colliderect(self.level.exit_rect) and self.level.all_targets_down():
            self.complete_level()

    def render(self) -> None:

        self.screen.fill(COLOR_BG)
        if self.state == GameState.MAIN_MENU:
            self.draw_main_menu()
        elif self.state == GameState.LEVEL_SELECT:
            self.draw_level_select()
        elif self.state == GameState.SETTINGS:
            self.draw_settings()
        elif self.state in (GameState.PLAYING, GameState.LEVEL_COMPLETE, GameState.FINAL_SCREEN):
            self.draw_game_world()
            if self.state == GameState.LEVEL_COMPLETE:
                self.draw_complete_overlay()
            elif self.state == GameState.FINAL_SCREEN:
                self.draw_final_overlay()
        pygame.display.flip()

 
    def process_shot(self, event: ShotEvent) -> None:
        hits = self.level.apply_shot(event, self.elapsed)
        shot_rect, start, end = self.level.build_shot_rect(event.origin, event.direction)
        self.sound.play("shotgun")
        self.particles.spawn_muzzle(start, end)
        self.add_shake(0.12, 5.0)
        if hits:
            self.sound.play("hit")
            for pos in hits:
                self.particles.spawn_burst(pos, COLOR_ENEMY, 30, 190, 0.35)
#Откат времени
    def restart_run(self, save_player_echo: bool) -> None:
        self.level.finalize_run_enemy_memories()
        frames = self.recorder.export()
        if save_player_echo and len(frames) > 4 and len(self.ghosts) < MAX_GHOSTS_PER_LEVEL:
            self.ghosts.append(Ghost(frames, len(self.ghosts) + 1))

        for ghost in self.ghosts:
            ghost.reset()
        self.level.start_run()
        self.player = Player(tile_center(self.level.data.player_start))
        self.recorder.clear()
        self.elapsed = 0.0
        self.coins_this_run = 0
        self.sound.play("rewind")
        self.particles.spawn_burst(self.player.rect.center, COLOR_BLUE, 36, 160, 0.35)
        self.add_shake(0.18, 4.0)

    def complete_level(self) -> None:
        self.completed_time = self.elapsed
        self.completed_ghosts = len(self.ghosts)
        self.completed_coins = self.coins_this_run
        self.completed_stars = self.calculate_stars(self.level.data, self.completed_time, self.completed_ghosts, self.completed_coins)
        self.last_improved = self.save_manager.update_record(
            self.level.data,
            self.completed_time,
            self.completed_ghosts,
            self.completed_coins,
            self.completed_stars,
        )
        self.state = GameState.LEVEL_COMPLETE
        self.sound.play("win")
        self.particles.spawn_burst(self.player.rect.center, COLOR_EXIT_READY, 80, 220, 0.55)

    def calculate_stars(self, level: LevelData, time_value: float, ghosts_used: int, coins: int) -> int:


        stars = 0
        if time_value <= level.target_time:
            stars += 1
        if coins >= len(level.coins):
            stars += 1
        if ghosts_used <= level.target_ghosts:
            stars += 1
        return stars

    def load_level(self, index: int, reset_progress: bool = True) -> None:
        self.current_level_index = index % len(self.levels)
        self.level = Level(self.levels[self.current_level_index])
        self.player = Player(tile_center(self.level.data.player_start))
        self.ghosts = []
        self.recorder.clear()
        self.elapsed = 0.0
        self.coins_this_run = 0
        self.particles.clear()
        self.state = GameState.PLAYING
        if reset_progress:
            self.show_message(self.level.data.hint)

    def show_message(self, text: str) -> None:
        self.message_text = text
        self.message_timer = 3.0

    def add_shake(self, duration: float, strength: float) -> None:
        if not self.save_manager.settings.screen_shake:
            return
        self.shake_timer = max(self.shake_timer, duration)
        self.shake_strength = max(self.shake_strength, strength)

    def current_shake_offset(self) -> Tuple[int, int]:
        if self.shake_timer <= 0 or not self.save_manager.settings.screen_shake:
            self.shake_strength = max(0.0, self.shake_strength * 0.90)
            return (0, 0)
        power = self.shake_strength * (self.shake_timer / 0.18)
        return (round(random.uniform(-power, power)), round(random.uniform(-power, power)))

#МЕНЮ
    def menu_up(self) -> None:
        if self.state == GameState.MAIN_MENU:
            self.menu_index = (self.menu_index - 1) % 4
            self.sound.play("menu")
        elif self.state == GameState.LEVEL_SELECT:
            self.level_select_index = (self.level_select_index - 1) % len(self.levels)
            self.sound.play("menu")
        elif self.state == GameState.SETTINGS:
            self.settings_index = (self.settings_index - 1) % 5
            self.sound.play("menu")

    def menu_down(self) -> None:
        if self.state == GameState.MAIN_MENU:
            self.menu_index = (self.menu_index + 1) % 4
            self.sound.play("menu")
        elif self.state == GameState.LEVEL_SELECT:
            self.level_select_index = (self.level_select_index + 1) % len(self.levels)
            self.sound.play("menu")
        elif self.state == GameState.SETTINGS:
            self.settings_index = (self.settings_index + 1) % 5
            self.sound.play("menu")

    def menu_left(self) -> None:
        if self.state == GameState.SETTINGS:
            self.change_setting(-1)

    def menu_right(self) -> None:
        if self.state == GameState.SETTINGS:
            self.change_setting(1)

    def menu_confirm(self) -> None:
        if self.state == GameState.MAIN_MENU:
            if self.menu_index == 0:
                self.load_level(self.current_level_index)
            elif self.menu_index == 1:
                self.state = GameState.LEVEL_SELECT
            elif self.menu_index == 2:
                self.state = GameState.SETTINGS
            elif self.menu_index == 3:
                self.running = False
        elif self.state == GameState.LEVEL_SELECT:
            self.load_level(self.level_select_index)
        elif self.state == GameState.SETTINGS:
            if self.settings_index == 3:
                self.save_manager.reset_records()
                self.show_message("Рекорды очищены")
            elif self.settings_index == 4:
                self.state = GameState.MAIN_MENU
            else:
                self.change_setting(1)
        elif self.state == GameState.LEVEL_COMPLETE:
            if self.current_level_index + 1 >= len(self.levels):
                self.state = GameState.FINAL_SCREEN
            else:
                self.load_level(self.current_level_index + 1)
        elif self.state == GameState.FINAL_SCREEN:
            self.state = GameState.MAIN_MENU

    def change_setting(self, direction: int) -> None:
        settings = self.save_manager.settings
        if self.settings_index == 0:
            settings.volume = clamp(settings.volume + direction * 0.10, 0.0, 1.0)
            self.sound.apply_volume()
            self.sound.play("menu")
        elif self.settings_index == 1:
            settings.scanlines = not settings.scanlines
            self.sound.play("menu")
        elif self.settings_index == 2:
            settings.screen_shake = not settings.screen_shake
            self.sound.play("menu")
        self.save_manager.save()

    def handle_escape(self) -> None:
        if self.state == GameState.PLAYING:
            self.state = GameState.MAIN_MENU
        elif self.state in (GameState.LEVEL_SELECT, GameState.SETTINGS, GameState.LEVEL_COMPLETE, GameState.FINAL_SCREEN):
            self.state = GameState.MAIN_MENU
        elif self.state == GameState.MAIN_MENU:
            self.running = False


    def draw_main_menu(self) -> None:
        self.draw_background_pattern()
        draw_centered(self.screen, self.font_title, "ECHOES OF TIME", (SCREEN_WIDTH // 2, 120), COLOR_TEXT)
        draw_centered(self.screen, self.font, "тактическая головоломка с эхо-забегами и дробовиком", (SCREEN_WIDTH // 2, 178), COLOR_MUTED)
        options = ["Играть", "Список уровней", "Настройки", "Выход"]
        for i, text in enumerate(options):
            y = 270 + i * 54
            selected = i == self.menu_index
            rect = pygame.Rect(SCREEN_WIDTH // 2 - 170, y - 10, 340, 42)
            pygame.draw.rect(self.screen, COLOR_PANEL_2 if selected else COLOR_PANEL, rect, border_radius=12)
            pygame.draw.rect(self.screen, COLOR_GOLD if selected else (48, 45, 62), rect, 2, border_radius=12)
            draw_centered(self.screen, self.font, text, rect.center, COLOR_GOLD if selected else COLOR_TEXT)
        draw_centered(self.screen, self.font_small, "Enter — выбрать, стрелки/WASD — навигация", (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 55), COLOR_MUTED)

    def draw_level_select(self) -> None:
        self.draw_background_pattern()
        draw_centered(self.screen, self.font_big, "Список уровней", (SCREEN_WIDTH // 2, 60), COLOR_TEXT)
        draw_centered(self.screen, self.font_small, "Цель реиграбельности: меньше эхо, быстрее время, больше монет", (SCREEN_WIDTH // 2, 100), COLOR_MUTED)
        for i, level in enumerate(self.levels):
            y = 145 + i * 92
            selected = i == self.level_select_index
            rect = pygame.Rect(90, y, SCREEN_WIDTH - 180, 76)
            pygame.draw.rect(self.screen, COLOR_PANEL_2 if selected else COLOR_PANEL, rect, border_radius=14)
            pygame.draw.rect(self.screen, COLOR_GOLD if selected else (50, 48, 63), rect, 2, border_radius=14)
            record = self.save_manager.get_record(level.name)
            draw_text(self.screen, self.font, level.name, (rect.x + 18, rect.y + 12), COLOR_GOLD if selected else COLOR_TEXT)

            record.best_stars = max(record.best_stars, calculate_saved_stars(level, record))
            draw_star_icons(self.screen, (rect.right - 92, rect.y + 28), record.best_stars, 13)
            info = f"Рекорд: {format_time(record.best_time)} | эхо: {record.best_ghosts if record.best_ghosts is not None else '—'} | монеты: {record.best_coins}/{len(level.coins)}"
            draw_text(self.screen, self.font_small, info, (rect.x + 18, rect.y + 43), COLOR_MUTED)
            draw_text(self.screen, self.font_small, f"Идеал: {level.target_ghosts} эхо, {level.target_time:.1f} c, все монеты", (rect.right - 355, rect.y + 52), COLOR_GOOD)
        draw_centered(self.screen, self.font_small, "Enter — начать выбранный уровень, Esc — назад", (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 42), COLOR_MUTED)

    def draw_settings(self) -> None:
        self.draw_background_pattern()
        draw_centered(self.screen, self.font_big, "Настройки", (SCREEN_WIDTH // 2, 70), COLOR_TEXT)
        settings = self.save_manager.settings
        options = [
            f"Громкость: {round(settings.volume * 10):02d}/10",
            f"Scanlines: {'вкл' if settings.scanlines else 'выкл'}",
            f"Тряска камеры: {'вкл' if settings.screen_shake else 'выкл'}",
            "Очистить рекорды",
            "Назад",
        ]
        for i, text in enumerate(options):
            y = 180 + i * 56
            selected = i == self.settings_index
            rect = pygame.Rect(SCREEN_WIDTH // 2 - 210, y - 10, 420, 42)
            pygame.draw.rect(self.screen, COLOR_PANEL_2 if selected else COLOR_PANEL, rect, border_radius=12)
            pygame.draw.rect(self.screen, COLOR_GOLD if selected else (48, 45, 62), rect, 2, border_radius=12)
            draw_centered(self.screen, self.font, text, rect.center, COLOR_GOLD if selected else COLOR_TEXT)
        draw_centered(self.screen, self.font_small, "Стрелки ←/→ меняют параметры, Enter подтверждает", (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 48), COLOR_MUTED)
        if self.message_timer > 0:
            draw_centered(self.screen, self.font, self.message_text, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 90), COLOR_GOOD)

    def draw_game_world(self) -> None:
        world = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        self.level.draw(world)
        for ghost in self.ghosts:
            ghost.draw(world)
        self.player.draw(world)
        self.particles.draw(world)
        self.apply_lighting(world)
        offset = self.current_shake_offset()
        self.screen.blit(world, offset)
        self.draw_hud()
        if self.save_manager.settings.scanlines:
            self.draw_scanlines()

    def apply_lighting(self, world: pygame.Surface) -> None:
        darkness = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        darkness.fill((0, 0, 0, 108))
        holes = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        for actor, radius, alpha in [(self.player, 160, 155), *[(g, 110, 80) for g in self.ghosts]]:
            for r in range(radius, 0, -8):
                a = int(alpha * (r / radius) ** 2)
                pygame.draw.circle(holes, (0, 0, 0, a), actor.rect.center, r)
        darkness.blit(holes, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        world.blit(darkness, (0, 0))

    def draw_hud(self) -> None:
        panel = pygame.Rect(0, WORLD_HEIGHT, SCREEN_WIDTH, HUD_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel)
        pygame.draw.line(self.screen, (54, 51, 67), (0, WORLD_HEIGHT), (SCREEN_WIDTH, WORLD_HEIGHT), 2)
        level = self.level.data
        time_left = max(0.0, level.duration - self.elapsed)
        draw_text(self.screen, self.font, level.name, (18, WORLD_HEIGHT + 12), COLOR_TEXT)
        draw_text(self.screen, self.font_small, level.hint, (18, WORLD_HEIGHT + 42), COLOR_MUTED)
        draw_text(self.screen, self.font, f"Время: {time_left:05.2f}", (520, WORLD_HEIGHT + 12), COLOR_GOOD if time_left > 3 else COLOR_WARN)
        draw_text(self.screen, self.font, f"Эхо: {len(self.ghosts)}/{MAX_GHOSTS_PER_LEVEL}", (700, WORLD_HEIGHT + 12), COLOR_BLUE)
        draw_text(self.screen, self.font, f"Патрон: {self.player.shells}/1", (840, WORLD_HEIGHT + 12), COLOR_SHOT if self.player.shells else COLOR_MUTED)
        draw_text(self.screen, self.font_small, f"Монеты: {self.coins_this_run}/{len(level.coins)} | Цели уничтожены: {'да' if self.level.all_targets_down() else 'нет'}", (520, WORLD_HEIGHT + 45), COLOR_MUTED)
        draw_text(self.screen, self.font_small, "Space — выстрел, R — откат времени, Esc — меню", (18, WORLD_HEIGHT + 68), COLOR_MUTED)
        if self.message_timer > 0 and self.state == GameState.PLAYING:
            draw_centered(self.screen, self.font, self.message_text, (SCREEN_WIDTH // 2, WORLD_HEIGHT - 26), COLOR_GOLD)

    def draw_complete_overlay(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 156))
        self.screen.blit(overlay, (0, 0))
        rect = pygame.Rect(SCREEN_WIDTH // 2 - 260, 135, 520, 360)
        pygame.draw.rect(self.screen, COLOR_PANEL_2, rect, border_radius=18)
        pygame.draw.rect(self.screen, COLOR_GOLD, rect, 2, border_radius=18)
        draw_centered(self.screen, self.font_big, "Комната очищена", (SCREEN_WIDTH // 2, rect.y + 48), COLOR_GOLD)
        draw_star_icons(self.screen, (SCREEN_WIDTH // 2, rect.y + 104), self.completed_stars, 24)
        level = self.level.data
        criteria = [
            (f"★ Время: {self.completed_time:.2f} c  / цель {level.target_time:.1f} c", self.completed_time <= level.target_time),
            (f"★ Монеты: {self.completed_coins}/{len(level.coins)}", self.completed_coins >= len(level.coins)),
            (f"★ Эхо: {self.completed_ghosts}  / идеал {level.target_ghosts}", self.completed_ghosts <= level.target_ghosts),
            ("Новый рекорд сохранён" if self.last_improved else "Рекорд не улучшен", self.last_improved),
        ]
        for i, (line, ok) in enumerate(criteria):
            color = COLOR_GOOD if ok else COLOR_MUTED
            if i == 3:
                color = COLOR_GOOD if self.last_improved else COLOR_TEXT
            draw_centered(self.screen, self.font, line, (SCREEN_WIDTH // 2, rect.y + 155 + i * 38), color)
        draw_centered(self.screen, self.font_small, "Enter — следующий уровень, Esc — главное меню", (SCREEN_WIDTH // 2, rect.bottom - 34), COLOR_MUTED)

    def draw_final_overlay(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 172))
        self.screen.blit(overlay, (0, 0))
        draw_centered(self.screen, self.font_big, "Архив времени закрыт", (SCREEN_WIDTH // 2, 210), COLOR_GOLD)
        draw_centered(self.screen, self.font, "Теперь можно перепроходить уровни на 3 звезды: быстрее, чище, с меньшим числом эхо.", (SCREEN_WIDTH // 2, 272), COLOR_TEXT)
        draw_centered(self.screen, self.font_small, "Enter — главное меню", (SCREEN_WIDTH // 2, 340), COLOR_MUTED)

    def draw_background_pattern(self) -> None:
        self.screen.fill(COLOR_BG)
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(self.screen, (22, 21, 31), (0, y), (SCREEN_WIDTH, y), 1)
        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(self.screen, (20, 19, 29), (x, 0), (x, SCREEN_HEIGHT), 1)
        draw_glow(self.screen, (SCREEN_WIDTH // 2, 150), 180, COLOR_BLUE, 30)

    def draw_scanlines(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(0, SCREEN_HEIGHT, 4):
            pygame.draw.line(overlay, (0, 0, 0, 32), (0, y), (SCREEN_WIDTH, y))
        self.screen.blit(overlay, (0, 0))
