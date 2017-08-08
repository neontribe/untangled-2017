from opensimplex import OpenSimplex

from tile import TileAttribute
from tile import TileType

import tmx

class Level():
    def load_tiles(self):
        self.width = 0
        self.height = 0
        self.grid = [[]]

    def get_tile(self, x, y):
        return self.grid[y][x]

    def can_move_to(self, x, y, name):
        if x < 0 or x >= self.width:
            return False
        elif y < 0 or y >= self.height:
            return False
        elif self.get_tile(x, y).has_attribute(TileAttribute.COLLIDE) and name != "james":
            return False
        return True


class ProceduralLevel(Level):
    def __init__(self, seed, width = 50, height = 50):
        self.openSimplex = OpenSimplex(seed)
        self.load_tiles(width, height)

    def load_tiles(self, width, height):
        self.width = width
        self.height = height
        self.grid = [
            [ self.generate_grid_tile(i, j) for i in range(width) ] for j in range(height)
        ] 

    def generate_grid_tile(self, x, y):
        noise = self.openSimplex.noise2d(x / 10, y / 10)
        if (noise < 0):
            return TileType.BRICK
        else:
            return TileType.DIRT


class SaveLevel(Level):
    def __init__(self,  path):
        tile_map = tmx.TileMap.load(path)
        layer = tile_map.layers[0]
        self.width = tile_map.width
        self.height = tile_map.height
        self.grid = [
            [None for x in range(self.width)] for y in range(self.height)
        ]
        for index, tile in enumerate(layer.tiles):
            x = index % self.width
            y = index // self.width
            if tile.gid == 54: # bush block
                self.grid[y][x] = TileType.BUSH
            elif tile.gid == 80: # tree
                self.grid[y][x] = TileType.TREE
            elif tile.gid == 178: #blue base block
                self.grid[y][x] = TileType.BLUE_BLOCK
            elif tile.gid == 8: #brick
                self.grid[y][x] = TileType.BRICK
            elif tile.gid == 22: #bridge
                self.grid[y][x] = TileType.BRIDGE
            elif tile.gid == 206: #water
                self.grid[y][x] = TileType.WATER
            elif tile.gid == 38: #shelter
                self.grid[y][x] = TileType.SHELTER
            elif tile.gid == 19: #sand
                self.grid[y][x] = TileType.SAND
            elif tile.gid == 130: #red base block
                self.grid[y][x] = TileType.RED_BLOCK
            else: # empty/other
                self.grid[y][x] = TileType.LAVA
        
