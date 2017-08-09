import pygame
import pygame.locals
import socket
import select
import random
import time
import logging
import zmq
import pdb
import bson
import uuid
import webbrowser
from pyre import Pyre, pyre_event
from pyre import zhelper
from collections import namedtuple
from enum import Enum

from map import *
from network import Network
from player import *
from flag import *
from screen import MainMenu
from level import SaveLevel
from tile import Tileset
from music import LevelMusic

white = (255,255,255)
black = (0,0,0)
red = (255, 0, 0)

width = 1024
height = 1024

font = 'assets/fonts/alterebro-pixel-font.ttf'
level_tileset_path = 'assets/tilesets/main.png'
player_animation_tileset_path = 'assets/tilesets/player.png'

class GameState(Enum):
    MENU = 0
    PLAY = 1
    HELP = 2
    CHARACTER = 3
    QUIT = 4
    MUTE = 5

class GameClient():
    game_state = GameState.MENU

    def __init__(self):
        self.network = Network()
        self.setup_pygame()
        me = Player(self.screen, self.map, self.network)

        self.players = PlayerManager(me, self.network)
        self.flags = [Flag(self.screen, self.map, "red"), Flag(self.screen, self.map, "blue")]
        self.map.set_centre_player(self.players.me)
        self.menu = MainMenu(self.screen, self.players)

    def setup_pygame(self):
        # Initialise screen/display
        self.screen = pygame.display.set_mode((width, height), pygame.HWSURFACE)

        # Initialise fonts.
        pygame.font.init()

        # Initialise music
        pygame.mixer.init()

        # Initialise the joystick.
        pygame.joystick.init()
        joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
        for joystick in joysticks:
            joystick.init()

        pygame.event.set_allowed(None)
        pygame.event.set_allowed([pygame.locals.QUIT,
            pygame.locals.JOYAXISMOTION,
            pygame.locals.KEYDOWN, pygame.locals.MOUSEBUTTONDOWN,  pygame.locals.JOYBUTTONDOWN])

        self.levels = {
            "main": SaveLevel('./assets/maps/CAPFLAG MAP')
        }

        self.map = Map(
            self.screen,
            self.levels.get("main"),
            Tileset(level_tileset_path, (16, 16), (32, 32)),
            LevelMusic('assets/music/song.mp3')
        )
        self.map.music.load_music()

    def set_state(self, new_state):
        if(new_state and new_state != self.game_state):
            self.game_state = new_state

            if(self.game_state.value == GameState.PLAY.value):
                pygame.key.set_repeat(50, 50)
            else:
                pygame.key.set_repeat(0, 0)

    def run(self):
        running = True
        clock = pygame.time.Clock()
        tickspeed = 60
        last_direction = None
        toMove = False # Flag for when player moves - reduces network stress
        cast = False # Flag for when player casts spell.
        me = self.players.me
        flags = self.flags

        if me.mute == "False":
            LevelMusic.play_music_repeat()

        try:
            while running:
                self.screen.fill((white))
                clock.tick(tickspeed)
                if(self.game_state.value == GameState.MENU.value):
                    self.menu.render((self.map.screen.get_width() * 0.45, self.map.screen.get_height()*0.4))
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT or event.type == pygame.locals.QUIT:
                            running = False
                            break

                        self.set_state(self.menu.update(event))
                elif(self.game_state.value == GameState.QUIT.value):
                    running = False
                    break
                elif(self.game_state.value == GameState.HELP.value):
                    webbrowser.open_new_tab("https://github.com/neontribe/untangled-2017/wiki")
                    self.game_state = GameState.MENU
                elif(self.game_state.value == GameState.MUTE.value):
                    if me.mute == "False":
                        me.set_mute("True", True)
                        LevelMusic.stop_music()
                    elif me.mute == "True":
                        me.set_mute("False", True)
                        LevelMusic.play_music_repeat()
                    self.game_state = GameState.MENU
                else:
                    # handle inputs
                    if last_direction == None:
                        last_direction = Movement.DOWN
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT or event.type == pygame.locals.QUIT:
                            running = False
                            break
                        elif event.type == pygame.locals.KEYDOWN and event.key == pygame.locals.K_ESCAPE:
                            self.set_state(GameState.MENU)

                        elif event.type == pygame.locals.KEYDOWN:
                            if event.key == pygame.locals.K_UP or event.key == pygame.locals.K_w:
                                me.move(Movement.UP)
                                last_direction = Movement.UP
                                toMove = True
                            elif event.key == pygame.locals.K_DOWN or event.key == pygame.locals.K_s:
                                me.move(Movement.DOWN)
                                last_direction = Movement.DOWN
                                toMove = True
                            elif event.key == pygame.locals.K_LEFT or event.key == pygame.locals.K_a:
                                me.move(Movement.LEFT)
                                last_direction = Movement.LEFT
                                toMove = True
                            elif event.key == pygame.locals.K_RIGHT or event.key == pygame.locals.K_d:
                                me.move(Movement.RIGHT)
                                last_direction = Movement.RIGHT
                                toMove = True
                            elif event.key == pygame.locals.K_RETURN or event.key == pygame.locals.K_SPACE :
                                if me.can_fire_ability:
                                    cast = True
                                    me.attack(Action.SPELL, last_direction)
                                
                            if event.key == pygame.locals.K_r and me.can_step_ability:
                                me.step = 2
                                me.steptime = time.time()
                                me.can_step_ability = False
                               
                            pygame.event.clear(pygame.locals.KEYDOWN)
                            
                        if time.time() - me.steptime >30:
                            me.can_step_ability = True
                        elif time.time() - me.steptime >3:
                            me.step = 1
                            
                    if pygame.mouse.get_pressed()[0]:
                        if me.can_fire_ability:
                            cast = True
                            me.attack(Action.SPELL, last_direction)
                        pygame.event.clear(pygame.locals.MOUSEBUTTONDOWN)
                    

                    # https://stackoverflow.com/a/15596758/3954432
                    # Handle controller input by setting flags (move, neutral)
                    # and using timers (delay, pressed).
                    # Move if pressed timer is greater than delay.

                    if(pygame.joystick.get_count() > 0 and not me.name.startswith("windows") and not toMove):
                        joystick = pygame.joystick.Joystick(0)
                        move = False
                        delay = 100
                        neutral = True
                        pressed = 0
                        last_update = pygame.time.get_ticks()
                        y_axis = joystick.get_axis(1)
                        x_axis = joystick.get_axis(0)

                        if y_axis == 0 and x_axis == 0: #Indicates no motion.
                            neutral = True
                            pressed = 0
                        else:
                            if neutral:
                                move = True
                                neutral = False
                            else:
                                pressed += pygame.time.get_ticks() - last_update
                        if pressed > delay:
                            move = True
                            pressed -= delay
                        if move:
                            # up/down
                            if y_axis > 0.5:
                                me.move(Movement.DOWN)
                                last_direction = Movement.DOWN
                                toMove = True
                            if y_axis < -0.5:
                                me.move(Movement.UP)
                                last_direction = Movement.UP
                                toMove = True
                            # left/right
                            if x_axis > 0.5:
                                me.move(Movement.RIGHT)
                                last_direction = Movement.RIGHT
                                toMove = True
                            if x_axis < -0.5:
                                me.move(Movement.LEFT)
                                last_direction = Movement.LEFT
                                toMove = True

                        # R
                        if joystick.get_button(5):
                            if me.can_fire_ability:
                                cast = True
                                me.attack(Action.SPELL, last_direction)
                        if joystick.get_button (9):
                            self.set_state(GameState.MENU)

                        last_update = pygame.time.get_ticks()

                    
                    if cast:
                        me.can_fire_ability = False
                        me.firetime = time.time()
                    
                    if time.time() - me.firetime > 2:
                        me.can_fire_ability = True

                    self.map.render()
                    me.render()
                    for flag in flags:
                        flag.render()
                    for spell in me.cast_spells:
                        spell.render()
                    for particle in me.particle_list:
                        particle.render()

                    self.players.set(self.network.node.peers())

                    # check network
                    events = self.network.get_events()
                    if events:
                        try:
                            for event in self.network.get_events():
                                if event.type == 'ENTER':
                                    # Force update on first join.
                                    toMove = True

                                    auth_status = event.headers.get('AUTHORITY')
                                    if auth_status == 'TRUE':
                                        self.players.authority_uuid = str(event.peer_uuid)
                                        self.players.remove(event.peer_uuid)

                                if event.group == "players:whois":
                                    self.network.node.shout("player:name", bson.dumps(
                                        {
                                            "name": self.players.me.name
                                        }
                                    ))

                                if event.group == "player:name":
                                    new_name = bson.loads(event.msg[0])
                                    player = self.players.get(event.peer_uuid)
                                    if new_name['name']:
                                        player.set_name(new_name['name'])

                                if event.group == "world:position":
                                    new_position = bson.loads(event.msg[0])
                                    network_player = self.players.get(event.peer_uuid)
                                if event.group == "world:combat":
                                    new_spell_properties = bson.loads(event.msg[0])
                                    network_spell_caster = self.players.get(event.peer_uuid)
                                    network_spell_caster.cast_spells.append(Spell(network_spell_caster, (0, 0)))
                                    network_spell_caster.cast_spells[-1].set_properties(SpellProperties(**new_spell_properties))
                                if event.group == "ctf:teams":
                                    if event.type == "SHOUT":
                                        team_defs = bson.loads(event.msg[0])
                                        self.players.set_teams(team_defs)
                                if event.group == "ctf:flags":
                                    if event.type == "SHOUT":
                                        flag_defs = bson.loads(event.msg[0])
                                        self.flags[0].set_position_from_authority(flag_defs.get("red"))
                                        self.flags[1].set_position_from_authority(flag_defs.get("blue"))

                                if network_player:
                                    network_player.set_position(Position(**new_position))

                        except Exception as e:
                            print(e)
                            import traceback
                            print(traceback.format_exc())
                            pass

                    # if there are other peers we can start sending to groups.
                    if self.players.others:
                        if toMove == True or cast == True:
                            self.network.node.shout("world:position", bson.dumps(me.get_position()._asdict()))
                            toMove = False
                        if cast == True:
                            self.network.node.shout("world:combat", bson.dumps(me.cast_spells[-1].get_properties()._asdict()))
                            cast = False

                    for playerUUID, player in self.players.others.items():
                        try:
                            player.render()
                            for spell in player.cast_spells:
                                spell.render()
                                spell.hit_target(me)

                        except PlayerException as e:
                            # PlayerException due to no initial position being set for that player
                            print(e)
                            pass

                pygame.display.update()
        finally:
            self.network.stop()

if __name__ == '__main__':
    logger = logging.getLogger("pyre")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    logger.propagate = False

    g = GameClient()
    g.run()
