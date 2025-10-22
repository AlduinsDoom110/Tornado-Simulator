"""Interactive tornado simulator with EF level toggles and rich visuals."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, Tuple

import pygame


# --- Configuration -----------------------------------------------------------------
WIDTH, HEIGHT = 960, 720
FPS = 60

SKY_TOP = (16, 24, 48)
SKY_BOTTOM = (90, 140, 200)
GROUND_TOP = (40, 80, 30)
GROUND_BOTTOM = (12, 40, 18)

CENTER_X = WIDTH // 2
GROUND_Y = int(HEIGHT * 0.85)
MAX_TORNADO_HEIGHT = int(HEIGHT * 0.75)
PARTICLES_PER_LEVEL = 220

EF_LEVELS: Dict[str, Dict[str, float]] = {
    "EF0": {"swirl": 1.2, "lift": 120.0, "base_radius": 130.0, "debris": 0.12, "color": (180, 200, 220)},
    "EF1": {"swirl": 1.6, "lift": 160.0, "base_radius": 155.0, "debris": 0.18, "color": (190, 210, 230)},
    "EF2": {"swirl": 2.2, "lift": 200.0, "base_radius": 180.0, "debris": 0.26, "color": (210, 220, 230)},
    "EF3": {"swirl": 2.9, "lift": 240.0, "base_radius": 210.0, "debris": 0.35, "color": (230, 230, 235)},
    "EF4": {"swirl": 3.6, "lift": 300.0, "base_radius": 240.0, "debris": 0.47, "color": (245, 240, 230)},
    "EF5": {"swirl": 4.5, "lift": 360.0, "base_radius": 280.0, "debris": 0.60, "color": (255, 250, 220)},
}

FONT_NAME = "freesansbold.ttf"


# --- Utility functions -------------------------------------------------------------
def lerp(color_a: Tuple[int, int, int], color_b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return (
        int(color_a[0] + (color_b[0] - color_a[0]) * t),
        int(color_a[1] + (color_b[1] - color_a[1]) * t),
        int(color_a[2] + (color_b[2] - color_a[2]) * t),
    )


def draw_vertical_gradient(surface: pygame.Surface, top_color: Tuple[int, int, int], bottom_color: Tuple[int, int, int]) -> None:
    for y in range(surface.get_height()):
        t = y / surface.get_height()
        color = lerp(top_color, bottom_color, t)
        pygame.draw.line(surface, color, (0, y), (surface.get_width(), y))


def draw_radial_glow(surface: pygame.Surface, center: Tuple[int, int], radius: int, color: Tuple[int, int, int], alpha: int) -> None:
    glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -1):
        glow_alpha = int(alpha * (r / radius) ** 2)
        pygame.draw.circle(glow, (*color, glow_alpha), (radius, radius), r)
    surface.blit(glow, (center[0] - radius, center[1] - radius), special_flags=pygame.BLEND_PREMULTIPLIED)


# --- Data classes ------------------------------------------------------------------
@dataclass
class Particle:
    radius_seed: float
    altitude: float
    angle: float
    swirl_variation: float
    brightness: float

    @classmethod
    def random(cls) -> "Particle":
        return cls(
            radius_seed=random.uniform(0.2, 1.0),
            altitude=random.uniform(0.0, MAX_TORNADO_HEIGHT),
            angle=random.uniform(0.0, math.tau),
            swirl_variation=random.uniform(0.6, 1.4),
            brightness=random.uniform(0.5, 1.0),
        )

    def update(self, dt: float, swirl_speed: float, lift_speed: float, base_radius: float) -> None:
        self.angle += swirl_speed * dt * self.swirl_variation
        self.altitude += lift_speed * dt * (0.4 + 0.6 * self.radius_seed)
        if self.altitude > MAX_TORNADO_HEIGHT:
            self.altitude -= MAX_TORNADO_HEIGHT
            self.angle = random.uniform(0.0, math.tau)
            self.radius_seed = random.uniform(0.2, 1.0)
            self.brightness = random.uniform(0.5, 1.0)

    def project(self, base_radius: float) -> Tuple[int, int, float]:
        height_ratio = self.altitude / MAX_TORNADO_HEIGHT
        radius = lerp_radius(self.radius_seed, base_radius, height_ratio)
        x = CENTER_X + math.cos(self.angle) * radius
        y = GROUND_Y - self.altitude
        size = max(1, int(4 * (1 - height_ratio) + 1))
        return int(x), int(y), size


def lerp_radius(seed: float, base_radius: float, height_ratio: float) -> float:
    neck_ratio = 0.05 + 0.35 * (1 - seed)
    width = base_radius * (1 - height_ratio) ** (0.4 + neck_ratio)
    return width * (0.6 + 0.4 * seed)


@dataclass
class Debris:
    x: float
    y: float
    velocity_x: float
    velocity_y: float
    lifetime: float

    @classmethod
    def spawn(cls) -> "Debris":
        angle = random.uniform(0, math.tau)
        speed = random.uniform(80, 220)
        return cls(
            x=CENTER_X + math.cos(angle) * random.uniform(10, 80),
            y=GROUND_Y - random.uniform(5, 20),
            velocity_x=math.cos(angle) * speed,
            velocity_y=-random.uniform(30, 160),
            lifetime=random.uniform(0.6, 1.4),
        )

    def update(self, dt: float) -> None:
        self.velocity_y += 220 * dt
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        self.lifetime -= dt


# --- Simulator ---------------------------------------------------------------------
class TornadoSimulator:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Tornado Simulator")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(FONT_NAME, 36)
        self.font_small = pygame.font.Font(FONT_NAME, 20)

        self.particles = [Particle.random() for _ in range(PARTICLES_PER_LEVEL)]
        self.debris_particles: list[Debris] = []
        self.level_names = list(EF_LEVELS.keys())
        self.level_index = 2  # Default to EF2
        self.time = 0.0

        self.sky_surface = pygame.Surface((WIDTH, HEIGHT))
        draw_vertical_gradient(self.sky_surface, SKY_TOP, SKY_BOTTOM)
        self.ground_surface = pygame.Surface((WIDTH, HEIGHT - GROUND_Y))
        draw_vertical_gradient(self.ground_surface, GROUND_TOP, GROUND_BOTTOM)

    @property
    def current_level(self) -> Dict[str, float]:
        return EF_LEVELS[self.level_names[self.level_index]]

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            self.time += dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.level_index = (self.level_index + 1) % len(self.level_names)
                    elif pygame.K_0 <= event.key <= pygame.K_5:
                        self.level_index = min(event.key - pygame.K_0, len(self.level_names) - 1)

            self.update(dt)
            self.draw()

        pygame.quit()

    # --- Update & draw -------------------------------------------------------------
    def update(self, dt: float) -> None:
        level = self.current_level
        swirl = level["swirl"]
        lift = level["lift"]
        base_radius = level["base_radius"]
        debris_rate = level["debris"]

        for particle in self.particles:
            particle.update(dt, swirl, lift, base_radius)

        # Debris simulation near the ground for extra drama
        if random.random() < debris_rate:
            self.debris_particles.append(Debris.spawn())

        for debris in self.debris_particles[:]:
            debris.update(dt)
            if debris.lifetime <= 0 or debris.y > HEIGHT:
                self.debris_particles.remove(debris)

    def draw(self) -> None:
        level = self.current_level
        color = level["color"]
        swirl = level["swirl"]
        lift = level["lift"]

        self.screen.blit(self.sky_surface, (0, 0))
        self.draw_cloud_layer()
        self.draw_tornado_body(color)
        self.draw_particles(color)
        self.draw_debris()
        self.draw_ground()
        self.draw_overlay(swirl, lift)

        pygame.display.flip()

    # --- Rendering helpers ---------------------------------------------------------
    def draw_ground(self) -> None:
        self.screen.blit(self.ground_surface, (0, GROUND_Y))
        fog_surface = pygame.Surface((WIDTH, HEIGHT - GROUND_Y), pygame.SRCALPHA)
        for y in range(fog_surface.get_height()):
            alpha = int(120 * (1 - y / fog_surface.get_height()))
            pygame.draw.line(fog_surface, (120, 140, 130, alpha), (0, y), (WIDTH, y))
        self.screen.blit(fog_surface, (0, GROUND_Y))

    def draw_cloud_layer(self) -> None:
        cloud_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(8):
            phase = self.time * (0.2 + i * 0.03)
            offset = math.sin(phase) * 40
            y = 80 + i * 18 + math.cos(phase * 0.7) * 12
            color = (200 + i * 3, 210 + i * 4, 220 + i * 5, 30 + i * 8)
            pygame.draw.ellipse(cloud_surface, color, (offset - 160, y, WIDTH + 320, 120))
        self.screen.blit(cloud_surface, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)

    def draw_tornado_body(self, color: Tuple[int, int, int]) -> None:
        body_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for layer in range(40):
            t = layer / 40
            radius = lerp_radius(1 - t * 0.85, self.current_level["base_radius"], t)
            alpha = int(100 * (1 - t) ** 1.8)
            y = GROUND_Y - t * MAX_TORNADO_HEIGHT
            pygame.draw.ellipse(
                body_surface,
                (*color, alpha),
                (CENTER_X - radius, y - 30, radius * 2, 60),
            )
        body_surface = pygame.transform.smoothscale(body_surface, (WIDTH, HEIGHT))
        self.screen.blit(body_surface, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)

    def draw_particles(self, color: Tuple[int, int, int]) -> None:
        for particle in self.particles:
            x, y, size = particle.project(self.current_level["base_radius"])
            alpha = int(220 * particle.brightness)
            tone = lerp((60, 60, 70), color, particle.brightness)
            particle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surface, (*tone, alpha), (size, size), size)
            self.screen.blit(particle_surface, (x - size, y - size), special_flags=pygame.BLEND_PREMULTIPLIED)

        draw_radial_glow(self.screen, (CENTER_X, GROUND_Y - MAX_TORNADO_HEIGHT // 2), 220, color, 55)
        draw_radial_glow(self.screen, (CENTER_X, GROUND_Y), 260, (100, 120, 130), 60)

    def draw_debris(self) -> None:
        for debris in self.debris_particles:
            alpha = max(40, int(255 * min(1.0, debris.lifetime + 0.3)))
            size = max(2, int(4 - (debris.lifetime * 2)))
            color = (200, 180, 120, alpha)
            pygame.draw.circle(self.screen, color, (int(debris.x), int(debris.y)), size)

    def draw_overlay(self, swirl: float, lift: float) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (10, 12, 18, 140), (20, 20, 320, 150), border_radius=14)
        self.screen.blit(overlay, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)

        level_name = self.level_names[self.level_index]
        title_text = self.font_large.render(f"{level_name} Tornado", True, (230, 240, 255))
        stats_text = self.font_small.render(
            f"Swirl {swirl:.1f}x   Lift {lift:.0f}u/s   Debris {int(self.current_level['debris'] * 100)}%", True, (200, 210, 220)
        )
        hint_text = self.font_small.render("Press SPACE or 0-5 to change EF level", True, (180, 190, 200))

        self.screen.blit(title_text, (40, 40))
        self.screen.blit(stats_text, (40, 90))
        self.screen.blit(hint_text, (40, 130))


if __name__ == "__main__":
    TornadoSimulator().run()
