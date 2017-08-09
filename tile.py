from enum import Enum

import pygame

import map

'''
TileAttribute represents the actions which a tile is able to inflict upon a player.

'''
class TileAttribute(Enum):
    COLLIDE =   0b0001
    SPIKES =    0b0010

class TileType(Enum):
<<<<<<< HEAD
    BUSH = ([53],  [ TileAttribute.COLLIDE ])
    TREE = ([79],  [ TileAttribute.COLLIDE ])
    BLUE_BLOCK = ([177],  [])
    RED_BLOCK = ([129],  [])
    BRICK = ([7],  [])
    BRIDGE = ([21],  [])
    WATER = ([205,206,207],  [ TileAttribute.COLLIDE ])
    SHELTER = ([37],  [ TileAttribute.COLLIDE ])
    SAND = ([18],  [])
    LAVA = ([166, 167, 168, 182, 183, 184, 198, 199, 200, 214, 215, 216, 229, 230, 229, 216, 215, 214, 299, 199, 198, 184, 183, 182, 168, 167],  [ TileAttribute.SPIKES ])
=======
    BUSH = (53,  [ TileAttribute.COLLIDE ])
    MELON = (137, [ TileAttribute.COLLIDE])
    TREE = (79,  [ TileAttribute.COLLIDE ])
    BLUE_BLOCK = (177,  [])
    RED_BLOCK = (129,  [])
    BRICK = (7,  [])
    BRIDGE = (21,  [])
    WATER = (205,  [ TileAttribute.COLLIDE ])
    SHELTER = (37,  [ TileAttribute.COLLIDE ])
    SAND = (18,  [])
    LAVA = (237,  [ TileAttribute.SPIKES ])
>>>>>>> bd883ba038c87691f06fa50bfd22b349b0c83cfb

    def __init__(self, tileset_id, attributes):
        self.tileset_id = tileset_id
        self.attributes = 0
        self.animationFrame = 0
        for attribute in attributes:
            # bitwise or - combines each binaru number into one number
            # a TileType with WATER and COLLIDE would look like 1001
            self.attributes = self.attributes | attribute.value

    def has_attribute(self, attribute):
        # bitwise and - sees if one binaru number contains another
        return self.attributes & attribute.value == attribute.value


class Tileset():
    def __init__(self, image, grid_dimensions, render_dimensions=(map.TILE_PIX_WIDTH, map.TILE_PIX_HEIGHT)):
        self.image = pygame.image.load(image)
        self.grid_dimensions = grid_dimensions
        self.render_dimensions = render_dimensions
        self.surfaces = {}

    def get_surface_by_id(self, id):
        if id in self.surfaces:
            return self.surfaces[id]

        clip_x, clip_y = self.find_position(id)

        cur_tile_width = (self.image.get_width() // self.grid_dimensions[0])
        cur_tile_height = (self.image.get_height() // self.grid_dimensions[1])

        clip_rect = (
            cur_tile_width * clip_x,
            cur_tile_height * clip_y,
            cur_tile_width,
            cur_tile_height
        )

        subsurface = self.image.subsurface(clip_rect).convert_alpha()
        subsurface = pygame.transform.scale(subsurface, self.render_dimensions)
        self.surfaces[id] = subsurface

        return self.surfaces[id]

    def find_position(self, id):
        x = id % self.grid_dimensions[0]
        y = id // self.grid_dimensions[1]

        return (x, y)

    def find_id(self, x, y):
        return y * self.grid_dimensions[1] + x
