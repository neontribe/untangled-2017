from collections import namedtuple
from enum import Enum
import math
import random
import pygame
import configparser
from pygame.rect import Rect

import client
from tile import Tileset
import map as map_module

class Movement(Enum):
    UP = 1
    RIGHT = 2
    DOWN = 3
    LEFT = 4
Position = namedtuple('Position', ['x', 'y'])
SpellProperties = namedtuple('SpellProperties', ['x', 'y', 'x_velocity', 'y_velocity',])

class Action(Enum):
    SPELL = 1
    SWIPE = 2

class PlayerException(Exception):
    pass

class Player():
    def __init__(self, screen, map, team):
        self.screen = screen
        self.map = map
        self.ready = False
        self.is_centre = False
        self.size = (map_module.TILE_PIX_WIDTH, map_module.TILE_PIX_HEIGHT)
        self.step = 1
        self.team = team
        self.cast_spells = []
        self.spell_limit = 50
        self.mute = 'True'
        self.tileset = Tileset(client.player_animation_tileset_path, (3, 4), (32, 32))
        self.name = ''
        self.x, self.y = (0, 0)
        self.initial_position = (0, 0)
        self.animation_ticker = 0
        self.set_position(self.initial_position)
        self.team = None

    def __raiseNoPosition(self):
        raise PlayerException({"message": "Player does not have a position set", "player": self})


    def save_to_config(self):
        config = configparser.ConfigParser()

        config['Player'] = {}
        config['Player']['name'] = self.name
        config['Player']['x'] = str(self.x)
        config['Player']['y'] = str(self.y)
        config['Player']['mute'] = str(self.mute)

        with open('player_save', 'w') as configfile:
            config.write(configfile)

        return

    def load_from_config(self):
        config = configparser.ConfigParser()
        config.read('player_save')

        if 'Player' in config:
            player_save_info = config['Player']

            self.set_name(player_save_info['name'])
            self.set_position(
                (
                    int(player_save_info['x']),
                    int(player_save_info['y'])
                )
            )
            self.set_mute(player_save_info.get('mute', 'True'))
            return True

        return False

    def set_name(self, name, save = False):
        self.name = name
        if save: self.save_to_config()

    def set_tileset(self, tileset):
        self.tileset = tileset

    def set_position(self, position):
        # Derive direction (for networked players)
        if self.x < position[0]:
            self.animation_ticker = self.tileset.find_id(self.x % 3, 2)
        elif self.x > position[0]:
            self.animation_ticker = self.tileset.find_id(self.x % 3, 1)

        if self.y < position[1]:
            self.animation_ticker = self.tileset.find_id(self.y % 3, 0)
        elif self.y > position[1]:
            self.animation_ticker = self.tileset.find_id(self.y % 3, 3)

        self.x, self.y = position
        self.ready = True

    def set_mute(self, mute, save = False):
        self.mute = mute
        if save: self.save_to_config()

    def render(self):
        font = pygame.font.Font(client.font, 30)

        name_tag_colour = (255, 255, 255)
        if self.team:
            if self.team == "blue":
                name_tag_colour = (0, 0, 255)
            elif self.team == "red":
                name_tag_colour = (255, 0, 0)

        name_tag = font.render(self.name, False, name_tag_colour)

        centre = self.map.get_pixel_pos(self.x, self.y)

        name_tag_pos = (
            centre[0] + ((self.size[0] - name_tag.get_width()) // 2),
            centre[1] - ((self.size[1] + name_tag.get_height()) // 2)
        )

        self.screen.blit(name_tag, name_tag_pos)

        sprite = self.tileset.get_surface_by_id(self.animation_ticker)
        self.screen.blit(sprite, centre)

        # create collision rectangle
        self.rect = sprite.get_rect()
        self.rect.topleft = centre

    def move(self, direction):
        if not self.ready:
            self.__raiseNoPosition()

        tmp_x = self.x
        tmp_y = self.y

        if direction == Movement.UP:
            tmp_y -= self.step
        elif direction == Movement.DOWN:
            tmp_y += self.step

        if direction == Movement.RIGHT:
            tmp_x += self.step
        elif direction == Movement.LEFT:
            tmp_x -= self.step

        if not self.map.level.can_move_to(tmp_x, tmp_y):
            return

        self.set_position(Position(tmp_x, tmp_y))

    def get_position(self):
        if not self.ready:
            self.__raiseNoPosition()

        return Position(self.x, self.y)

    def attack(self, action, direction,position=None):
        if action == Action.SPELL:
            if direction == Movement.UP:
                spell = Spell(self, (0, -0.25),position)
            elif direction == Movement.RIGHT:
                spell = Spell(self, (0.25, 0),position)
            elif direction == Movement.DOWN:
                spell = Spell(self, (0, 0.25),position)
            elif direction == Movement.LEFT:
                spell = Spell(self, (-0.25, 0),position)
            else:
                spell = Spell(self, direction,position)

            # Remove first element of list if limit reached.
            if len(self.cast_spells) > self.spell_limit:
                self.cast_spells[1:]
            self.cast_spells.append(spell)
        elif action == Action.SWIPE:
            #TODO
            return

    def remove_spell(self,spell):
        self.cast_spells.remove(spell)
        return

    def set_team(self, team):
        self.team = team

class Spell():
    def __init__(self, player, velocity, position=None, size=(0.25, 0.25), colour=(0,0,0), life=100):
        self.player = player
        self.size = size
        self.colour = colour
        self.life = life
        self.maxLife = life
        if position == None:
            # spawn at player - additional maths centres the spell
            self.x = self.player.x + 0.5 - (size[0] / 2)
            self.y = self.player.y + 0.5 - (size[1] / 2)
        else:
            self.set_position(position)

        self.set_velocity(velocity)

    def render(self):
        self.colour = (random.randrange(255),random.randrange(255),random.randrange(255))
        newSize = self.life/self.maxLife #random.randrange(100)/100
        self.size = (newSize,newSize)
        if(self.life <= 0):
            self.destroy()

        self.life -= 1

        pixel_pos = self.player.map.get_pixel_pos(self.x, self.y);
        pixel_size = (
            self.size[0] * map_module.TILE_PIX_WIDTH,
            self.size[1] * map_module.TILE_PIX_HEIGHT
        )
        offset_pos = (
            pixel_pos[0] - (pixel_size[0]/2),
            pixel_pos[1] - (pixel_size[1]/2)
        )
        self.rect = pygame.draw.rect(self.player.screen, self.colour, Rect(offset_pos, pixel_size))

        # move the projectile by its velocity
        self.x += self.velo_x
        self.y += self.velo_y

    #destroy the spell
    def destroy(self):
        self.player.remove_spell(self)

    def get_properties(self):
        return SpellProperties(self.x, self.y, self.velo_x, self.velo_y)

    def set_properties(self, properties):
        self.x, self.y, self.velo_x, self.velo_y = properties

    def set_position(self, position):
        self.x = position[0] + 0.5 - (self.size[0] / 2)
        self.y = position[1] + 0.5 - (self.size[1] / 2)

    def set_velocity(self, velocity):
        self.velo_x, self.velo_y = velocity

    def hit_target(self, target):
        if self.rect.colliderect(target.rect):
            # TODO - decide on what to do with collision
            pass

class PlayerManager():
    def __init__(self, me, network):
        self.me = me
        self.network = network
        self.me.load_from_config()
        self.others = {}
        self.authority_uuid = ''

    def set_teams(self, teams):
        blue_team = teams.get('blue')
        red_team = teams.get('red')

        # Set team for current player
        self_uuid = str(self.network.node.uuid())

        if self_uuid in blue_team:
            self.me.set_team("blue")
        elif self_uuid in red_team:
            self.me.set_team("red")

        # Set teams for other players
        for uuid, player in self.others:
            str_uuid = str(uuid)
            if str_uuid in blue_team:
                player.set_team("blue")
            elif str_uuid in red_team:
                player.set_team("red")


    def set(self, players):
        newPlayers = {}
        for uuid in players:
            if str(uuid) == self.authority_uuid:
                continue

            random.seed(str(uuid))
            newPlayers[str(uuid)] = self.others.get(str(uuid), Player(self.me.screen, self.me.map, 0))
        self.others = newPlayers
        # print(self.others)

    def all(self):
        return list(self.others.values()).push(self.me)

    def remove(self, uuid):
        if str(uuid) in self.others:
            del self.others[str(uuid)]

    def get(self, uuid):
        return self.others[str(uuid)]
