import os
import random
import math
import pygame
from os import listdir
from os.path import isfile, join
pygame.init()
pygame.mixer.init()

pygame.display.set_caption("Ninja Frog")

WIDTH, HEIGHT = 1000, 800
FPS = 60
PLAYER_VEL = 5

window = pygame.display.set_mode((WIDTH, HEIGHT))
die_sound = pygame.mixer.Sound(os.path.join("assets", "Sounds", "die.mp3"))

def flip(sprites):
  return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


def load_sprite_sheets(dir1, dir2, width, height, direction=False):
  path = join("assets", dir1, dir2)
  images = [f for f in listdir(path) if isfile(join(path, f))]

  all_sprites = {}

  for image in images:
      sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()

      sprites = []
      for i in range(sprite_sheet.get_width() // width):
          surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
          rect = pygame.Rect(i * width, 0, width, height)
          surface.blit(sprite_sheet, (0, 0), rect)
          sprites.append(pygame.transform.scale2x(surface))

      if direction:
          all_sprites[image.replace(".png", "") + "_right"] = sprites
          all_sprites[image.replace(".png", "") + "_left"] = flip(sprites)
      else:
          all_sprites[image.replace(".png", "")] = sprites

  return all_sprites


def get_block(size):
  path = join("assets", "Terrain", "Terrain.png")
  image = pygame.image.load(path).convert_alpha()
  surface = pygame.Surface((size, size), pygame.SRCALPHA, 16)
  rect = pygame.Rect(96, 0, size, size)
  # rect = pygame.Rect(0, 0, size, size)
  surface.blit(image, (0, 0), rect)
  return pygame.transform.scale2x(surface)


class Player(pygame.sprite.Sprite):
  COLOR = (255, 0, 0)
  GRAVITY = 1
  SPRITES = load_sprite_sheets("MainCharacters", "NinjaFrog", 32, 32, True)
  ANIMATION_DELAY = 3

  def __init__(self, x, y, width, height):
      super().__init__()
      self.rect = pygame.Rect(x, y, width, height)
      self.x_vel = 0
      self.y_vel = 0
      self.mask = None
      self.direction = "left"
      self.animation_count = 0
      self.fall_count = 0
      self.jump_count = 0
      self.hit = False
      self.hit_count = 0

  def jump(self):
      self.y_vel = -self.GRAVITY * 8
      self.animation_count = 0
      self.jump_count += 1
      if self.jump_count == 1:
          self.fall_count = 0

  def move(self, dx, dy):
      self.rect.x += dx
      self.rect.y += dy

  def make_hit(self):
      self.hit = True

  def move_left(self, vel):
      self.x_vel = -vel
      if self.direction != "left":
          self.direction = "left"
          self.animation_count = 0

  def move_right(self, vel):
      self.x_vel = vel
      if self.direction != "right":
          self.direction = "right"
          self.animation_count = 0

  def loop(self, fps):
      self.y_vel += min(1, (self.fall_count / fps) * self.GRAVITY)
      self.move(self.x_vel, self.y_vel)

      if self.hit:
          self.hit_count += 1
      if self.hit_count > fps * 2:
          self.hit = False
          self.hit_count = 0

      self.fall_count += 1
      self.update_sprite()

  def landed(self):
      self.fall_count = 0
      self.y_vel = 0
      self.jump_count = 0

  def hit_head(self):
      self.count = 0
      self.y_vel *= -1

  def update_sprite(self):
      sprite_sheet = "idle"
      if self.hit:
          sprite_sheet = "hit"
      elif self.y_vel < 0:
          if self.jump_count == 1:
              sprite_sheet = "jump"
          elif self.jump_count == 2:
              sprite_sheet = "double_jump"
      elif self.y_vel > self.GRAVITY * 2:
          sprite_sheet = "fall"
      elif self.x_vel != 0:
          sprite_sheet = "run"

      sprite_sheet_name = sprite_sheet + "_" + self.direction
      sprites = self.SPRITES[sprite_sheet_name]
      sprite_index = (self.animation_count //
                      self.ANIMATION_DELAY) % len(sprites)
      self.sprite = sprites[sprite_index]
      self.animation_count += 1
      self.update()

  def update(self):
      self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
      self.mask = pygame.mask.from_surface(self.sprite)

  def draw(self, win, offset_x):
      win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))


class Object(pygame.sprite.Sprite):
  def __init__(self, x, y, width, height, name=None):
      super().__init__()
      self.rect = pygame.Rect(x, y, width, height)
      self.image = pygame.Surface((width, height), pygame.SRCALPHA)
      self.width = width
      self.height = height
      self.name = name

  def draw(self, win, offset_x):
      win.blit(self.image, (self.rect.x - offset_x, self.rect.y))


class Block(Object):
  def __init__(self, x, y, size):
      super().__init__(x, y, size, size)
      block = get_block(size)
      self.image.blit(block, (0, 0))
      self.mask = pygame.mask.from_surface(self.image)


class Fire(Object):
  ANIMATION_DELAY = 3

  def __init__(self, x, y, width, height):
      super().__init__(x, y, width, height, "fire")
      self.fire = load_sprite_sheets("Traps", "Fire", width, height)
      self.image = self.fire["off"][0]
      self.mask = pygame.mask.from_surface(self.image)
      self.animation_count = 0
      self.animation_name = "off"

  def on(self):
      self.animation_name = "on"

  def off(self):
      self.animation_name = "off"

  def loop(self):
      sprites = self.fire[self.animation_name]
      sprite_index = (self.animation_count //
                      self.ANIMATION_DELAY) % len(sprites)
      self.image = sprites[sprite_index]
      self.animation_count += 1

      self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
      self.mask = pygame.mask.from_surface(self.image)

      if self.animation_count // self.ANIMATION_DELAY > len(sprites):
          self.animation_count = 0


class Fruit(Object):
    ANIMATION_DELAY = 3
    collect_sound = pygame.mixer.Sound("assets/Sounds/collect.mp3")

    def __init__(self, x, y):
        super().__init__(x, y - 4, 32, 32, "fruit")  # Y axis moved up by 4px
        self.apple_sheet = pygame.image.load("assets/Items/Fruits/Apple.png").convert_alpha()
        self.collected_sheet = pygame.image.load("assets/Items/Fruits/Collected.png").convert_alpha()

        # Load apple frames
        self.apple_frames = []
        for i in range(self.apple_sheet.get_width() // 32):
            surface = pygame.Surface((32, 32), pygame.SRCALPHA)
            rect = pygame.Rect(i * 32, 0, 32, 32)
            surface.blit(self.apple_sheet, (0, 0), rect)
            self.apple_frames.append(pygame.transform.scale2x(surface))

        # Load collected frames
        self.collected_frames = []
        for i in range(self.collected_sheet.get_width() // 32):
            surface = pygame.Surface((32, 32), pygame.SRCALPHA)
            rect = pygame.Rect(i * 32, 0, 32, 32)
            surface.blit(self.collected_sheet, (0, 0), rect)
            self.collected_frames.append(pygame.transform.scale2x(surface))

        self.animation_count = 0
        self.collected = False
        self.played_sound = False
        self.finished_collected_animation = False
        self.mask = pygame.mask.from_surface(self.apple_frames[0])

    def loop(self):
        if self.finished_collected_animation:
            return  # Do nothing if collected animation has finished

        if not self.collected:
            frame_index = (self.animation_count // self.ANIMATION_DELAY) % len(self.apple_frames)
            self.image = self.apple_frames[frame_index]
        else:
            if not self.played_sound:
                Fruit.collect_sound.play()
                self.played_sound = True
            frame_index = self.animation_count // self.ANIMATION_DELAY
            if frame_index < len(self.collected_frames):
                self.image = self.collected_frames[frame_index]
            else:
                self.finished_collected_animation = True
                return

        self.animation_count += 1
        self.rect = self.image.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.image)

    def draw(self, win, offset_x):
        if not self.finished_collected_animation:
            win.blit(self.image, (self.rect.x - offset_x, self.rect.y))


class Checkpoint(Object):
    def __init__(self, x, y):
        # 64x64 source image, display as 32x32
        super().__init__(x, y, 64, 64, "checkpoint")
        original_image = pygame.image.load("assets/Items/Checkpoints/End/End (Idle).png").convert_alpha()

        # Scale down to 32x32
        self.image = pygame.transform.scale(original_image, (128, 128))
        self.mask = pygame.mask.from_surface(self.image)


def get_background(name):
  image = pygame.image.load(join("assets", "Background", name))
  _, _, width, height = image.get_rect()
  tiles = []

  for i in range(WIDTH // width + 1):
      for j in range(HEIGHT // height + 1):
          pos = (i * width, j * height)
          tiles.append(pos)

  return tiles, image

def draw(window, background, bg_image, player, objects, offset_x, level_img, fires, fruits, checkpoints):
    for tile in background:
        window.blit(bg_image, tile)

    for obj in objects:
        obj.draw(window, offset_x)

    for fire in fires:
        fire.draw(window, offset_x)
    
    for fruit in fruits:
        fruit.draw(window, offset_x)
    
    for checkpoint in checkpoints:
        checkpoint.draw(window, offset_x)

    player.draw(window, offset_x)

    level_rect = level_img.get_rect(midtop=(WIDTH // 2, 20))
    window.blit(level_img, level_rect)

    pygame.display.update()


def win_screen(win):
    font_path = os.path.join("assets", "fonts", "RetroGaming.ttf")

    # Large "YOU WIN" text
    title_font = pygame.font.Font(font_path, 80)
    title_text = title_font.render("YOU WIN", True, (255, 255, 0))
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40))

    # Smaller "Press SPACE to play again" text
    subtitle_font = pygame.font.Font(font_path, 30)
    subtitle_text = subtitle_font.render("Press SPACE to play again", True, (255, 255, 255))
    subtitle_rect = subtitle_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 150))

    # Draw screen
    win.fill((0, 0, 0))
    win.blit(title_text, title_rect)
    win.blit(subtitle_text, subtitle_rect)
    pygame.display.update()

    # Wait for spacebar to restart
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    waiting = False


def handle_vertical_collision(player, objects, dy):
  collided_objects = []
  for obj in objects:
      if pygame.sprite.collide_mask(player, obj):
          if dy > 0:
              player.rect.bottom = obj.rect.top
              player.landed()
          elif dy < 0:
              player.rect.top = obj.rect.bottom
              player.hit_head()

          collided_objects.append(obj)

  return collided_objects


def collide(player, objects, dx):
  player.move(dx, 0)
  player.update()
  collided_object = None
  for obj in objects:
      if pygame.sprite.collide_mask(player, obj):
          collided_object = obj
          break

  player.move(-dx, 0)
  player.update()
  return collided_object


def handle_move(player, objects):
  keys = pygame.key.get_pressed()

  player.x_vel = 0
  collide_left = collide(player, objects, -PLAYER_VEL * 2)
  collide_right = collide(player, objects, PLAYER_VEL * 2)

  if keys[pygame.K_LEFT] and not collide_left:
      player.move_left(PLAYER_VEL)
  if keys[pygame.K_RIGHT] and not collide_right:
      player.move_right(PLAYER_VEL)

  vertical_collide = handle_vertical_collision(player, objects, player.y_vel)
  to_check = [collide_left, collide_right, *vertical_collide]

  for obj in to_check:
      if obj and obj.name == "fire":
          player.make_hit()

def game_over_screen(win):
    font_path = os.path.join("assets", "fonts", "RetroGaming.ttf")

    # Large "GAME OVER" text
    title_font = pygame.font.Font(font_path, 80)
    title_text = title_font.render("GAME OVER", True, (255, 0, 0))
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40))

    # Smaller instruction text
    subtitle_font = pygame.font.Font(font_path, 30)
    subtitle_text = subtitle_font.render("Press SPACE to play again", True, (255, 255, 255))
    subtitle_rect = subtitle_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 150))

    # Clear screen and draw texts
    win.fill((0, 0, 0))
    win.blit(title_text, title_rect)
    win.blit(subtitle_text, subtitle_rect)
    pygame.display.update()

    # Wait for SPACE key press to restart
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    waiting = False

def generate_fixed_platform_course(block_size):
    blocks = []
    fires = []
    fruits = []
    checkpoints = []

    # Ground platform
    num_ground_blocks = (WIDTH * 2) // block_size
    for i in range(-WIDTH // block_size, num_ground_blocks):
        x = i * block_size
        y = HEIGHT - block_size
        blocks.append(Block(x, y, block_size))

    # Floating platforms
    platform_layout = [
        (-11,2,1), (-11,3,1), (-11,4,1), (-11,5,1),
        (-11,6,1), (-11,7,1), (-11,8,1), (-11,9,1),
        (0,2,1),
        (6, 5, 2), (10, 4, 3), (15, 2, 3), (15, 3, 2), 
        (20, 1, 4), (23, 2, 1), (23, 3, 1), (20, 4, 4),
        (29, 2, 1), (30, 3, 1), (31, 4, 1),
        (26, 5, 3), (31, 4, 2), (35, 1, 1), (35, 2, 1), 
        (35, 3, 1), (37, 1, 1), (37, 2, 1), (37, 3, 1), 
        (39, 1, 1), (39, 2, 1), (39, 3, 1),
        (41, 1, 1), (41, 2, 1), (41, 3, 1),(41, 4, 1),
        (45, 5, 4), (52, 4, 2), (56, 3, 3), (61, 4, 2),
        (66, 5, 3), (71, 4, 2), (75, 3, 4), (81, 4, 2),
        (86, 5, 3), (91, 4, 2), (95, 3, 3), (100, 4, 2),
        (102, 4, 1), (102, 5, 1), (102, 6, 1), (102, 7, 1),
        (102, 8, 1), (102, 9, 1),
    ]
    for start_x_index, tier, length in platform_layout:
        y = HEIGHT - block_size * tier
        for i in range(length):
            x = (start_x_index + i) * block_size
            blocks.append(Block(x, y, block_size))

    # Fire layout: (x_block_index, tier)
    fire_layout = [
        (1,2), (6,6), (12, 2), (22, 5)
    ]
    for x_index, tier in fire_layout:
        x = x_index * block_size + (block_size - 16) // 2  # center horizontally
        y = HEIGHT - block_size * tier + 32  # position on top of block
        fire = Fire(x, y, 16, 32)
        fire.on()
        fires.append(fire)
    
    # Example fruit positions
    fruit_positions = [
        (7,6), (14, 1), (11,5), (11,6), (12,5), (12,6), (20,1), (20,2), (21,1), (21,2), (22,1), (22,2), (31,2), (32, 2), (55, 2), (95, 2)
    ]

    for x_block, tier in fruit_positions:
        x = x_block * block_size + (block_size - 32) // 2 - 16
        y = HEIGHT - block_size * tier - 32 - 32
        fruits.append(Fruit(x, y))

        # Checkpoint positions: (x_block_index, tier)
    checkpoint_positions = [
        (101, 5)
    ]

    for x_index, tier in checkpoint_positions:
        x = x_index * block_size - 16
        y = HEIGHT - block_size * tier - 32
        checkpoints.append(Checkpoint(x, y))

    return blocks, fires, fruits, checkpoints


def main(window):
  clock = pygame.time.Clock()
  background, bg_image = get_background("Yellow.png")

  # Load and scale the level image
  level_image = pygame.image.load(os.path.join("assets", "Menu", "Levels", "01.png")).convert_alpha()

  # Scale the image to desired size (e.g., double the original)
  level_image = pygame.transform.scale(level_image, (80, 80))

  block_size = 96

#   player = Player(100, 100, 50, 50)
  floor = [Block(i * block_size, HEIGHT - block_size, block_size)
            for i in range(-WIDTH // block_size, (WIDTH * 2) // block_size)]
  objects, fires, fruits, checkpoints = generate_fixed_platform_course(block_size)
  spawn_x = 2 * block_size
  spawn_y = HEIGHT - block_size * 2  # one block above ground
  player = Player(spawn_x, spawn_y, 50, 50)

  offset_x = 0
  scroll_area_width = 200

  run = True
  while run:
      clock.tick(FPS)

      for event in pygame.event.get():
          if event.type == pygame.QUIT:
              run = False
              break

          if event.type == pygame.KEYDOWN:
              if event.key == pygame.K_SPACE and player.jump_count < 2:
                  player.jump()

      player.loop(FPS)

      for fire in fires:
        fire.loop()

      # Check fire collisions
      for fire in fires:
        if pygame.sprite.collide_mask(player, fire):
            player.make_hit()
            break  # avoid hitting repeatedly in same frame
    
      for fruit in fruits:
        fruit.loop()
        if not fruit.collected and pygame.sprite.collide_mask(player, fruit):
            fruit.collected = True
            fruit.animation_count = 0

      handle_move(player, objects)
      draw(window, background, bg_image, player, objects, offset_x, level_image, fires, fruits, checkpoints)

      if player.rect.top > HEIGHT:
        die_sound.play()
        game_over_screen(window)
        main(window)  # Restart game
        return        # Exit current loop

      for checkpoint in checkpoints:
        if pygame.sprite.collide_mask(player, checkpoint):
            win_screen(window)
            main(window)  # Restart game
            return        # Exit the current run

      if ((player.rect.right - offset_x >= WIDTH - scroll_area_width) and player.x_vel > 0) or (
              (player.rect.left - offset_x <= scroll_area_width) and player.x_vel < 0):
          offset_x += player.x_vel

  pygame.quit()
  quit()


if __name__ == "__main__":
  main(window)
