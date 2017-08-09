from collections import namedtuple
from enum import Enum
import math
import random
import pygame
import configparser

from pygame.rect import Rect

import client
import bson
from tile import Tileset
from level import Place
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
    def __init__(self, screen, map, network):
        self.screen = screen
        self.map = map
        self.ready = False
        self.is_centre = False
        self.size = (map_module.TILE_PIX_WIDTH, map_module.TILE_PIX_HEIGHT)
        self.step = 1
        self.cast_spells = []
        self.spell_limit = 50
        self.mute = 'True'
        self.tileset = Tileset(client.player_animation_tileset_path, (3, 4), (32, 32))
        self.name = ''
        self.x, self.y = (0, 0)
        self.animation_ticker = 0
        self.network = network

        self.particle_list = []
        self.particle_limit = 500

        self.steptime = 0
        self.can_step_ability = True
        
        self.firetime = 0
        self.can_fire_ability = True

        self.initial_position = map.level.get_place(Place.RED_SPAWN)

        self.set_position(self.initial_position)

        self.team = None

    def __raiseNoPosition(self):
        raise PlayerException({"message": "Player does not have a position set", "player": self})


    def save_to_config(self):
        config = configparser.ConfigParser()

        config['Player'] = {}
        config['Player']['name'] = self.name
        config['Player']['mute'] = str(self.mute)

        with open('player_save', 'w') as configfile:
            config.write(configfile)

        return

    def load_from_config(self):
        config = configparser.ConfigParser()
        config.read('player_save')

        if 'Player' in config:
            player_save_info = config['Player']
            self.network.node.set_header('NAME', self.name)
            self.set_name(player_save_info['name'])
            self.set_mute(player_save_info.get('mute', 'True'))
            return True

        return False

    def set_name(self, name, save = False):
        self.name = name
        if save:
            self.network.node.shout("player:name", bson.dumps(
                {
                    "name": self.name
                }
            ))
            self.save_to_config()

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
                name_tag_colour = (0, 191, 255)
            elif self.team == "red":
                name_tag_colour = (255, 0, 0)

        name_tag = font.render(self.name, False, name_tag_colour)

        centre = self.map.get_pixel_pos(self.x, self.y)

        name_tag_pos = (
            centre[0] + ((self.size[0] - (name_tag.get_width()+10)) // 2),
            centre[1] - ((self.size[1] + name_tag.get_height()) // 2)
        )

        rect = pygame.Surface((name_tag.get_width() + 10, name_tag.get_height()), pygame.SRCALPHA, 32)
        rect.fill((0,0,0, 160))
        self.screen.blit(rect, name_tag_pos)

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
        
        c = (255,255,255)
        if self.team:
            if self.team == "blue":
                c = (0, 0, 255)
            elif self.team == "red":
                c = (255, 0, 0)

        tmp_x = 0
        tmp_y = 0

        # while (can keep moving) and (x difference is not more than step) and (y difference is not more than step)
        while self.map.level.can_move_to(self.x + tmp_x, self.y + tmp_y) and abs(tmp_x) <= self.step and abs(tmp_y) <= self.step:
            self.add_particle(3,(self.x+tmp_x+ 0.5,self.y+tmp_y+0.9),c,3,None,(-tmp_x/5,-tmp_y/5),15,2,0.1)
            if direction == Movement.RIGHT:
                tmp_x += 1
            elif direction == Movement.LEFT:
                tmp_x -= 1

            if direction == Movement.UP:
                tmp_y -= 1
            elif direction == Movement.DOWN:
                tmp_y += 1

        if tmp_x != 0:
            tmp_x += (-1 if tmp_x > 0 else 1)
        if tmp_y != 0:
            tmp_y += (-1 if tmp_y > 0 else 1)


        self.set_position(Position(self.x + tmp_x, self.y + tmp_y))

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

    def add_particle(self,amount, position, colour=(255,255,255), size=3, velocity=None, gravity=(0,0), life=40, metadata=0,grow=0):
        for i in range(amount):        
            if(len(self.particle_list) > self.particle_limit):
                self.particle_list[0].destroy()
            self.particle_list.append(Particle(self, position, colour, size, velocity, gravity, life, metadata,grow))
        return
        
    def remove_particle(self,particle):
        self.particle_list.remove(particle)
        return

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
        self.player.add_particle(5,(self.x,self.y),self.colour,2,None,(self.velo_x*3,self.velo_y*3),40,0,0.1)
        del(self)

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
        for uuid, player in self.others.items():
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
            newPlayers[str(uuid)] = self.others.get(
                str(uuid),
                Player(self.me.screen, self.me.map, self.network)
            )

        self.others = newPlayers

    def all(self):
        return list(self.others.values()).push(self.me)

    def remove(self, uuid):
        if str(uuid) in self.others:
            del self.others[str(uuid)]

    def get(self, uuid):
        return self.others[str(uuid)]

class Particle():
    def __init__(self,player, position, colour=(255,255,255), size=3, velocity=None, gravity=(0,0), life=40, metadata=0, grow=0):
        self.player = player
        self.colour = colour
        self.size = size
        self.life = life
        self.maxlife = life
        self.meta = metadata
        self.grow = grow

        self.set_position(position)
        i = 1000
        if velocity != None:
            self.set_velocity(velocity)
        else:
            self.set_velocity((random.randrange(-i,i)/(i*40),random.randrange(-i,i)/(i*40)))
        self.set_gravity(gravity)
        
    def render(self):
        pixel_pos = self.player.map.get_pixel_pos(self.x,self.y)
        progress = self.life/self.maxlife
        #if progress <= self.fade:
            #self.alpha = int(self.startalpha*(progress*2))
        
        if self.life <= 0 :
            self.destroy()

        self.life -= 1

        #colour = (self.colour[0],self.colour[1],self.colour[2],self.alpha)

        self.rect = pygame.draw.circle(self.player.screen, self.colour, (int(pixel_pos[0]),int(pixel_pos[1])), int(self.size), self.meta)

        self.x += self.velo_x
        self.y += self.velo_y
        self.velo_x += self.grav_x
        self.velo_y += self.grav_y
        self.size += self.grow

    def set_position(self,position):
        self.x = position[0]
        self.y = position[1]
    def set_velocity(self, velocity):
        self.velo_x, self.velo_y = velocity
    def set_gravity(self, gravity):
        self.grav_x = gravity[0]/100
        self.grav_y = gravity[1]/100

    def destroy(self):
        self.player.remove_particle(self)
        del(self)
