
import tkinter as tk
import random
import math
import time
import json
import os


# ============================================================
# M.JAHANARA - NEON STRIKE
# Python Space Shooter Game
# ============================================================

BG = "#03050b"
PANEL = "#090b13"
RED = "#ff304f"
BLUE = "#28cfff"
WHITE = "#f4f5ff"
GRAY = "#9ca5bb"
GOLD = "#ffd166"

SAVE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "sky_game_save.json"
)


def clamp(value, low, high):
    return max(low, min(value, high))


class NeonStrike:

    def __init__(self, root):

        self.root = root
        self.root.title("M.JAHANARA | NEON STRIKE")
        self.root.configure(bg=BG)

        self.root.attributes("-fullscreen", True)

        self.canvas = tk.Canvas(
            root,
            bg=BG,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        self.width = 1000
        self.height = 700
        self.scale = 1.0

        self.state = "menu"
        self.running = True

        # Game variables
        self.score = 0
        self.best_score = 0
        self.lives = 3

        self.player = None
        self.enemies = []
        self.bullets = []
        self.explosions = []

        # Input
        self.keys = set()
        self.pointer_down = False
        self.touch_direction = (0, 0)

        # Timers
        self.last_shot = 0
        self.last_spawn = 0
        self.invulnerable_until = 0

        self.frame_delay = 16

        # Settings
        self.difficulty = "NORMAL"
        self.auto_shoot = True
        self.sound_enabled = False
        self.touch_controls = True

        self.load_data()
        self.configure_difficulty()

        # Events
        self.root.bind("<KeyPress>", self.key_down)
        self.root.bind("<KeyRelease>", self.key_up)
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.escape)

        self.canvas.bind("<Configure>", self.resize)
        self.canvas.bind("<Button-1>", self.mouse_down)
        self.canvas.bind("<B1-Motion>", self.mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_up)

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.draw_menu()

        self.root.after(100, self.initial_resize)
        self.root.after(self.frame_delay, self.game_loop)

    # ========================================================
    # SAVE AND LOAD
    # ========================================================

    def load_data(self):

        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)

            self.best_score = max(
                0,
                int(data.get("best_score", 0))
            )

            settings = data.get("settings", {})

            if settings.get("difficulty") in (
                "EASY", "NORMAL", "HARD"
            ):
                self.difficulty = settings["difficulty"]

            self.auto_shoot = bool(
                settings.get("auto_shoot", True)
            )

            self.sound_enabled = bool(
                settings.get("sound", False)
            )

            self.touch_controls = bool(
                settings.get("touch", True)
            )

        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def save_data(self):

        data = {
            "best_score": self.best_score,
            "settings": {
                "difficulty": self.difficulty,
                "auto_shoot": self.auto_shoot,
                "sound": self.sound_enabled,
                "touch": self.touch_controls
            }
        }

        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)

        except OSError:
            pass

    # ========================================================
    # DIFFICULTY
    # ========================================================

    def configure_difficulty(self):

        configurations = {

            "EASY": {
                "spawn": 1.7,
                "enemy_speed": (1.0, 1.7),
                "enemy_health": 1,
                "enemy_shot": 2.2,
                "player_speed": 7.0
            },

            "NORMAL": {
                "spawn": 1.2,
                "enemy_speed": (1.5, 2.5),
                "enemy_health": 1,
                "enemy_shot": 1.5,
                "player_speed": 6.0
            },

            "HARD": {
                "spawn": 0.8,
                "enemy_speed": (2.0, 3.4),
                "enemy_health": 2,
                "enemy_shot": 1.0,
                "player_speed": 5.5
            }
        }

        config = configurations[self.difficulty]

        self.spawn_delay = config["spawn"]
        self.enemy_speed_range = config["enemy_speed"]
        self.enemy_health = config["enemy_health"]
        self.enemy_shot_delay = config["enemy_shot"]
        self.player_speed = config["player_speed"]

    # ========================================================
    # SCREEN AND RESPONSIVE LAYOUT
    # ========================================================

    def initial_resize(self):

        self.width = max(320, self.canvas.winfo_width())
        self.height = max(300, self.canvas.winfo_height())

        self.update_scale()
        self.redraw_current_screen()

    def update_scale(self):

        self.scale = clamp(
            min(
                self.width / 1000,
                self.height / 700
            ),
            0.45,
            1.6
        )

    def resize(self, event):

        if event.width < 100 or event.height < 100:
            return

        old_width = self.width
        old_height = self.height

        if old_width == event.width and old_height == event.height:
            return

        self.width = event.width
        self.height = event.height

        self.update_scale()

        rx = self.width / max(old_width, 1)
        ry = self.height / max(old_height, 1)

        if self.player:

            self.player["x"] *= rx
            self.player["y"] *= ry

        for enemy in self.enemies:
            enemy["x"] *= rx
            enemy["y"] *= ry

        for bullet in self.bullets:
            bullet["x"] *= rx
            bullet["y"] *= ry

        for particle in self.explosions:
            particle["x"] *= rx
            particle["y"] *= ry

        self.redraw_current_screen()

    def redraw_current_screen(self):

        if self.state == "menu":
            self.draw_menu()

        elif self.state == "settings":
            self.draw_settings()

        elif self.state == "scores":
            self.draw_scores()

        elif self.state == "about":
            self.draw_about()

        elif self.state == "playing":
            self.draw_background()
            self.draw_game()

        elif self.state == "paused":
            self.draw_background()
            self.draw_game()
            self.draw_pause()

        elif self.state == "gameover":
            self.draw_game_over()

    # ========================================================
    # DRAWING FUNCTIONS
    # ========================================================

    def clear(self):
        self.canvas.delete("all")

    def text(
        self,
        x,
        y,
        value,
        size=14,
        color=WHITE,
        bold=False,
        tags=()
    ):

        self.canvas.create_text(
            x,
            y,
            text=value,
            fill=color,
            font=(
                "Arial",
                max(8, int(size * self.scale)),
                "bold" if bold else "normal"
            ),
            tags=tags
        )

    def rectangle(
        self,
        x1,
        y1,
        x2,
        y2,
        fill=PANEL,
        outline=RED,
        width=2,
        tags=()
    ):

        self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill=fill,
            outline=outline,
            width=max(1, int(width * self.scale)),
            tags=tags
        )

    def panel(self, x1, y1, x2, y2):

        self.rectangle(
            x1,
            y1,
            x2,
            y2,
            fill="#080911",
            outline=RED
        )

        self.canvas.create_line(
            x1 + 12,
            y1 + 4,
            x2 - 12,
            y1 + 4,
            fill="#702036"
        )

    def button(
        self,
        x,
        y,
        width,
        height,
        label,
        callback,
        primary=False
    ):

        tag = f"button_{len(self.canvas.find_all())}"

        x1 = x - width / 2
        y1 = y - height / 2
        x2 = x + width / 2
        y2 = y + height / 2

        fill = "#170810" if primary else "#080911"
        outline = RED if primary else "#713044"

        self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill=fill,
            outline=outline,
            width=max(1, int(2 * self.scale)),
            tags=(tag, "button")
        )

        self.canvas.create_text(
            x,
            y,
            text=label,
            fill=WHITE,
            font=(
                "Arial",
                max(9, int(13 * self.scale)),
                "bold"
            ),
            tags=(tag, "button")
        )

        self.canvas.tag_bind(
            tag,
            "<Button-1>",
            lambda event, fn=callback: self.execute_button(fn)
        )

        self.canvas.tag_bind(
            tag,
            "<Enter>",
            lambda event, t=tag:
                self.canvas.itemconfigure(t, fill="#30101c")
        )

        self.canvas.tag_bind(
            tag,
            "<Leave>",
            lambda event, t=tag, f=fill:
                self.canvas.itemconfigure(t, fill=f)
        )

    def execute_button(self, callback):

        callback()
        return "break"

    # ========================================================
    # BACKGROUND
    # ========================================================

    def draw_background(self):

        self.clear()

        w = self.width
        h = self.height

        self.canvas.configure(bg=BG)

        self.canvas.create_oval(
            -w * .25,
            -h * .3,
            w * .65,
            h * .7,
            fill="#100b1b",
            outline=""
        )

        self.canvas.create_oval(
            w * .55,
            -h * .2,
            w * 1.2,
            h * .55,
            fill="#190817",
            outline=""
        )

        radius = min(w, h) * .17

        px = w * .82
        py = h * .43

        self.canvas.create_oval(
            px-radius,
            py-radius,
            px+radius,
            py+radius,
            fill="#101b32",
            outline="#59233e",
            width=2
        )

        self.canvas.create_arc(
            px-radius-5,
            py-radius-5,
            px+radius+5,
            py+radius+5,
            start=195,
            extent=140,
            style="arc",
            outline="#b22b48",
            width=2
        )

        star_count = max(
            60,
            min(300, int(w * h / 5000))
        )

        for _ in range(star_count):

            x = random.randint(0, max(1, w))
            y = random.randint(0, max(1, h))

            size = random.choice([1, 1, 1, 2])

            color = random.choice([
                "#35415d",
                "#68738f",
                "#69263f",
                "#a34b5e"
            ])

            self.canvas.create_oval(
                x,
                y,
                x+size,
                y+size,
                fill=color,
                outline=""
            )

    def draw_title(self):

        cx = self.width / 2

        self.text(
            cx,
            self.height * .13,
            "M.JAHANARA",
            37,
            WHITE,
            True
        )

        self.text(
            cx,
            self.height * .205,
            "NEON STRIKE",
            32,
            RED,
            True
        )

        self.text(
            cx,
            self.height * .265,
            "F I G H T   •   S U R V I V E   •   W I N",
            10,
            WHITE,
            True
        )

    # ========================================================
    # PLAYER AND ENEMY GRAPHICS
    # ========================================================

    def draw_player_ship(self, x, y):

        s = self.scale

        points = [
            x, y-38*s,
            x-15*s, y+12*s,
            x-45*s, y+30*s,
            x-12*s, y+24*s,
            x, y+38*s,
            x+12*s, y+24*s,
            x+45*s, y+30*s,
            x+15*s, y+12*s
        ]

        self.canvas.create_polygon(
            points,
            fill="#122c4c",
            outline=BLUE,
            width=2,
            tags="dynamic"
        )

        self.canvas.create_oval(
            x-7*s,
            y-8*s,
            x+7*s,
            y+9*s,
            fill=WHITE,
            outline=BLUE,
            tags="dynamic"
        )

        for dx in (-23, 23):

            self.canvas.create_oval(
                x+(dx-7)*s,
                y+22*s,
                x+(dx+7)*s,
                y+43*s,
                fill=BLUE,
                outline="",
                tags="dynamic"
            )

    def draw_enemy_ship(self, x, y):

        s = self.scale

        points = [
            x, y+25*s,
            x-13*s, y+8*s,
            x-32*s, y-10*s,
            x-12*s, y-5*s,
            x, y-31*s,
            x+12*s, y-5*s,
            x+32*s, y-10*s,
            x+13*s, y+8*s
        ]

        self.canvas.create_polygon(
            points,
            fill="#38101f",
            outline=RED,
            width=2,
            tags="dynamic"
        )

        self.canvas.create_oval(
            x-6*s,
            y-7*s,
            x+6*s,
            y+7*s,
            fill=RED,
            outline="#ff9aab",
            tags="dynamic"
        )

    # ========================================================
    # FOOTER
    # ========================================================

    def draw_footer(self):

        self.canvas.create_line(
            self.width*.25,
            self.height-35,
            self.width*.75,
            self.height-35,
            fill="#521a2b"
        )

        self.text(
            self.width/2,
            self.height-19,
            "M.JAHANARA  •  GAME STUDIO",
            10,
            RED,
            True
        )

    # ========================================================
    # MAIN MENU
    # ========================================================

    def draw_menu(self):

        self.state = "menu"

        self.draw_background()
        self.draw_title()

        cx = self.width / 2
        cy = self.height

        self.draw_player_ship(
            cx,
            cy*.405
        )

        start_y = cy*.57

        gap = min(
            49*self.scale,
            cy*.075
        )

        button_width = min(
            self.width*.72,
            340*self.scale
        )

        button_height = max(
            36,
            min(47*self.scale, cy*.07)
        )

        items = [
            ("▶   START GAME", self.start_game, True),
            ("⚙   SETTINGS", self.draw_settings, False),
            ("▤   HIGH SCORES", self.draw_scores, False),
            ("ⓘ   ABOUT", self.draw_about, False),
            ("✕   EXIT", self.close, False)
        ]

        for i, (label, action, primary) in enumerate(items):

            self.button(
                cx,
                start_y+i*gap,
                button_width,
                button_height,
                label,
                action,
                primary
            )

        self.draw_footer()

    # ========================================================
    # SETTINGS
    # ========================================================

    def draw_settings(self):

        self.state = "settings"

        self.draw_background()

        cx = self.width/2
        cy = self.height/2

        self.text(
            cx,
            self.height*.14,
            "SETTINGS",
            30,
            RED,
            True
        )

        pw = min(self.width*.88, 600*self.scale)
        ph = min(self.height*.55, 410*self.scale)

        self.panel(
            cx-pw/2,
            cy-ph/2,
            cx+pw/2,
            cy+ph/2
        )

        row_gap = ph*.19
        first_y = cy-ph*.29

        settings = [
            (
                "DIFFICULTY",
                self.difficulty,
                self.change_difficulty
            ),
            (
                "AUTO SHOOTING",
                "ON" if self.auto_shoot else "OFF",
                self.toggle_auto
            ),
            (
                "SOUND EFFECTS",
                "ON" if self.sound_enabled else "OFF",
                self.toggle_sound
            ),
            (
                "TOUCH CONTROLS",
                "ON" if self.touch_controls else "OFF",
                self.toggle_touch
            )
        ]

        for i, (name, value, action) in enumerate(settings):

            y = first_y+i*row_gap

            self.text(
                cx-pw*.34,
                y,
                name,
                12,
                WHITE,
                True
            )

            self.button(
                cx+pw*.27,
                y,
                pw*.36,
                max(32, 40*self.scale),
                f"<   {value}   >",
                action
            )

        self.button(
            cx,
            cy+ph*.40,
            min(270, pw*.7),
            45,
            "SAVE & BACK",
            self.save_and_back,
            True
        )

        self.draw_footer()

    def change_difficulty(self):

        options = ["EASY", "NORMAL", "HARD"]

        index = options.index(self.difficulty)

        self.difficulty = options[
            (index+1) % len(options)
        ]

        self.configure_difficulty()
        self.draw_settings()

    def toggle_auto(self):

        self.auto_shoot = not self.auto_shoot
        self.draw_settings()

    def toggle_sound(self):

        self.sound_enabled = not self.sound_enabled

        if self.sound_enabled:
            self.play_sound()

        self.draw_settings()

    def toggle_touch(self):

        self.touch_controls = not self.touch_controls
        self.draw_settings()

    def save_and_back(self):

        self.save_data()
        self.draw_menu()

    # ========================================================
    # HIGH SCORES
    # ========================================================

    def draw_scores(self):

        self.state = "scores"

        self.draw_background()

        cx = self.width/2
        cy = self.height/2

        self.text(
            cx,
            self.height*.23,
            "HIGH SCORES",
            30,
            RED,
            True
        )

        pw = min(
            self.width*.82,
            480*self.scale
        )

        self.panel(
            cx-pw/2,
            cy-90*self.scale,
            cx+pw/2,
            cy+80*self.scale
        )

        self.text(
            cx,
            cy-43*self.scale,
            "BEST SCORE",
            15,
            GRAY,
            True
        )

        self.text(
            cx,
            cy+15*self.scale,
            str(self.best_score),
            35,
            GOLD,
            True
        )

        self.button(
            cx,
            cy+145*self.scale,
            min(260, pw*.7),
            45,
            "BACK TO MENU",
            self.draw_menu
        )

        self.draw_footer()

    # ========================================================
    # ABOUT
    # ========================================================

    def draw_about(self):

        self.state = "about"

        self.draw_background()

        cx = self.width/2
        cy = self.height/2

        pw = min(
            self.width*.88,
            600*self.scale
        )

        ph = min(
            self.height*.70,
            490*self.scale
        )

        self.panel(
            cx-pw/2,
            cy-ph/2,
            cx+pw/2,
            cy+ph/2
        )

        self.text(
            cx,
            cy-ph*.35,
            "M.JAHANARA",
            26,
            RED,
            True
        )

        self.text(
            cx,
            cy-ph*.22,
            "NEON STRIKE",
            16,
            WHITE,
            True
        )

        self.text(
            cx,
            cy-ph*.12,
            "A PYTHON SPACE SHOOTER GAME",
            11,
            GRAY,
            True
        )

        self.text(
            cx,
            cy+ph*.05,
            "CONTROLS",
            14,
            RED,
            True
        )

        self.text(
            cx,
            cy+ph*.20,
            "W / A / S / D  -  MOVE\n"
            "ARROW KEYS  -  MOVE\n"
            "MOUSE / TOUCH  -  STEER\n"
            "SPACE  -  SHOOT (AUTO OFF)\n"
            "P / ESC  -  PAUSE\n"
            "F11  -  FULLSCREEN",
            11,
            WHITE,
            True
        )

        self.text(
            cx,
            cy+ph*.40,
            "Made with ♥ by M.JAHANARA",
            11,
            RED,
            True
        )

        self.button(
            cx,
            cy+ph*.59,
            min(250, pw*.7),
            42,
            "BACK TO MENU",
            self.draw_menu
        )

    # ========================================================
    # START GAME
    # ========================================================

    def start_game(self):

        self.configure_difficulty()

        self.state = "playing"

        self.score = 0
        self.lives = 3

        self.enemies.clear()
        self.bullets.clear()
        self.explosions.clear()

        self.keys.clear()

        self.touch_direction = (0, 0)
        self.pointer_down = False

        self.invulnerable_until = 0

        self.player = {
            "x": self.width/2,
            "y": self.height*.80
        }

        now = time.monotonic()

        self.last_shot = now
        self.last_spawn = now

        self.draw_background()
        self.draw_game()

    # ========================================================
    # SHOOTING
    # ========================================================

    def shoot(self, x, y, enemy=False):

        self.bullets.append({

            "x": x,
            "y": y,

            # Player bullets go UP.
            # Enemy bullets go DOWN.
            "speed": 7 if enemy else -9,

            "enemy": enemy
        })

    def player_shoot(self):

        if not self.player or self.state != "playing":
            return

        now = time.monotonic()

        # Prevent rapid repeated manual shots.
        if now-self.last_shot < .18:
            return

        self.shoot(
            self.player["x"],
            self.player["y"]-30*self.scale
        )

        self.last_shot = now

    # ========================================================
    # ENEMY SPAWNING
    # ========================================================

    def spawn_enemy(self):

        margin = 45*self.scale

        self.enemies.append({

            "x": random.uniform(
                margin,
                max(margin+1, self.width-margin)
            ),

            "y": -40*self.scale,

            "speed": random.uniform(
                *self.enemy_speed_range
            ),

            "health": self.enemy_health,

            "last_shot": time.monotonic()
        })

    # ========================================================
    # BULLET COLLISIONS
    # ========================================================

    def update_bullets(self):

        for bullet in self.bullets[:]:

            bullet["y"] += bullet["speed"]*self.scale

            if (
                bullet["y"] < -30
                or bullet["y"] > self.height+30
            ):

                self.bullets.remove(bullet)
                continue

            # Enemy bullet vs player
            if bullet["enemy"]:

                if time.monotonic() < self.invulnerable_until:
                    continue

                if self.player:

                    distance = math.hypot(
                        bullet["x"]-self.player["x"],
                        bullet["y"]-self.player["y"]
                    )

                    if distance < 30*self.scale:

                        self.bullets.remove(bullet)
                        self.player_hit()

                        if self.state != "playing":
                            return

            # Player bullet vs enemies
            else:

                for enemy in self.enemies[:]:

                    distance = math.hypot(
                        bullet["x"]-enemy["x"],
                        bullet["y"]-enemy["y"]
                    )

                    if distance < 32*self.scale:

                        if bullet in self.bullets:
                            self.bullets.remove(bullet)

                        enemy["health"] -= 1

                        if enemy["health"] <= 0:

                            self.explode(
                                enemy["x"],
                                enemy["y"]
                            )

                            self.enemies.remove(enemy)
                            self.score += 10

                        break

    # ========================================================
    # ENEMY MOVEMENT AND ATTACK
    # ========================================================

    def update_enemies(self):

        now = time.monotonic()

        for enemy in self.enemies[:]:

            enemy["y"] += enemy["speed"]*self.scale

            if (
                now-enemy["last_shot"]
                >= self.enemy_shot_delay
            ):

                self.shoot(
                    enemy["x"],
                    enemy["y"]+25*self.scale,
                    enemy=True
                )

                enemy["last_shot"] = now

            # Enemy escaped: player loses one life.
            if enemy["y"] > self.height+45*self.scale:

                self.enemies.remove(enemy)
                self.lives -= 1

                if self.lives <= 0:
                    self.game_over()
                    return

                continue

            # Direct enemy collision with player.
            if self.player:

                distance = math.hypot(
                    enemy["x"]-self.player["x"],
                    enemy["y"]-self.player["y"]
                )

                if (
                    distance < 35*self.scale
                    and now >= self.invulnerable_until
                ):

                    self.enemies.remove(enemy)

                    self.explode(
                        enemy["x"],
                        enemy["y"]
                    )

                    self.player_hit()

                    if self.state != "playing":
                        return

    # ========================================================
    # EXPLOSIONS
    # ========================================================

    def explode(self, x, y):

        for _ in range(14):

            angle = random.uniform(0, math.tau)
            speed = random.uniform(1, 5)

            self.explosions.append({

                "x": x,
                "y": y,

                "dx": math.cos(angle)*speed,
                "dy": math.sin(angle)*speed,

                "life": random.randint(12, 22),

                "size": random.randint(2, 5),

                "color": random.choice([
                    RED,
                    GOLD,
                    WHITE,
                    "#ff8844"
                ])
            })

    def update_explosions(self):

        for particle in self.explosions[:]:

            particle["x"] += particle["dx"]*self.scale
            particle["y"] += particle["dy"]*self.scale

            particle["life"] -= 1

            if particle["life"] <= 0:
                self.explosions.remove(particle)

    # ========================================================
    # PLAYER MOVEMENT
    # ========================================================

    def move_player(self, dx, dy):

        if not self.player:
            return

        speed = self.player_speed*self.scale

        if dx and dy:

            length = math.hypot(dx, dy)

            dx /= length
            dy /= length

        self.player["x"] = clamp(
            self.player["x"]+dx*speed,
            40*self.scale,
            self.width-40*self.scale
        )

        self.player["y"] = clamp(
            self.player["y"]+dy*speed,
            105*self.scale,
            self.height-70*self.scale
        )

    # ========================================================
    # PLAYER DAMAGE
    # ========================================================

    def player_hit(self):

        if self.state != "playing":
            return

        self.lives -= 1

        self.invulnerable_until = time.monotonic()+1.2

        if self.player:

            self.explode(
                self.player["x"],
                self.player["y"]
            )

        self.play_sound()

        if self.lives <= 0:
            self.game_over()

    # ========================================================
    # HUD
    # ========================================================

    def draw_hud(self):

        s = self.scale
        w = self.width

        self.canvas.create_polygon(
            12, 10,
            min(w*.31, 240*s), 10,
            min(w*.34, 255*s), 40,
            min(w*.31, 240*s), 72,
            12, 72,
            fill="#080911",
            outline=RED,
            width=2,
            tags="dynamic"
        )

        self.text(
            27,
            25,
            "SCORE:",
            10,
            WHITE,
            True,
            ("dynamic",)
        )

        self.text(
            75,
            49,
            str(self.score),
            17,
            WHITE,
            True,
            ("dynamic",)
        )

        self.text(
            w/2,
            40,
            "  ".join(["♥"]*self.lives),
            24,
            RED,
            True,
            ("dynamic",)
        )

        bx = w-48

        self.rectangle(
            bx-25,
            12,
            bx+25,
            68,
            fill="#080911",
            outline=RED,
            tags=("dynamic", "pause_button")
        )

        self.text(
            bx,
            40,
            "Ⅱ",
            22,
            WHITE,
            True,
            ("dynamic", "pause_button")
        )

        self.canvas.tag_bind(
            "pause_button",
            "<Button-1>",
            lambda event: self.toggle_pause()
        )

        if self.touch_controls:
            self.draw_touch_controls()

    # ========================================================
    # TOUCH CONTROLS
    # ========================================================

    def draw_touch_controls(self):

        s = self.scale

        x = 78*s
        y = self.height-78*s

        r = 49*s

        self.canvas.create_oval(
            x-r,
            y-r,
            x+r,
            y+r,
            fill="#090c18",
            outline="#77829b",
            width=2,
            tags="dynamic"
        )

        self.canvas.create_oval(
            x-17*s,
            y-17*s,
            x+17*s,
            y+17*s,
            fill="#a31630",
            outline=RED,
            width=2,
            tags="dynamic"
        )

        directions = [
            (0, -32, "▲"),
            (0, 32, "▼"),
            (-32, 0, "◀"),
            (32, 0, "▶")
        ]

        for dx, dy, char in directions:

            self.text(
                x+dx*s,
                y+dy*s,
                char,
                11,
                WHITE,
                True,
                ("dynamic",)
            )

        fx = self.width-76*s
        fy = self.height-78*s

        self.canvas.create_oval(
            fx-39*s,
            fy-39*s,
            fx+39*s,
            fy+39*s,
            fill="#170812",
            outline=RED,
            width=3,
            tags="dynamic"
        )

        self.text(
            fx,
            fy,
            "✥",
            31,
            RED,
            True,
            ("dynamic",)
        )

    # ========================================================
    # DRAW GAME
    # ========================================================

    def draw_game(self):

        self.canvas.delete("dynamic")

        if self.player:

            blink = (
                time.monotonic() < self.invulnerable_until
                and int(time.monotonic()*12)%2 == 0
            )

            if not blink:

                self.draw_player_ship(
                    self.player["x"],
                    self.player["y"]
                )

        for enemy in self.enemies:

            self.draw_enemy_ship(
                enemy["x"],
                enemy["y"]
            )

        for bullet in self.bullets:

            color = RED if bullet["enemy"] else BLUE

            x = bullet["x"]
            y = bullet["y"]

            self.canvas.create_oval(
                x-4*self.scale,
                y-8*self.scale,
                x+4*self.scale,
                y+8*self.scale,
                fill=color,
                outline="",
                tags="dynamic"
            )

        for particle in self.explosions:

            size = particle["size"]*self.scale

            self.canvas.create_oval(
                particle["x"],
                particle["y"],
                particle["x"]+size,
                particle["y"]+size,
                fill=particle["color"],
                outline="",
                tags="dynamic"
            )

        self.draw_hud()

    # ========================================================
    # PAUSE / RESUME
    # ========================================================

    def toggle_pause(self):

        if self.state == "playing":

            self.state = "paused"
            self.draw_pause()

        elif self.state == "paused":

            self.state = "playing"

            # IMPORTANT: Remove the pause overlay on resume.
            self.canvas.delete("pause_overlay")

            self.draw_game()

    def draw_pause(self):

        self.canvas.delete("pause_overlay")

        self.canvas.create_rectangle(
            0,
            0,
            self.width,
            self.height,
            fill="#03040b",
            stipple="gray50",
            outline="",
            tags="pause_overlay"
        )

        cx = self.width/2
        cy = self.height/2

        pw = min(
            self.width*.78,
            470*self.scale
        )

        self.canvas.create_rectangle(
            cx-pw/2,
            cy-110*self.scale,
            cx+pw/2,
            cy+110*self.scale,
            fill=PANEL,
            outline=RED,
            width=2,
            tags="pause_overlay"
        )

        self.canvas.create_text(
            cx,
            cy-55*self.scale,
            text="GAME PAUSED",
            fill=RED,
            font=(
                "Arial",
                max(16, int(26*self.scale)),
                "bold"
            ),
            tags="pause_overlay"
        )

        self.button(
            cx,
            cy,
            min(260, pw*.75),
            44,
            "RESUME GAME",
            self.toggle_pause,
            True
        )

        self.button(
            cx,
            cy+65*self.scale,
            min(260, pw*.75),
            42,
            "MAIN MENU",
            self.draw_menu
        )

    # ========================================================
    # GAME OVER
    # ========================================================

    def game_over(self):

        if self.state != "playing":
            return

        self.state = "gameover"

        self.best_score = max(
            self.best_score,
            self.score
        )

        self.save_data()
        self.draw_game_over()

    def draw_game_over(self):

        self.state = "gameover"

        self.draw_background()

        cx = self.width/2

        self.text(
            cx,
            self.height*.20,
            "☠",
            48,
            RED,
            True
        )

        pw = min(
            self.width*.82,
            550*self.scale
        )

        self.panel(
            cx-pw/2,
            self.height*.29,
            cx+pw/2,
            self.height*.44
        )

        self.text(
            cx,
            self.height*.365,
            "GAME OVER",
            36,
            RED,
            True
        )

        self.text(
            cx,
            self.height*.51,
            "FINAL SCORE",
            16,
            WHITE,
            True
        )

        self.text(
            cx,
            self.height*.58,
            str(self.score),
            32,
            GOLD,
            True
        )

        self.button(
            cx,
            self.height*.70,
            min(300, pw*.72),
            48,
            "↻   RESTART",
            self.start_game,
            True
        )

        self.button(
            cx,
            self.height*.80,
            min(300, pw*.72),
            45,
            "⌂   MAIN MENU",
            self.draw_menu
        )

        self.text(
            cx,
            self.height*.92,
            "M.JAHANARA  •  GAME STUDIO",
            10,
            GRAY,
            True
        )

    # ========================================================
    # MOUSE / TOUCH INPUT
    # ========================================================

    def control_at(self, x, y):

        if not self.touch_controls:
            return None

        s = self.scale

        pad_x = 78*s
        pad_y = self.height-78*s

        fire_x = self.width-76*s
        fire_y = self.height-78*s

        if math.hypot(x-pad_x, y-pad_y) < 55*s:
            return "pad"

        if math.hypot(x-fire_x, y-fire_y) < 45*s:
            return "fire"

        return None

    def set_touch_direction(self, x, y):

        pad_x = 78*self.scale
        pad_y = self.height-78*self.scale

        dx = x-pad_x
        dy = y-pad_y

        distance = math.hypot(dx, dy)

        if distance < 8:
            self.touch_direction = (0, 0)

        else:
            self.touch_direction = (
                dx/distance,
                dy/distance
            )

    def mouse_down(self, event):

        if self.state != "playing":
            return

        control = self.control_at(event.x, event.y)

        if control == "pad":

            self.pointer_down = True

            self.set_touch_direction(
                event.x,
                event.y
            )

            return

        if control == "fire":

            self.player_shoot()
            return

        self.pointer_down = True

        if self.player:

            self.player["x"] = clamp(
                event.x,
                40*self.scale,
                self.width-40*self.scale
            )

            self.player["y"] = clamp(
                event.y,
                105*self.scale,
                self.height-70*self.scale
            )

    def mouse_move(self, event):

        if self.state != "playing":
            return

        control = self.control_at(event.x, event.y)

        if control == "pad":

            self.set_touch_direction(
                event.x,
                event.y
            )

        elif control == "fire":

            self.player_shoot()

        elif self.pointer_down and self.player:

            self.player["x"] = clamp(
                event.x,
                40*self.scale,
                self.width-40*self.scale
            )

            self.player["y"] = clamp(
                event.y,
                105*self.scale,
                self.height-70*self.scale
            )

    def mouse_up(self, _event):

        self.pointer_down = False
        self.touch_direction = (0, 0)

    # ========================================================
    # KEYBOARD
    # ========================================================

    def key_down(self, event):

        key = event.keysym.lower()

        if key in self.keys:
            return

        self.keys.add(key)

        if key == "space":

            if self.state == "playing" and not self.auto_shoot:
                self.player_shoot()

        elif key == "r":

            if self.state == "gameover":
                self.start_game()

    def key_up(self, event):

        self.keys.discard(event.keysym.lower())

    def toggle_fullscreen(self, _event=None):

        current = bool(
            self.root.attributes("-fullscreen")
        )

        self.root.attributes(
            "-fullscreen",
            not current
        )

        return "break"

    def escape(self, _event=None):

        if self.state in ("playing", "paused"):

            self.toggle_pause()

        else:

            self.root.attributes(
                "-fullscreen",
                False
            )

        return "break"

    # ========================================================
    # SOUND
    # ========================================================

    def play_sound(self):

        if not self.sound_enabled:
            return

        try:
            self.root.bell()

        except tk.TclError:
            pass

    # ========================================================
    # GAME LOOP
    # ========================================================

    def game_loop(self):

        if not self.running:
            return

        try:

            if self.state == "playing":

                dx = 0
                dy = 0

                if (
                    "a" in self.keys
                    or "left" in self.keys
                ):
                    dx -= 1

                if (
                    "d" in self.keys
                    or "right" in self.keys
                ):
                    dx += 1

                if (
                    "w" in self.keys
                    or "up" in self.keys
                ):
                    dy -= 1

                if (
                    "s" in self.keys
                    or "down" in self.keys
                ):
                    dy += 1

                tx, ty = self.touch_direction

                dx += tx
                dy += ty

                self.move_player(dx, dy)

                now = time.monotonic()

                # Automatic shooting
                if (
                    self.auto_shoot
                    and now-self.last_shot >= .23
                ):

                    self.player_shoot()

                # Spawn enemies
                if now-self.last_spawn >= self.spawn_delay:

                    self.spawn_enemy()
                    self.last_spawn = now

                # Update objects
                self.update_enemies()

                if self.state == "playing":
                    self.update_bullets()

                if self.state == "playing":
                    self.update_explosions()

                if self.state == "playing":
                    self.draw_game()

            if self.running:

                self.root.after(
                    self.frame_delay,
                    self.game_loop
                )

        except tk.TclError:
            self.running = False

    # ========================================================
    # EXIT
    # ========================================================

    def close(self):

        self.running = False

        self.save_data()

        try:
            self.root.destroy()

        except tk.TclError:
            pass


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    game = NeonStrike(root)

    root.mainloop()
