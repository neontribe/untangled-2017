from typing import List
from typing import Tuple
from typing import Union
import time
from pygame import Rect
import random, time

from lib.component import component
from lib.framework import Framework
from game.systems.collisionsystem import CollisionCall
from game.systems.particlesystem import Particle

@component(networked=True)
class IngameObject:
    """Gives an entity a place and size in game."""
    position: Tuple[int, int]
    size: Tuple[int, int]
    id = None

    def get_rect(self):
        return Rect(self.position,self.size)

@component(networked=True)
class Health:
    """Gives the entity health"""
    maxValue: int
    value: int

@component(networked=True)
class Crops:
    """Stores infomation about crops"""
    name: str
    growth_rate: int
    dehydration_rate: float
    growth_stage:int
    max_growth_stage:int
    plantage_time:float = time.time()

@component(networked=True)
class Energy:
    """"Gives the entity energy"""
    value: int

@component(networked=True)
class Damager:
    damagemin: int
    damagemax: int
    cooldown: float
    lasthit: float = 0.0
    enemyFaction: bool = True
    knockback: bool = True
    exclude = []

@component(networked=True)
class CanPickUp:
    itemID: str
    pickedUp: bool = False
    quantity: int = 1


@component(networked=True)
class WaterBar:
    """Gives the entity a water bar"""
    value: int
    disabled: bool = False

@component(networked=True)
class SpriteSheet:
    """Gives an entity an image and animations."""
    path: str
    tile_size: Union[int, Tuple[int, int]]
    tiles: dict
    moving: bool = False

@component(networked=True)
class Inventory:
    """Gives a player items"""
    items: dict
    maxSlots: int = 6
    activeSlot: int = 0
    hoverSlot: int = None
    activeItem: Tuple[str, int, SpriteSheet, int] = None
    usedSlots = [False for i in range(0, maxSlots)]

    distanceToDrop: int = 100

    itemSlotOffset: int = 6
    slotOffset: int = 10
    slotSize: int = 55

    x: float = 0
    y: float = 0
    height: float = slotOffset*2 + slotSize
    width: float = slotSize * maxSlots + slotOffset * maxSlots + slotOffset

    mapMinX: float = 0
    mapMinY: float = 0
    mapMaxX: float = 0
    mapMaxY: float = 0

    def getFirst(self):
        for i, v in enumerate(self.usedSlots):
            if not v:
                return i

    def getIDs(self):
        ret = []
        for i, v in self.items.items():
            ret.append(v['ID'])
        return ret

@component(networked=True)
class SpriteSheet:
    """Gives an entity an image and animations."""
    path: str
    tile_size: Union[int, Tuple[int, int]]
    tiles: dict
    default_tile: int = 0
    moving: bool = False

@component(networked=True)
class BackgroundMusic:
    path: str

directionVelocity = {
    'default':[0,0],
    'left':[-1,0],
    'right':[1,0],
    'up':[0,-1],
    'down':[0,1]
}

@component(networked=True)
class Map:
    path: str
    width: int
    height: int
    grid: list

@component(networked=True)
class Directioned:
    """States that an entity will be pointing in a certain direction.
    e.g. if walking"""
    direction: str = 'default'
    isOnlyLR: bool = False

    def toVelocity(self):
        return directionVelocity[self.direction]


@component(networked=True)
class Profile:
    """Gives an entity a name and gender."""
    name: str = 'Player'
    gender: str = 'Unknown'
    colour: Tuple[int,int,int] = (0, 255, 25)

@component(networked=True)
class PlayerControl:
    """Lets an entity be controlled by specific player's arrow keys."""
    player_id: str

@component(networked=True)
class GameAction:
    """Allows entities to have different actions"""
    action: str = ""
    isDropping: bool = False
    isHarvesting: bool = False
    last_plant: float = 0.0

@component()
class MoveRandom:
    direction: str = 'default'
    lastmove: float = 0
    movetime: float = 0

@component(networked=True)
class Clock:
    minute:int = 0
    cycle: int = 0
    year:  int = 0

@component(networked=False)
class Timed:
    time: float = 0

@component()
class ChasePlayer:
    speed: int
@component(networked=True)
class Wieldable:
    wielded: bool
    player_id: Union[str, None] = None
    cooldown = 2
    _last_hit: float = 0.0
@component(networked=True)
class SwingSword:
    swing: bool
@component(networked=True)
class ParticleEmitter:
    # square / circle / ring / star
    # blank means random
    particleTypes: list
    # offset from IngameObject
    offset: Tuple[int,int] = (0,0)
    # Initial movement
    velocity: Tuple[float,float] = (0.0,0.0)
    # Added to velocity each frame
    acceleration: Tuple[float,float] = (0.0,0.0)
    colour: Tuple[int,int,int] = (255,255,255)
    # "above" or "below" the object it's on render
    height: str = "below"
    randomness: Tuple[float,float] = (1.0,1.0)
    lifespan: int = 10
    doCreateParticles: bool = True
    # Will multiply velocity by the directionVelocity dict above
    # 0 - ignore direction
    # 1 - times by direction
    # 2 - times by inverse direction (so particles go in opposite to facing)
    directionMode: int = 0
    onlyWhenMoving: bool = False
    size: int = 8
    cooldown: float = 0.0
    particleAmount: int = 1
    initialRandomOnly: bool = False

    #DO NOT USE THIS MANUALLY
    _prePosition = (0,0)
    _lastGet = 0

    def getParticles(self,entity):
        new_particles = []
        if self.doCreateParticles and IngameObject in entity and self._lastGet + self.cooldown < time.time():
            doParticles = True
            if self.onlyWhenMoving:
                if self._prePosition == entity[IngameObject].position:
                    doParticles = False
                else:
                    self._prePosition = entity[IngameObject].position

            if doParticles:
                for i in range(0,self.particleAmount):
                    l = ["square","circle","ring","star"]
                    if len(self.particleTypes) > 0:
                        l = self.particleTypes
                    t = random.choice(l)
                    pos = (entity[IngameObject].position[0] + self.offset[0], entity[IngameObject].position[1] + self.offset[1])
                    vel = self.velocity
                    rand = self.randomness
                    if self.initialRandomOnly:
                        vel = (vel[0] + ((random.uniform(-10.0,10) * rand[0])/10), vel[1] + ((random.uniform(-10.0,10) * rand[1])/10))
                        rand = (0,0)
                    col = self.colour
                    if col == (-1,-1,-1):
                        col = Particle.get_random_colour()
                    if self.directionMode > 0 and Directioned in entity:
                        dire = entity[Directioned].toVelocity()
                        modi = 1
                        if self.directionMode == 2:
                            modi = -1
                        vel = (vel[0] * dire[0] * modi, vel[1] * dire[1] * modi)
                    part = Particle(
                        t,
                        pos,
                        self.lifespan,
                        velocity = vel,
                        acceleration = self.acceleration,
                        colour = col,
                        below = (self.height == "below"),
                        randomness = rand,
                        size = self.size
                    )
                    self._lastGet = time.time()
                    new_particles.append(part)
        return new_particles

@component(networked=True)
class Collidable:
    """Lets an entity collide with another collidable"""
    call_name: str
    canCollide: bool = True
    #rect to override
    customCollisionBox = None
    doPush: bool = False
    def setCustomCollisionBox(self, obj: IngameObject, width: int, height: int):
        center = (obj.position[0] + (obj.size[0] / 2), obj.position[1] + (obj.size[1] / 2))
        newTopLeft = (center[0] - (width/2), center[1] - (height/2))
        self.customCollisionBox = Rect(newTopLeft[0], newTopLeft[1], width, height)

    def toRect(self,entity):
        if self.customCollisionBox is not None:
            return self.customCollisionBox
        pos = entity[IngameObject].position
        size = entity[IngameObject].size
        return Rect(
            pos[0] - (size[0] / 2),
            pos[1] - (size[1] / 2),
            entity[IngameObject].size[0],
            entity[IngameObject].size[1]
        )

