import pygame
from pygame import Rect

from lib.system import System
from game.components import *
from game.systems.collisionsystem import *

class RenderSystem(System):
    """This system draws any entity with a SpriteSheet component."""

    def __init__(self, screen):
        self.screen = screen
        self.image_cache = {}
        self.steps = 0
        self.particles = {
            'above':[],
            'below':[]
        }
        self.particleFunc = {
            'square': lambda p, s: self.particle_square(p,s),
            'circle': lambda p, s: self.particle_circle(p,s),
            'ring': lambda p, s: self.particle_ring(p,s),
            'star': lambda p, s: self.particle_star(p,s)
        }

        font_path = 'assets/fonts/alterebro-pixel-font.ttf'
        self.font = pygame.font.Font(font_path, 45)

    def update(self, game, dt: float, events: list):
        # Step through 15 sprite frames each second
        self.steps += dt
        frame = int(self.steps // (1.0 / 15))

        # Find our center, if we have a player to focus on
        our_center = (0, 0)
        for key, entity in game.entities.items():
            # Are they a player?
            if PlayerControl in entity and IngameObject in entity:
                # Are they us?
                if game.net.is_me(entity[PlayerControl].player_id):
                    our_center = entity[IngameObject].position
                    break

        self.draw_particles(game, "below", our_center)

        previousCollidables = []

        # Render everything we can
        for key, entity in game.entities.items():
            # Don't check for items being picked up
            if CanPickUp in entity:
                if entity[CanPickUp].pickedUp:
                    continue

            #Check collisions for entity against all previously checked entities
            if IngameObject in entity and Collidable in entity:
                if entity[Collidable].canCollide:
                    game.collisionSystem.checkCollisions(game,key,entity[Collidable],previousCollidables)
                    previousCollidables.append((key,entity[Collidable]))

            if IngameObject in entity and ParticleEmitter in entity:
                new_part = entity[ParticleEmitter].getParticle(entity)
                if new_part != None:
                    game.particles.add_particle(new_part)

            # Is this an entity we should draw?
            if IngameObject in entity and SpriteSheet in entity:
                spritesheet = entity[SpriteSheet]

                # Where are they relative to us?
                pos = entity[IngameObject].position
                rel_pos = (pos[0] - our_center[0], pos[1] - our_center[1])
                
                screen_pos = (rel_pos[0] + game.framework.dimensions[0]/2, rel_pos[1] + game.framework.dimensions[1]/2)

                img_indexes = spritesheet.tiles["default"]

                # Will they be facing a certain direction?
                if Directioned in entity:
                    alts = spritesheet.tiles[entity[Directioned].direction]
                    if alts != None:
                        img_indexes = alts

                # Get the image relevent to how far through the animation we are
                if spritesheet.moving:
                    img_index = img_indexes[frame % len(img_indexes)]
                else:
                    img_index = img_indexes[0]
                img = self.get_image(spritesheet, img_index)
                
                #Scale the image
                if img.get_size() != entity[IngameObject].size:
                    img = pygame.transform.smoothscale(img, entity[IngameObject].size)
                
                rect = Rect(screen_pos, entity[IngameObject].size)
                rect.center = screen_pos
                
                # Add a rectangle behind the item because the quantity is seen outside of the item
                if CanPickUp in entity:
                    pygame.draw.circle(self.screen, (0, 255, 0), (int(rect.x + rect.width / 2), int(rect.y + rect.height / 2)), int(rect.width/2))

                # Draw the image
                self.screen.blit(img, rect)

                # If it is an item show the amount of items there are
                if CanPickUp in entity:
                    if entity[CanPickUp].quantity > 1:
                        rendered_text_qitem = self.font.render(str(entity[CanPickUp].quantity), False, (0, 0, 0))
                        
                        self.screen.blit(rendered_text_qitem, rect)
                        
                # Center health bar and nametag
                rect.x -= 30
                # Checks if entity has an energy component
                if Energy in entity:
                    # Energy bar wrapper
                    energyBarThickness = 2
                    pygame.draw.rect(self.screen, (255, 255, 255),(rect.x, rect.y-45, 100+energyBarThickness*2, 10), energyBarThickness)
                    
                    # Yellow energy bar
                    if entity[Energy].value > 0:
                        currentEnergyPos = (rect.x+energyBarThickness, rect.y-45+energyBarThickness, entity[Energy].value, 10-energyBarThickness*2)
                        pygame.draw.rect(self.screen, (255, 255, 0), currentEnergyPos)

                # Checks if entity has a health component
                if Health in entity:
                    # Health bar wrapper
                    healthBarThickness = 2
                    pygame.draw.rect(self.screen, (255, 255, 255), (rect.x, rect.y-30, 100+healthBarThickness*2, 10), healthBarThickness)
             
                    # Red health bar
                    if entity[Health].value > 0:
                        currentHealthPos = (rect.x+healthBarThickness, rect.y-30+healthBarThickness, entity[Health].value, 10-healthBarThickness*2)
                        pygame.draw.rect(self.screen, (255, 0, 0), currentHealthPos)

                if WaterBar in entity:
                    if not entity[WaterBar].disabled:
                        # Water bar wrapper
                        waterBarThickness = 2
                        pygame.draw.rect(self.screen, (255, 255, 255), (rect.x, rect.y-60, 100+waterBarThickness*2, 10), waterBarThickness)

                        # Blue water bar
                        if entity[Health].value > 0:
                            currentWaterPos = (rect.x+waterBarThickness, rect.y-60+waterBarThickness, entity[WaterBar].value, 10-waterBarThickness*2)
                            pygame.draw.rect(self.screen, (0, 0, 255), currentWaterPos)

                        rect.y -= 15

                # Does the entity have a name we can draw
                if Profile in entity:
                    name = entity[Profile].name

                    # Draw our name with our font in white
                    rendered_text_surface = self.font.render(name, False, (0, 255, 25))

                    # Move the nametag above the player
                    rect.y -= 100

                    # Draw this rendered text we've made to the screen
                    self.screen.blit(rendered_text_surface, rect)

                # Checks if it is a player
                if PlayerControl in entity:
                    # Draw the inventory bar for us only
                    if game.net.is_me(entity[PlayerControl].player_id):
                        # Debugging if statement
                        if Inventory in entity:
                            inv = entity[Inventory]

                            # Inventory bar colours
                            inventoryBackgroundColour = (183, 92, 5)
                            slotBackgroundColour = (255, 159, 67)

                            # Draw inventory bar
                            inventoryPos = (inv.x, inv.y, inv.width, inv.height)
                            pygame.draw.rect(self.screen, inventoryBackgroundColour, inventoryPos)

                            # Draw slots
                            slotIndex = 0
                            for x in range(int(inv.x+inv.slotOffset), int(inv.x+inv.width), inv.slotOffset+inv.slotSize):
                                # The active slot has a different colour
                                if slotIndex == inv.activeSlot:
                                    colour = (241, 196, 15)
                                elif slotIndex == inv.hoverSlot:
                                    colour = (243, 156, 18)
                                else:
                                    colour = slotBackgroundColour

                                pygame.draw.rect(self.screen, colour, (x, inv.y+inv.slotOffset, inv.slotSize, inv.slotSize))
                                
                                # Check if item exists in inventory
                                if slotIndex * 2 < len(entity[Inventory].items):
                                    item = game.entities[entity[Inventory].items[slotIndex * 2]]

                                    itemImgIndexes = item[SpriteSheet].tiles['default']
                                    itemImgIndex = itemImgIndexes[frame % len(itemImgIndexes)]

                                    # If it does, get its image
                                    itemImg = self.get_image(item[SpriteSheet], itemImgIndex)
                                    itemW, itemH = (inv.slotSize-inv.slotOffset, inv.slotSize-inv.itemSlotOffset * 2)
                                    itemImg = pygame.transform.scale(itemImg, (itemW, itemH))

                                    # The item is placed in the slot with a 3px offset
                                    itemRect = (x + inv.itemSlotOffset, inv.y+inv.slotOffset + inv.itemSlotOffset, itemW, itemH)
                                    self.screen.blit(itemImg, itemRect)

                                    # Drawing text that shows how many items of this kind there are
                                    lItemRect = list(itemRect)
                                    lItemRect[1] += inv.slotOffset
                                    itemRect = tuple(lItemRect)

                                    rendered_text_qslot = self.font.render(str(entity[Inventory].items[slotIndex * 2 + 1]), False, (255, 255, 255))
                                    self.screen.blit(rendered_text_qslot, itemRect)

                                slotIndex += 1
            self.draw_particles(game, "above", our_center)

    def get_image(self, spritesheet, index):
        # Ideally, we cache so we only process a file once
        if spritesheet.path not in self.image_cache:
            # Load from file
            sheet_img = pygame.image.load(spritesheet.path)

            if isinstance(spritesheet.tile_size, tuple):
                tile_width = spritesheet.tile_size[0]
                tile_height = spritesheet.tile_size[1]
            else:
                tile_width = spritesheet.tile_size
                tile_height = spritesheet.tile_size


            # Check the file can be divided right
            if sheet_img.get_width() % tile_width != 0 or sheet_img.get_height() % tile_height != 0:
                raise ValueError('Spritesheet width and height are not a multiple of its tile size')
            
            # Partition into sub-images
            images = []
            for y in range(0, sheet_img.get_height(), tile_height):
                for x in range(0, sheet_img.get_width(), tile_width):
                    bounds = pygame.Rect(x, y, tile_width, tile_height)
                    images.append(sheet_img.subsurface(bounds))
            self.image_cache[spritesheet.path] = images

        return self.image_cache[spritesheet.path][index]

    def draw_particles(self, game, height: str, our_center):
        if height in self.particles.keys():
            for p in self.particles[height]:
                self.draw_particle(game, p, our_center)

    def draw_particle(self, game, particle, our_center):
        pos = (round(particle.position[0]), round(particle.position[1]))
        rel_pos = (pos[0] - our_center[0], pos[1] - our_center[1])
        screen_pos = (rel_pos[0] + game.framework.dimensions[0] // 2, rel_pos[1] + game.framework.dimensions[1] // 2)
        self.particleFunc[particle.particleType](particle, screen_pos)

    def particle_square(self, p, pos):
        rect = Rect(pos[0],pos[1],8,8)
        pygame.draw.rect(self.screen,p.colour,rect)

    def particle_circle(self, p, pos):
        pygame.draw.circle(self.screen,p.colour,pos,4)
        
    def particle_ring(self, p, pos):
        pygame.draw.circle(self.screen,p.colour,pos,4,2)

    def particle_star(self, p, pos):
        hor = (
            [pos[0] - 4, pos[1]],
            [pos[0] + 4, pos[1]]
        )
        ver = (
            [pos[0], pos[1] - 4],
            [pos[0], pos[1] + 4]
        )
        pygame.draw.line(self.screen,p.colour,hor[0],hor[1],2)
        pygame.draw.line(self.screen,p.colour,ver[0],ver[1],2)
