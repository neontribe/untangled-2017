TILE_PIX_WIDTH = 32
TILE_PIX_HEIGHT = 32

import pygame
import pygame.locals
import os.path

from enum import Enum

from player import *

class Map():
    def __init__(self, screen, level, tileset, music):
        self.screen = screen
        self.level = level
        self.tileset = tileset
        self.music = music
        self.animationFrame = 0

    def set_centre_player(self, player):
        player.is_centre = True
        self.centre_player = player

    def render(self):
        self.animationFrame += 1
        self.animationFrame %= 16
        
        # get the tile at the top left and bottom right
        top_left_pos = self.get_map_pos(0, 0)
        bot_right_pos = self.get_map_pos(self.screen.get_width(), self.screen.get_height())
        for x in range(max(0, top_left_pos[0]), min(bot_right_pos[0] + 2, self.level.width)):
            for y in range(max(0, top_left_pos[1]), min(bot_right_pos[1] + 2, self.level.height)):
                tile = self.level.get_tile(x, y)
                tile_ids = tile.tileset_id
                if len(tile_ids) > 1:
                    pixel_pos = self.get_pixel_pos(x, y)
                    tile_image = self.tileset.get_surface_by_id(
                        tile_ids[self.animationFrame % len(tile_ids)-1]
                    )
                   
                else:
                    # TODO more readable ranges please
                    # for every tile in between
                    pixel_pos = self.get_pixel_pos(x, y)
                    tile_image = self.tileset.get_surface_by_id(tile_ids[0])
                self.screen.blit(tile_image, (pixel_pos[0], pixel_pos[1]))# TODO more readable ranges pleasepass

    def get_pixel_pos(self, x, y):
        # converts coordinates from those on the map to a position on the screen
        # what are the coordinates relative to the player
        relative_x = x - self.centre_player.x
        relative_y = y - self.centre_player.y

        # convert the coordinates into pixels
        pixel_x = relative_x * TILE_PIX_WIDTH
        pixel_y = relative_y * TILE_PIX_HEIGHT

        # base the coordinates around the centre of the screen, not the top-left
        centred_x = pixel_x + (self.screen.get_width() // 2)
        centred_y = pixel_y + (self.screen.get_height() // 2)

        return [centred_x, centred_y]

    def get_map_pos(self, pixel_x, pixel_y):
        # converts coordinates from a position on the screen to cordinates on the map
        # factor in that the pixels are relative to the centre of the screen
        uncentred_x = pixel_x - (self.screen.get_width() // 2)
        uncentred_y = pixel_y - (self.screen.get_height() // 2)

        # convert the pixels into coordinates
        relative_x = uncentred_x // TILE_PIX_WIDTH
        relative_y = uncentred_y // TILE_PIX_HEIGHT

        # make the coordinates absolute, not relative to the player
        map_x = relative_x + self.centre_player.x
        map_y = relative_y + self.centre_player.y

        return [map_x, map_y]
