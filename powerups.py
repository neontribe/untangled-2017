import pygame

class Powerup():
    def __init__(self, id, rect, colour, screenbuffer,  map):
        self.id = id
        self.rect = rect
        self.colour = colour
        self.screenbuffer = screenbuffer
        self.map = map
        
    def onPickup(self, player):
        pass
        
    def onDrop(self):
        pass
        
    def onUpdate(self):
        pass
    
    def draw(self):
        temppos = self.map.get_pixel_pos(self.rect.x,  self.rect.y)
        pygame.draw.rect(self.screenbuffer, self.colour, pygame.Rect(temppos[0],  temppos[1],  32,  32))
        pass
