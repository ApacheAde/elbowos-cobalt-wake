#!/usr/bin/env python3
"""Cobalt Wake — neon light-cycle arcade for ElbowOS."""
import argparse, math, os, random, subprocess, sys

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "COBALT WAKE"
HANDLE = "x.com/ElbowOS"
CELL = 30
OX, OY = 90, 220
COLS, ROWS = 30, 52
PAL = {
    "bg": (4, 10, 22),
    "grid": (10, 28, 48),
    "rail": (18, 70, 110),
    "cyan": (48, 230, 255),
    "cobalt": (20, 110, 255),
    "mint": (90, 255, 210),
    "magenta": (255, 50, 170),
    "gold": (255, 200, 50),
    "amber": (255, 170, 70),
    "white": (240, 250, 255),
    "dim": (70, 110, 140),
    "crash": (255, 70, 90),
}

DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # N E S W


class Rider:
    def __init__(self, x, y, heading, color, glow, name):
        self.x, self.y, self.h = x, y, heading
        self.color, self.glow, self.name = color, glow, name
        self.alive = True
        self.cool = 0
        self.trail = [(x, y)]

    def ahead(self, h=None):
        dx, dy = DIRS[h if h is not None else self.h]
        return self.x + dx, self.y + dy


class Game:
    def __init__(self, auto=False):
        self.auto = auto
        self.t = self.score = self.cuts = 0
        self.flash = 0
        self.sparks = []
        self.orbs = []
        self.grid = [[0] * COLS for _ in range(ROWS)]
        self.stars = [(random.randrange(W), random.randrange(H), random.randint(1, 2)) for _ in range(55)]
        self._reset_round()

    def _reset_round(self):
        self.grid = [[0] * COLS for _ in range(ROWS)]
        self.player = Rider(5, ROWS - 4, 0, PAL["cyan"], PAL["cobalt"], "YOU")
        self.foes = [
            Rider(COLS - 6, 4, 2, PAL["magenta"], (180, 20, 90), "RIX"),
            Rider(COLS // 2, 4, 2, PAL["gold"], (160, 90, 10), "SOL"),
        ]
        self.orbs = []
        for _ in range(8):
            self._spawn_orb()

    def _spawn_orb(self):
        for _ in range(40):
            x, y = random.randrange(2, COLS - 2), random.randrange(2, ROWS - 2)
            if self.grid[y][x] == 0:
                self.orbs.append([x, y])
                return

    def occupied(self, x, y):
        if x < 0 or y < 0 or x >= COLS or y >= ROWS:
            return True
        return self.grid[y][x] != 0

    def paint(self, rider, tag):
        if 0 <= rider.x < COLS and 0 <= rider.y < ROWS:
            self.grid[rider.y][rider.x] = tag
            rider.trail.append((rider.x, rider.y))
            if len(rider.trail) > 420:
                rider.trail.pop(0)

    def crash(self, rider, reward=False):
        rider.alive = False
        rider.cool = 28
        px, py = self.cell_xy(rider.x, rider.y)
        col = PAL["crash"] if rider is self.player else rider.color
        for _ in range(18):
            a = random.random() * 6.28
            self.sparks.append([px, py, math.cos(a) * 9, math.sin(a) * 9, 16, col])
        if reward and rider is not self.player:
            self.score += 80
            self.cuts += 1
            self.flash = 8

    def cell_xy(self, cx, cy):
        return OX + cx * CELL + CELL // 2, OY + cy * CELL + CELL // 2

    def choose(self, rider):
        opts = []
        for h in (rider.h, (rider.h + 1) % 4, (rider.h + 3) % 4):
            nx, ny = rider.ahead(h)
            if not self.occupied(nx, ny):
                open_n = 0
                for k in range(4):
                    ax, ay = nx + DIRS[k][0], ny + DIRS[k][1]
                    if not self.occupied(ax, ay):
                        open_n += 1
                pull = 0
                if self.orbs:
                    ox, oy = self.orbs[0]
                    pull = -abs(ox - nx) - abs(oy - ny)
                opts.append((open_n * 4 + pull + random.random(), h))
        if not opts:
            return rider.h
        opts.sort(reverse=True)
        return opts[0][1]

    def tick_rider(self, rider, tag, heading=None):
        if not rider.alive:
            rider.cool -= 1
            if rider.cool <= 0:
                for x in range(2, COLS - 2):
                    y = random.randrange(3, ROWS - 3)
                    if self.grid[y][x] == 0:
                        rider.x, rider.y, rider.h = x, y, random.randrange(4)
                        rider.alive = True
                        rider.trail = [(x, y)]
                        break
            return
        if heading is not None and heading != (rider.h + 2) % 4:
            rider.h = heading
        nx, ny = rider.ahead()
        if self.occupied(nx, ny):
            self.crash(rider, reward=(rider is not self.player))
            return
        rider.x, rider.y = nx, ny
        self.paint(rider, tag)
        for o in list(self.orbs):
            if o[0] == nx and o[1] == ny:
                self.orbs.remove(o)
                self._spawn_orb()
                if rider is self.player:
                    self.score += 15
                    self.flash = 5
                px, py = self.cell_xy(nx, ny)
                for _ in range(8):
                    a = random.random() * 6.28
                    self.sparks.append([px, py, math.cos(a) * 6, math.sin(a) * 6, 12, rider.color])

    def autoplay(self):
        self.tick_rider(self.player, 1, self.choose(self.player))

    def step(self, keys=None):
        self.t += 1
        self.flash = max(0, self.flash - 1)
        if self.t % 2 == 0:
            if self.auto:
                self.autoplay()
            elif keys is not None:
                h = None
                if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                    h = 3
                elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                    h = 1
                elif keys[pygame.K_UP] or keys[pygame.K_w]:
                    h = 0
                elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
                    h = 2
                self.tick_rider(self.player, 1, h)
            else:
                self.tick_rider(self.player, 1, None)
            for i, foe in enumerate(self.foes):
                self.tick_rider(foe, 2 + i, self.choose(foe) if foe.alive else None)
            if self.player.alive:
                self.score += 1
        live = []
        for s in self.sparks:
            s[0] += s[2]
            s[1] += s[3]
            s[4] -= 1
            if s[4] > 0:
                live.append(s)
        self.sparks = live

    def draw(self, surf, font, small, mid):
        surf.fill(PAL["bg"])
        for y in range(0, H, 10):
            k = y / H
            pygame.draw.rect(surf, (int(4 + 8 * k), int(10 + 16 * (1 - k)), int(22 + 30 * k)), (0, y, W, 10))
        for x, y, r in self.stars:
            yy = (y + int(self.t * 0.4)) % H
            tw = 60 + int(40 * math.sin(self.t * 0.07 + x))
            pygame.draw.circle(surf, (tw // 3, tw // 2, tw), (x, yy), r)
        arena = pygame.Rect(OX - 8, OY - 8, COLS * CELL + 16, ROWS * CELL + 16)
        pygame.draw.rect(surf, PAL["rail"], arena, 6, border_radius=10)
        for gx in range(COLS + 1):
            x = OX + gx * CELL
            pygame.draw.line(surf, PAL["grid"], (x, OY), (x, OY + ROWS * CELL), 1)
        for gy in range(ROWS + 1):
            y = OY + gy * CELL
            pygame.draw.line(surf, PAL["grid"], (OX, y), (OX + COLS * CELL, y), 1)
        for y in range(ROWS):
            for x in range(COLS):
                tag = self.grid[y][x]
                if not tag:
                    continue
                col = PAL["cyan"] if tag == 1 else (PAL["magenta"] if tag == 2 else PAL["gold"])
                rx, ry = OX + x * CELL + 3, OY + y * CELL + 3
                pygame.draw.rect(surf, col, (rx, ry, CELL - 6, CELL - 6), border_radius=4)
        for ox, oy in self.orbs:
            px, py = self.cell_xy(ox, oy)
            pulse = 7 + int(3 * math.sin(self.t * 0.2 + ox))
            pygame.draw.circle(surf, PAL["mint"], (px, py), pulse)
            pygame.draw.circle(surf, PAL["white"], (px, py), 3)
        riders = [self.player] + self.foes
        for r in riders:
            if not r.alive:
                continue
            px, py = self.cell_xy(r.x, r.y)
            pygame.draw.circle(surf, r.glow, (px, py), 18)
            pygame.draw.circle(surf, r.color, (px, py), 11)
            pygame.draw.circle(surf, PAL["white"], (px, py), 4)
            dx, dy = DIRS[r.h]
            pygame.draw.circle(surf, PAL["white"], (px + dx * 12, py + dy * 12), 4)
        for s in self.sparks:
            pygame.draw.circle(surf, s[5], (int(s[0]), int(s[1])), max(2, s[4] // 3))
        if self.flash:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((90, 255, 210, 14 * self.flash))
            surf.blit(veil, (0, 0))
        banner = pygame.Surface((W, 150), pygame.SRCALPHA)
        banner.fill((2, 8, 18, 190))
        surf.blit(banner, (0, 0))
        surf.blit(font.render(TITLE, True, PAL["cyan"]), (40, 18))
        surf.blit(small.render(HANDLE, True, PAL["magenta"]), (40, 88))
        sc = font.render(f"{self.score:05d}", True, PAL["white"])
        surf.blit(sc, (W - 48 - sc.get_width(), 18))
        meta = small.render(f"CUTS {self.cuts}", True, PAL["gold"])
        surf.blit(meta, (W - 48 - meta.get_width(), 90))
        foot = small.render("WASD / arrows steer   last ribbon standing", True, PAL["dim"])
        surf.blit(foot, foot.get_rect(center=(W * 0.5, H - 56)))


def record(path):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    pygame.font.init()
    surf = pygame.Surface((W, H))
    font = pygame.font.SysFont("DejaVu Sans", 58, bold=True)
    mid = pygame.font.SysFont("DejaVu Sans", 48, bold=True)
    small = pygame.font.SysFont("DejaVu Sans", 34, bold=True)
    g = Game(auto=True)
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    frames = FPS * 15
    try:
        for _ in range(frames):
            g.step()
            g.draw(surf, font, small, mid)
            proc.stdin.write(pygame.image.tostring(surf, "RGB"))
        proc.stdin.close()
        err = proc.stderr.read()
        rc = proc.wait(timeout=60)
    except Exception:
        proc.kill()
        raise
    if rc != 0:
        raise RuntimeError(err.decode("utf-8", "ignore")[-800:])
    print("wrote", path)


def play():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("DejaVu Sans", 58, bold=True)
    mid = pygame.font.SysFont("DejaVu Sans", 48, bold=True)
    small = pygame.font.SysFont("DejaVu Sans", 34, bold=True)
    g = Game(auto=False)
    run = True
    while run:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                run = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                run = False
        g.step(pygame.key.get_pressed())
        g.draw(screen, font, small, mid)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--record", action="store_true")
    p.add_argument("--play", action="store_true")
    p.add_argument("--out", default="/home/workdir/artifacts/COBALT_WAKE_ElbowOS.mp4")
    a = p.parse_args()
    if a.record or not a.play:
        record(a.out)
        if a.play:
            play()
    else:
        play()


if __name__ == "__main__":
    main()
