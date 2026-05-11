author = "Amir Zahavi"

import pygame


class MonsterSprite(pygame.sprite.Sprite):
    def __init__(self, frames, col, row, tile_size, map_rect):
        super().__init__()
        self.frames = frames
        self.tile_size = tile_size
        self.map_rect = map_rect
        self.anim_tick = 0
        self.anim_frame = 0
        # pixel position (for smooth movement)
        self.pixel_x = col * tile_size
        self.pixel_y = row * tile_size
        # target tile
        self.target_col = col
        self.target_row = row
        self.image = self.frames[0]
        self.rect = self.image.get_rect()
        self._update_rect()

    def _update_rect(self):
        self.rect.topleft = (
            self.map_rect.x + self.pixel_x,
            self.map_rect.y + self.pixel_y
        )

    def set_target(self, col, row):
        self.target_col = col
        self.target_row = row

    def update(self):
        SPEED = 4
        target_x = self.target_col * self.tile_size
        target_y = self.target_row * self.tile_size

        if self.pixel_x < target_x:
            self.pixel_x = min(self.pixel_x + SPEED, target_x)
        elif self.pixel_x > target_x:
            self.pixel_x = max(self.pixel_x - SPEED, target_x)
        if self.pixel_y < target_y:
            self.pixel_y = min(self.pixel_y + SPEED, target_y)
        elif self.pixel_y > target_y:
            self.pixel_y = max(self.pixel_y - SPEED, target_y)

        self.anim_tick += 1
        if self.anim_tick >= 8:
            self.anim_tick = 0
            self.anim_frame = (self.anim_frame + 1) % len(self.frames)
        self.image = self.frames[self.anim_frame]

        self._update_rect()