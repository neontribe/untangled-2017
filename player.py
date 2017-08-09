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
    def __init__(self, screen, map, network, health=100, mana=100):
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
        
        self.health = health
        self.mana = mana
        self.maxMana = mana

    def __raiseNoPosition(self):
        raise PlayerException({"message": "Everything is lava: Player does not have a position set", "player": self})


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

    def hudRender(self):
        font = pygame.font.Font(client.font, 30)
        mana = font.render("Mana: "+str(self.mana)+"/100", False, (255,255,255))
        health = font.render("Health: "+str(self.health)+"/100", False, (255,255,255))
        rect = pygame.Surface((health.get_width() + 15, 50), pygame.SRCALPHA, 32)
        rect.fill((0,0,0, 255))
        self.screen.blit(rect, (0,0))
        self.screen.blit(mana, (10,0))
        self.screen.blit(health, (10,25))

    def render(self, isMe = False):
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

        self.render_particles()
        
        if isMe:
            self.hudRender()

    def render_particles(self):
        toRemove = []
        for particle in self.particle_list:
            pixel_pos = self.map.get_pixel_pos(particle["position"][0],particle["position"][1])
        
            if particle["life"] <= 0:
                toRemove.append(particle)

            particle["life"] -= 1

            pygame.draw.circle(self.screen, particle["colour"], (int(pixel_pos[0]),int(pixel_pos[1])), int(particle["size"]), particle["metadata"])

            particle["position"] = (particle["position"][0] + particle["velocity"][0],particle["position"][1] + particle["velocity"][1])
            particle["velocity"] = (particle["velocity"][0] + particle["gravity"][0], particle["velocity"][1] + particle["gravity"][1])
            particle["size"] += particle["grow"]

        for p in toRemove:
            self.remove_particle(p)

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
            #               amount,    position,              colour,size,velocity,gravity,life,metadata,grow
            self.add_particle(3,(self.x+tmp_x+ 0.5,self.y+tmp_y+0.9),c,3,None,(-tmp_x/1000,-tmp_y/1000),5,2,0.1)
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

    def attack(self, action, direction, image, position=None):
        if action == Action.SPELL:
            if len(self.cast_spells) > self.spell_limit:
                self.cast_spells[1:]
            if self.mana >= 5:
                self.depleatMana(5)
                if direction == Movement.UP:
                    spell = Spell(self, (0, -0.25), image, position)
                    self.cast_spells.append(spell)
                elif direction == Movement.RIGHT:
                    spell = Spell(self, (0.25, 0), image, position)
                    self.cast_spells.append(spell)
                elif direction == Movement.DOWN:
                    spell = Spell(self, (0, 0.25), image, position)
                    self.cast_spells.append(spell)
                elif direction == Movement.LEFT:
                    spell = Spell(self, (-0.25, 0), image, position)
                    self.cast_spells.append(spell)
                else:
                    spell = Spell(self, direction, image, position)
                # Remove first element of list if limit reached.
                if len(self.cast_spells) > self.spell_limit:
                    self.cast_spells[1:]
                self.cast_spells.append(spell)
                return True
            else:
                return False
        elif action == Action.SWIPE:
            #TODO
            return False
        return False

    def remove_spell(self,spell):
        self.cast_spells.remove(spell)
        return

    def set_team(self, team):
        self.team = team

    def add_particle(self,amount, position, colour=(255,255,255), size=3, velocity=None, gravity=(0,0), life=40, metadata=0,grow=0):
        for i in range(amount):        
            if(len(self.particle_list) >= self.particle_limit):
                self.particle_list[0].destroy()
            newParticle = {"position":position, "velocity":velocity, "gravity":gravity, "colour":colour, "size":size, "life":life, "metadata":metadata, "grow":grow}
            i = 1000
            if velocity != None:
                newParticle["velocity"] = velocity
            else:
                newParticle["velocity"] = (random.randrange(-i,i)/(i*10),random.randrange(-i,i)/(i*10))
            self.particle_list.append(newParticle)

    def remove_particle(self,particle):
        self.particle_list.remove(particle)
        return
        
    def depleatHealth(self, amount):
        self.health -= amount
        if self.health < 0:
            self.die()
            
    def die(self): # Don't get confused with `def` and `death`!!! XD
        pass
    
    def addMana(self, amount):
        self.mana += amount
    
    def depleatMana(self, amount):
        self.mana -= amount

class Spell():
    def __init__(self, player, velocity, image, position=None, size=(0.1, 0.1), colour=(0,0,0), life=100):
        self.player = player
        self.image = image
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

        self.image = pygame.image.load(image)

    def render(self):
        self.colour = (random.randrange(255),random.randrange(255),random.randrange(255))
        progress = self.life/self.maxLife #random.randrange(100)/100
        newSize = (progress*self.size[0],progress*self.size[1])
        if(self.life <= 0):
            self.destroy()

        self.life -= 1

        # Complicated mathmatical equations
        image_size = self.image.get_size()
        newImageSize = (
            int(image_size[0]*newSize[0]),
            int(image_size[1]*newSize[1])
        )
        # Look at all this math!
        newRotation = round(math.atan2(self.velo_x,self.velo_y)*(180/math.pi)-180,4)


        pixel_pos = self.player.map.get_pixel_pos(self.x, self.y);
        offset_pos = (
            pixel_pos[0] - (newImageSize[0]/2),
            pixel_pos[1] - (newImageSize[1]/2)
        )

        surf = pygame.transform.scale(self.image, newImageSize)
        if newImageSize[0] != 0 and newImageSize[1] != 0:
            surf = pygame.transform.rotate(surf, newRotation)
        self.player.screen.blit(surf, offset_pos)

        # move the projectile by its velocity
        self.x += self.velo_x
        self.y += self.velo_y


    #destroy the spell
    def destroy(self):
        self.player.remove_spell(self)
        #self.player.add_particle(5,(self.x,self.y),self.colour,2,None,(self.velo_x*3,self.velo_y*3),40,0,0.1)
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

    # def hit_target(self, target):
    #     if self.rect.colliderect(target.rect):
    #         # TODO - decide on what to do with collision
    #         pass

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
