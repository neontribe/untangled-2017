import pygame
from pygame import Rect
import math
import random
import time
from lib.system import System
from game.components import *
from game.systems.userinputsystem import get_position

class AnimalSystem(System):
    def update(self, game, dt: float, events: list):
        # Find and get the tilemap, if it exists
        tmap = None
        for key, entity in game.entities.items():
            if Map in entity and SpriteSheet in entity:
                tmap = entity
                break

        for key, entity in game.entities.items():
            if MoveRandom in entity:
                if time.time() - entity[MoveRandom].lastmove >= entity[MoveRandom].movetime:
                    direct = ['left', 'right', 'up', 'down','default','default','default']
                    dire = random.choice(direct)
                    if Directioned in entity:
                        if not entity[Directioned].isOnlyLR:
                            entity[Directioned].direction = dire
                        else:
                            if dire != 'up' and dire != 'down':
                                entity[Directioned].direction = dire
                    entity[MoveRandom].lastmove = time.time()
                    entity[MoveRandom].movetime = random.uniform(0.2,3)
                else:
                    velo = {
                        'default': (0,0),
                        'left': (-1, 0),
                        'right': (1, 0),
                        'up': (0, 1),
                        'down': (0, -1)
                    }[entity[Directioned].direction]
                    animal_center = get_position(entity[IngameObject], velo, tmap)
                    entity[IngameObject].position = animal_center

                    if SpriteSheet in entity:
                        entity[SpriteSheet].moving = True
                    