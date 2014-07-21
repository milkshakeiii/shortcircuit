'''
Short Circuit by Tyler Mitchell and Henry Solberg

A (hopefully!) fun turn-based puzzle game.
Get to all the goal hexes without being detected!
Uses an external level pack.

7/31/2012
'''

import pygame, sys, os, copy, random
from pygame.locals import *

FPS = 30
WINWIDTH = 1200
WINHEIGHT = 675

HALF_WINWIDTH = int(WINWIDTH/2)
HALF_WINHEIGHT = int(WINHEIGHT/2)

BLACK = (0, 0, 0)
GRAY = (166, 166, 166)
DARKGRAY = (90, 90, 90)
WHITE = (255, 255, 255)
OFFWHITE = (240, 240, 180)
DARKBLUE = (0, 50, 100)
DOSGREEN = (10, 220, 10)
GREEN = (10, 150, 10)
RED = (255, 0, 0)
BLUE = (0, 100, 255)


REDTINT = (255, 0, 0, 130)
BLUETINT = (0, 100, 255, 130)

BGCOLOR = DARKBLUE
TEXTCOLOR = OFFWHITE

MENUMUSIC_FILENAME = 'data\\music\\loooooong circuit.ogg'
BGMUSIC_FILENAME = 'data\\music\\short circuit background.ogg'
LEVELS_FILENAME = 'data\\sclevels.data'
PROFILES_FILENAME = 'scprofiles.data'

# width and height of the square tile containing a hex
SIDE_OF_TILE = 40

# For facing
RIGHT = 0
UPRIGHT = 1
UPLEFT = 2
LEFT = 3
DOWNLEFT = 4
DOWNRIGHT = 5



def loadImageFile(filename, useColorKey=False):
    '''A nice helper image-loading function.  Grabs errors.'''
    try:
        image = pygame.image.load(filename)
    except pygame.error, message:
        print 'Cannot load image:', filename
        terminate()
    
    if useColorKey:
        image = image.convert()
        colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey, RLEACCEL)
    else:
        image = image.convert_alpha()
    
    return image

class Button:
    def __init__(self, rect, text='', textColor=OFFWHITE, color=BLUE,
                 highlightColor=RED, clickedColor=BLACK):
        self.rect = rect
        self.text = text
        self.textColor = textColor
        self.color = color
        self.highlightColor = highlightColor
        self.clickedColor= clickedColor
        self.font = BASICFONT
        self.mouseOn = False
        self.isClicked = False

        self.setupText()

        self.update(None, False)

    def isPointIn(self, point):
        '''Returns boolean'''
        return self.rect.collidepoint(point)

    def setColor(self, color):
        self.color = color

    def setClickedColor(self, color):
        self.clickedColor = color

    def setHighlightColor(self, color):
        '''Set it to None for no highlighting'''
        self.highlightColor = color

    def setFont(self, font):
        self.font = font

    def setText(self, text):
        self.text = text
        self.setupText()

    def setupText(self):
        self.textSurf = self.font.render(self.text, True, self.textColor)
        self.textRect = self.textSurf.get_rect()
        self.update(None, False)

    def update(self, mousePoint=None, mouseClicked=False):
        '''mousePoint is the location of the mouse, or None if it is to be ignored
        mouseClicked is a boolean...if True the button will check if it's been clicked'''
        self.textRect.center = self.rect.center
        if mousePoint != None:
            if self.isPointIn(mousePoint):
                self.mouseOn = True
                if mouseClicked:
                    self.isClicked = True
                else:
                    self.isClicked = False
            else:
                # mouse not on button
                self.mouseOn = False
                self.isClicked = False #just to be sure

    def draw(self, surf):
        '''Draws the button on the surface.'''
        pygame.draw.rect(surf, self.color, self.rect)
        if self.mouseOn:
            # mouse is on button, so highlight
            if self.highlightColor != None:
                pygame.draw.rect(surf, self.highlightColor, self.rect.inflate(6, 6), 3)
            if self.isClicked:
                # we've been clicked, give feedback
                pygame.draw.rect(surf, self.clickedColor, self.rect)
        surf.blit(self.textSurf, self.textRect)

class ButtonGroup:
    def __init__(self, buttons):
        '''buttons is a list of buttons to be added immediately, often empty'''
        self.buttons = buttons

    def __getitem__(self, index):
        return self.buttons[index]

    def __len__(self):
        return len(self.buttons)

    def index(self, item):
        return self.buttons.index(item)

    def add(self, button):
        self.buttons.append(button)

    def setColor(self, color):
        for button in self.buttons:
            button.setColor(color)

    def update(self, mousePoint=None, mouseClicked=False):
        for button in self.buttons:
            button.update(mousePoint, mouseClicked)

    def draw(self, surf):
        for button in self.buttons:
            button.draw(surf)

    def getClickedButton(self):
        '''Returns the first button in the group which has been clicked.
        No buttons clicked => returns None'''
        for button in self.buttons:
            if button.isClicked:
                return button
        return None

class Profile:
    def __init__(self, profileDict):
        '''profileDict is the base dictionary of the profile.
        See readProfilesFile for help'''
        self.dict = profileDict

    def __getitem__(self, key):
        return self.dict[key]

    def __setitem__(self, key, value):
        self.dict[key] = value

    def __len__(self):
        return len(self.dict)

    def isLevelIndexCompleted(self, levelIndex):
        '''Returns boolean'''
        if levelIndex < 15:
            # tutorial level
            return (levelIndex < self['tutLevel'])
        else:
            if levelIndex <= self['highestBlock']:
                # level is in a previous block
                return True
            elif levelIndex > self['highestBlock'] + 5:
                # level is in a future block
                return False
            else:
                # level is in current block
                return (levelIndex in self['currentLevels'])

    def isLevelIndexUnlocked(self, levelIndex):
        '''Returns boolean'''
####################################################
        # NO LEVELS 43-45 YET
        if levelIndex in range(42, 45):
            return False
####################################################
        if self.isLevelIndexCompleted(levelIndex):
            return True
        elif self['tutLevel'] < 15:
            # not done with tutorial
            return (levelIndex == self['tutLevel'])
        else:
            # level is incomplete, non-tutorial
            return self['highestBlock'] < levelIndex <= self['highestBlock'] + 5

    def updateProfile(self, completedLevelIndex):
        '''records the fact that the user has completed the level.
        Returns True if just unlocked a block, False otherwise.'''
        if self['tutLevel'] == 15:
            if self['currentLevels'] == [0]:
                # first level in this block
                self['currentLevels'] = [completedLevelIndex]
            else:
                self['currentLevels'].append(completedLevelIndex)
            if len(self['currentLevels']) == 5:
                # time to unlock the next block!
                self['highestBlock'] += 5
                self['currentLevels'] = [0]
                return True
        elif completedLevelIndex == self['tutLevel']:
            # completed tutorial level
            self['tutLevel'] += 1
            if self['tutLevel'] % 5 == 0:
                self['highestBlock'] = self['tutLevel'] - 1
                if self['tutLevel'] == 15:
                    # completed tutorial
                    return True
        elif completedLevelIndex in self['currentLevels']:
            # the user has already completed this level, do nothing
            pass
        return False
        

def getTopLeft(address):
    '''Converts an array address into the top-left corner point of the
    square on the gameboard (NOT WINDOW) to which the address refers.
    (For use in placing tiles and sprites.)'''
    (x, y) = address
    return (SIDE_OF_TILE*x + SIDE_OF_TILE/2*(y%2),
            SIDE_OF_TILE*3/4*y)

class Tile:
    def __init__(self, address):
        # address is (x, y) location on gameboard (not pixels)
        self.address = address
        self.image = IMAGESDICT['tile']
        self.rect = self.image.get_rect()
        self.rect.topleft = getTopLeft(self.address)
        self.walled = False
    
    def getAddress(self):
        return self.address
    
    def setAddress(self, newAddress):
        self.address = newAddress
    
    def getImage(self):
        return self.image
    
    def setImage(self, newImage):
        self.image = newImage

    def resetImage(self):
        self.setImage(IMAGESDICT['tile'])
    
    def getRect(self):
        return self.rect

    def hasWall(self):
        return self.walled

    def setWall(self, walled):
        '''True or False'''
        self.walled = walled
        if self.walled:
            self.setImage(IMAGESDICT['wall'])

    def makeGoal(self):
        self.setImage(IMAGESDICT['UncGoal'])

    def markCompletedGoal(self):
        self.setImage(IMAGESDICT['CompGoal'])

class Gameboard:
    '''A 2D list of tiles.'''
    def __init__(self, width, height, position):
        # Width and Height >=1
        # position is (x, y) location
        self.width = width
        self.height = height
        self.position = position

        # array[x][y] is the tile at (x, y)
        self.array = [[Tile((x, y)) for y in range(self.getHeight())]
                    for x in range(self.getWidth())]
        self.surface = pygame.Surface(((self.getWidth() + .5)*SIDE_OF_TILE,
            (.75*self.getHeight() + .25)*SIDE_OF_TILE))
        self.getSurface().fill(BGCOLOR)
        self.blitTiles()
        self.image = self.getSurface().copy()
    
    def getSurface(self):
        return self.surface
    
    def setSurface(self, newSurface):
        self.surface = newSurface
    
    def resetSurface(self):
        self.setSurface(pygame.Surface(((self.getWidth() + .5)*SIDE_OF_TILE,
            SIDE_OF_TILE*(1 + (self.getHeight() - 1)*.75))))
        self.resetTiles()
        self.blitTiles()
    
    def getImage(self):
        return self.image
    
    def setImage(self, newImage):
        self.image = newImage
    
    def getArray(self):
        return self.array
    
    def getWidth(self):
        return self.width
    
    def getHeight(self):
        return self.height
    
    def getPos(self):
        return self.position
    
    def setPos(self, newPos):
        self.position = newPos

    def resetTiles(self):
        for x in range(self.getWidth()):
            for y in range(self.getHeight()):
                tile.resetImage()

    def blitTiles(self):
        for x in range(self.getWidth()):
            for y in range(self.getHeight()):
                tile = self.getArray()[x][y]
                self.getSurface().blit(tile.getImage(), tile.getRect())

    def saveImage(self):
        '''Sets the image as a copy of what's currently drawn to the surface.'''
        self.setImage(self.getSurface().copy())

    def buildWallAt(self, address):
        (x, y) = address
        self.getArray()[x][y].setWall(True)

    def isWallAt(self, address):
        (x, y) = address
        return self.getArray()[x][y].hasWall()

    def addGoalAt(self, address):
        (x, y) = address
        self.getArray()[x][y].makeGoal()

    def markGoalAt(self, address):
        # doesn't check to see if there was even a goal there
        (x, y) = address
        self.getArray()[x][y].markCompletedGoal()

    def isAddressOutOfRange(self, address):
        (x, y) = address
        if (x < 0) or (x > self.getWidth() - 1) \
           or (y < 0) or (y > self.getHeight() - 1):
            return True
        else:
            return False

    def getTilesInZone(self, hometile, righthandDir):
        '''Returns a list of tiles in a half-cone whose right-hand edge is in
        righthandDir, and a list of those tiles which have walls.
        Hometile is included (possibly in both).'''
        (a, b) = hometile.getAddress()
        tiles = []
        tilesWithWalls = []
        for h in range(self.getWidth()):
            # for computing
            # k - b >= line1 are hexes below or on UPRIGHT line
            # k - b <= -line1 are hexes above or on DOWNRIGHT line
            line1 = -2*(h - a + (b+1)%2) + .1*((b+1)%2)
            # k - b >= line2 are hexes below or on UPLEFT line
            # k - b <= -line2 are hexes above or on DOWNLEFT line
            line2 = 2*(h - a - b%2) + .1*(b%2)
            for k in range(self.getHeight()):
                tileInZone = False
                if righthandDir == RIGHT and line1 <= k - b <= 0:
                    tileInZone = True
                elif righthandDir == UPRIGHT and k - b <= -line2 and k - b <= -line1:
                    tileInZone = True
                elif righthandDir == UPLEFT and k - b <= 0 and k - b >= line2:
                    tileInZone = True
                elif righthandDir == LEFT and 0 <= k - b <= -line2:
                    tileInZone = True
                elif righthandDir == DOWNLEFT and k - b >= line1 and k - b >= line2:
                    tileInZone = True
                elif righthandDir == DOWNRIGHT and k - b >= 0 and k - b <= -line1:
                    tileInZone = True
                
                if tileInZone:
                    tile = self.getArray()[h][k]
                    tiles.append(tile)
                    if tile.hasWall():
                        tilesWithWalls.append(tile)
        return tiles, tilesWithWalls

    def getDetectedTiles(self, dish):
        '''Returns a list of those tiles being scanned by the dish.'''
        (x, y) = dish.getAddress()
        mainDir = dish.getFacing()
        (dx, dy) = getdxdy((x, y), mainDir)
        if self.isAddressOutOfRange((x + dx, y + dy)) or self.isWallAt((x + dx, y + dy)):
            return []
        else:
            startTile = self.getArray()[x + dx][y + dy]
            offDir = (mainDir - 1) % 6
            righthandTiles, righthandWalls = self.getTilesInZone(startTile, offDir)
            lefthandTiles, lefthandWalls = self.getTilesInZone(startTile, mainDir)

            tiles = list(set(righthandTiles) | set(lefthandTiles))

            blockingWalls = []
            for rightWall in list(set(righthandWalls) - set(lefthandWalls)):
                blockingWalls.append((rightWall, offDir))
            for leftWall in list(set(lefthandWalls) - set(righthandWalls)):
                blockingWalls.append((leftWall, mainDir))
            # remove half-cones because of walls off the center line
            for (tileWithWall, righthandDir) in blockingWalls:
                blockedTiles = self.getBlockedTiles(tileWithWall, righthandDir)
                tiles = list(set(tiles) - set(blockedTiles)) # remove blocked tiles from those detected

            # remove center line beyond walls
            for centerwall in list(set(righthandWalls) & set(lefthandWalls)):
                blockedTiles = list(set(self.getBlockedTiles(centerwall, mainDir)) \
                                    & set(self.getBlockedTiles(centerwall, offDir)))
                tiles = list(set(tiles) - set(blockedTiles)) # remove blocked tiles from those detected
                    
            return tiles

    def getBlockedTiles(self, tileWithWall, righthandDir):
        '''Returns a list of tiles blocked.'''
        blockedTiles, wallsInZone = self.getTilesInZone(tileWithWall, righthandDir)
        return blockedTiles

class GameSprite(pygame.sprite.Sprite):
    def __init__(self, images, address, facing=RIGHT):
        pygame.sprite.Sprite.__init__(self)
        self.images = images
        self.facing = facing
        self.image = self.images[facing]
        self.rect = self.image.get_rect(topleft=getTopLeft(address))
        self.address = address

    def getImages(self):
        return self.images

    def getFacing(self):
            return self.facing

    def setFacing(self, newFacing):
        self.facing = newFacing

    def getRect(self):
        return self.rect

    def setRect(self, newRect):
        self.rect = newRect

    def getAddress(self):
        return self.address

    def setAddress(self, newAddress):
        self.address = newAddress

    def getImage(self):
        return self.image

    def setImage(self, newImage):
        self.image = newImage
        self.setRect(self.getImage().get_rect(topleft=getTopLeft(self.getAddress())))

    def move(self, gameboard, dx, dy):
        '''Changes the address of the sprite on the board.  Will not change if
        no hex on the board at the incremented address (sprite at edge).'''
        (x, y) = self.getAddress()
        newAddress = (x + dx, y + dy)
        if gameboard.isAddressOutOfRange(newAddress):
            # move is not possible, sprite at edge
            return False
        elif gameboard.isWallAt(newAddress):
            # move is not possible, wall in way
            return False
        else:
            self.setAddress(newAddress)
            return True

    def update(self):
        self.getRect().topleft = getTopLeft(self.getAddress())
        self.setImage(self.getImages()[self.getFacing()])

class PlayerSprite(GameSprite):
    def __init__(self, address, facing=RIGHT):
        images = IMAGESDICT['c']
        GameSprite.__init__(self, images, address, facing)

class DishSprite(GameSprite):
    def __init__(self, tint, address, facing=RIGHT):
        '''Tint is the color/type of dish.'''
        images = IMAGESDICT['dish']
        GameSprite.__init__(self, images, address, facing)
        self.tint = tint

    def getTint(self):
        return self.tint

    def setTint(self, newTint):
        self.tint = newTint



def main():
    global FPSCLOCK, DISPLAYSURF, TITLEFONT, BIGFONT, BASICFONT, MSGFONT, IMAGESDICT, SOUNDSDICT

    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    DISPLAYSURF = pygame.display.set_mode((WINWIDTH, WINHEIGHT))
##    DISPLAYSURF = pygame.display.set_mode((WINWIDTH, WINHEIGHT), FULLSCREEN)
    pygame.display.set_icon(loadImageFile('data\\images\\sc.ico'))
    pygame.display.set_caption('Short Circuit')

    TITLEFONT = pygame.font.Font('data\\fonts\\razerregular.ttf', 96)
    BIGFONT = pygame.font.Font('data\\fonts\\razerregular.ttf', 32)
    BASICFONT = pygame.font.Font('data\\fonts\\razerregular.ttf', 16)
    MSGFONT = pygame.font.Font('data\\fonts\\dos.ttf', 24)

    # Global images dictionary
    IMAGESDICT = {'c':      (loadImageFile('data\\images\\c0.png'),
                             loadImageFile('data\\images\\c1.png'),
                             loadImageFile('data\\images\\c2.png'),
                             loadImageFile('data\\images\\c3.png'),
                             loadImageFile('data\\images\\c4.png'),
                             loadImageFile('data\\images\\c5.png')),
                  'dish':   (loadImageFile('data\\images\\dish0.png'),
                             loadImageFile('data\\images\\dish1.png'),
                             loadImageFile('data\\images\\dish2.png'),
                             loadImageFile('data\\images\\dish3.png'),
                             loadImageFile('data\\images\\dish4.png'),
                             loadImageFile('data\\images\\dish5.png')),
                  'tile':   loadImageFile('data\\images\\hex_large.bmp', True),
                  'tile mask': loadImageFile('data\\images\\hex_large_mask.bmp', True),
                  'wall':   loadImageFile('data\\images\\wall.bmp', True),
                  'UncGoal':    loadImageFile('data\\images\\UncGoal.png'),
                  'CompGoal':   loadImageFile('data\\images\\CompGoal.png'),
                  'levelComplete':  loadImageFile('data\\images\\levelcomplete.png'),
                  'beenDetected':   loadImageFile('data\\images\\beendetected.png'),
                  'msgBG':  loadImageFile('data\\images\\msgBG.png')}

    # Global sounds dictionary
    SOUNDSDICT = {'keyStrokes': pygame.mixer.Sound('data\\sounds\\keyStrokes.ogg')}

    levels = readLevelsFile(LEVELS_FILENAME)
    numberOfLevels = len(levels)
    assert numberOfLevels > 0, 'No levels found in %s.' % (LEVELS_FILENAME)

    profiles = readProfilesFile(PROFILES_FILENAME)

    # startscreen
    pygame.mixer.music.load(MENUMUSIC_FILENAME)
    pygame.mixer.music.play(-1, 0.0)
    showStartScreen()

    # transition
    fadeToColor(BLACK, 500)

    # initial profile select
    profileSelectResult = 'changeProf'
    while profileSelectResult == 'changeProf':
        profiles, profileSelectResult = showProfileSelectScreen(profiles)
    currentProfileIndex = profileSelectResult

    while True:
        # level selection
        levelSelectResult = showLevelSelectScreen(numberOfLevels, profiles[currentProfileIndex])
        while levelSelectResult == 'changeProf':
            profileSelectResult = 'changeProf'
            while profileSelectResult == 'changeProf':
                profiles, profileSelectResult = showProfileSelectScreen(profiles)
            currentProfileIndex = profileSelectResult
            levelSelectResult = showLevelSelectScreen(numberOfLevels, profiles[currentProfileIndex])

        # level selection occurred
        currentLevelIndex = levelSelectResult

        # transition
        fadetime = 1000 # milliseconds
        pygame.mixer.music.fadeout(fadetime)
        fadeToColor(BLACK, fadetime)
        
        pygame.mixer.music.load(BGMUSIC_FILENAME)
        pygame.mixer.music.play(-1, 0.0)
        
        # leveling loop -- breaking this loop will go up to level selection above
        leveling = True
        while leveling:
            result = runLevel(levels, currentLevelIndex)
            if result == 'complete':
                # record the completion
                newBlock = profiles[currentProfileIndex].updateProfile(currentLevelIndex)
                saveProfilesFile(profiles, PROFILES_FILENAME)
                if newBlock:
                    leveling = False
                if profiles[currentProfileIndex].isLevelIndexUnlocked(currentLevelIndex + 1):
                    currentLevelIndex += 1
                else:
                    leveling = False # return to level select
            elif result == 'levelSelect':
                leveling = False # return to level select
            elif result == 'reset':
                pass

        # transition
        fadetime = 500 # milliseconds
        pygame.mixer.music.fadeout(fadetime)
        fadeToColor(BLACK, fadetime)
        pygame.mixer.music.load(MENUMUSIC_FILENAME)
        pygame.mixer.music.play(-1, 0.0)

def runLevel(levels, levelNum):
    '''Returns 'reset' or 'complete' based on status.'''
    levelDict = copy.deepcopy(levels[levelNum])

    gameboard = Gameboard(levelDict['width'], levelDict['height'],
                          (int((WINWIDTH - (levelDict['width'] + .5)*SIDE_OF_TILE)/2),
                           WINHEIGHT - (.75*levelDict['height'] + .25)*SIDE_OF_TILE))
    for address in levelDict['wallAddresses']:
        gameboard.buildWallAt(address)
    for address in levelDict['goalAddresses']:
        gameboard.addGoalAt(address)
    gameboard.blitTiles()
    gameboard.saveImage()

    player = PlayerSprite(levelDict['playerAddress'])
    movingSprites = pygame.sprite.Group(player)
    
    dishSprites = pygame.sprite.Group()
    for tint, address, facing in levelDict['dishes']:
        dishSprites.add(DishSprite(tint, address, facing))

    levelMessages = levelDict['messages']

    gameState = {'turnCounter': 0,
                 'nextMessage': 0}
    goalsAchieved = False
    playerDetected = False
    messageShown = False

    navButtons = ButtonGroup([])
    levelSelectRect = pygame.Rect(WINWIDTH - 180, WINHEIGHT - 40, 165, 30)
    levelSelectButton = Button(levelSelectRect, '[L]evel selection')
    navButtons.add(levelSelectButton)
    mousePoint = None

    # main game loop
    while True:
        # reset variables
        detectionColor = WHITE
        playerMoveTo = None
        keyPressed = False
        mouseClicked = False

        checkForQuit()
        checkForToggleFullscreen()
        for event in pygame.event.get(): # event handling loop
            if event.type == MOUSEMOTION:
                mousePoint = event.pos
            if event.type == MOUSEBUTTONUP:
                mousePoint = event.pos
                mouseClicked = True
            if event.type == KEYDOWN:
                keyPressed = True
                if not playerDetected and not goalsAchieved: # don't move if level's over
                    if event.key in (K_KP6, K_d): # move right
                        playerMoveTo = RIGHT
                    elif event.key in (K_KP9, K_e): # move up right
                        playerMoveTo = UPRIGHT
                    elif event.key in (K_KP7, K_q): # move up left
                        playerMoveTo = UPLEFT
                    elif event.key in (K_KP4, K_a): # move left
                        playerMoveTo = LEFT
                    elif event.key in (K_KP1, K_z): # move down left
                        playerMoveTo = DOWNLEFT
                    elif event.key in (K_KP3, K_c): # move down right
                        playerMoveTo = DOWNRIGHT
                    elif event.key == K_BACKSPACE:
                        return 'reset'
                    elif event.key == K_l:
                        return 'levelSelect'

        if playerMoveTo != None:
            moved = makeMove(gameboard, player, playerMoveTo)

            if moved:
                # increment the turn counter
                gameState['turnCounter'] += 1

                for dish in dishSprites:
                    if gameState['turnCounter'] % 4 == 0 \
                       and dish.getTint() == REDTINT:
                        dish.setFacing((dish.getFacing() + 1) % 6)
                    elif gameState['turnCounter'] % 5 == 0 \
                         and dish.getTint() == BLUETINT:
                        dish.setFacing((dish.getFacing() + 1) % 6)

                if player.getAddress() in levelDict['goalAddresses']:
                    levelDict['goalAddresses'].remove(player.getAddress())
                    gameboard.markGoalAt(player.getAddress())
                    gameboard.blitTiles()
                    gameboard.saveImage()
                    if len(levelDict['goalAddresses']) == 0:
                        goalsAchieved = True
                        keyPressed = False


        DISPLAYSURF.fill(BGCOLOR)
        gameboard.getSurface().blit(gameboard.getImage(), (0,0))

        # draw sprites to board
        movingSprites.update()
        dishSprites.update()
        movingSprites.clear(gameboard.getSurface(), gameboard.getImage())
        dishSprites.clear(gameboard.getSurface(), gameboard.getImage())
        movingSprites.draw(gameboard.getSurface())
        dishSprites.draw(gameboard.getSurface())

        # find detected tiles and tint them, and if the player is there...
        for dish in dishSprites:
            detectedTiles = gameboard.getDetectedTiles(dish)
            if len(detectedTiles) > 0:
                (r, g, b, a) = dish.getTint()
                tintSurf = IMAGESDICT['tile mask'].copy()
                overlay = pygame.Surface((SIDE_OF_TILE, SIDE_OF_TILE))
                overlay.fill((r, g, b))
                overlay.set_alpha(a)
                tintSurf.blit(overlay, (0,0))
                colorkey = tintSurf.get_at((0,0))
                tintSurf.set_colorkey(colorkey, RLEACCEL)
                tintSurf.set_alpha(a)
                for tile in detectedTiles:
                    gameboard.getSurface().blit(tintSurf, tile.getRect())
                    if player.getAddress() == tile.getAddress():
                        if not playerDetected:
                            keyPressed = False
                        playerDetected = True
                        detectionColor = (r, g, b)

        # draw the step counter
        turnSurf = BASICFONT.render('Turn: %s' % (gameState['turnCounter']), 1, TEXTCOLOR)
        turnRect = turnSurf.get_rect()
        turnRect.bottomleft = (20, WINHEIGHT - 10)
        DISPLAYSURF.blit(turnSurf, turnRect)
        # draw the level counter
        levelSurf = BASICFONT.render('Level: %s' % (levelNum + 1), 1, TEXTCOLOR)
        levelRect = levelSurf.get_rect()
        levelRect.bottomleft = (20, WINHEIGHT - 30)
        DISPLAYSURF.blit(levelSurf, levelRect)
        # draw level select button
        navButtons.update(mousePoint, mouseClicked)
        navButtons.draw(DISPLAYSURF)


        # draw gameboard
        DISPLAYSURF.blit(gameboard.getSurface(), gameboard.getPos())

        if playerDetected:
            # player has been spotted!...pause until keypress
            detectSurf = IMAGESDICT['beenDetected']
            detectRect = detectSurf.get_rect()
            detectRect.center = (HALF_WINWIDTH, HALF_WINHEIGHT)
            DISPLAYSURF.blit(detectSurf, detectRect)
            if keyPressed:
                return 'reset'
        elif goalsAchieved:
            # level complete...pause until keypress
            completeSurf = IMAGESDICT['levelComplete']
            completeRect = completeSurf.get_rect()
            completeRect.center = (HALF_WINWIDTH, HALF_WINHEIGHT)
            DISPLAYSURF.blit(completeSurf, completeRect)
            if keyPressed:
                return 'complete'
        else:
            # typical day at the park
            if len(levelMessages) > gameState['nextMessage'] and gameState['turnCounter'] == levelMessages[gameState['nextMessage']][0]:
                msgIndex = gameState['nextMessage']
                personSpeaking = levelMessages[msgIndex][1]
                message = levelMessages[msgIndex][2]
                drawInLevelMessage(message, personSpeaking, not messageShown)
                messageShown = True
            elif messageShown:
                gameState['nextMessage'] += 1
                messageShown = False

        # handle level select button
        if mouseClicked and not goalsAchieved:
            navClickedButton = navButtons.getClickedButton()
            if navClickedButton == levelSelectButton:
                return 'levelSelect'
            navClickedButton = None

        pygame.display.update()
        FPSCLOCK.tick(FPS)

def makeMove(gameboard, sprite, direction):
    '''Moves a sprite on the gameboard in the given direction, if possible.
    Returns True if it happened, False if not.'''
    if direction not in (RIGHT, UPRIGHT, UPLEFT, LEFT, DOWNLEFT, DOWNRIGHT):
        return False
    address = sprite.getAddress()
    (dx, dy) = getdxdy(address, direction)
    sprite.setFacing(direction)
    return sprite.move(gameboard, dx, dy)

def drawInLevelMessage(message, personSpeaking, firstTime):
    '''Displays the message.'''
    msgSurf = IMAGESDICT['msgBG'].copy()
    msgRect = msgSurf.get_rect(midtop = (HALF_WINWIDTH, 2))

    if personSpeaking != None:
        text = personSpeaking + ': ' + message
    else:
        text = message
    lines = breakUpIntoLines(text, 70)
    topCoord = 25
    typingSkipped = not firstTime
    for line in lines:
        if firstTime and not typingSkipped:
            height, typingSkipped = typeText(msgSurf, msgRect, line, (186, topCoord), MSGFONT, DOSGREEN)
        if typingSkipped:
            textSurf = MSGFONT.render(line, True, DOSGREEN)
            msgSurf.blit(textSurf, (186, topCoord))
            height = textSurf.get_height()
        topCoord += height
    DISPLAYSURF.blit(msgSurf, msgRect)

def breakUpIntoLines(text, maxCharsPerLine):
    '''Returns a list of strings (the lines).'''
    lines = ['']
    currentLineIndex = 0
    currentWord = ''
    text += ' '
    while text != '':
        currentWord = text[:text.find(' ')]
        if len(lines[currentLineIndex]) + len(currentWord) + 1 <= maxCharsPerLine:
            # add word to line
            if lines[currentLineIndex]:
                lines[currentLineIndex] += ' '
            lines[currentLineIndex] += currentWord
        else:
            lines.append(currentWord)
            currentLineIndex += 1
        text = text[text.find(' ')+1:]
    return lines

def typeText(surfToTypeOn, surfRect, text, topleft, fontObj, textColor, charsPerSec=32):
    '''Type text on at the given charsPerSec.  Returns height of the text,
    and then a boolean for if they skipped the typing.

    surfToTypeOn - pygame Surface
    text - string of text
    topleft - coordinates of destination (the topleft corner)
    fontObj - pygame Font'''
    displayOldImage = DISPLAYSURF.copy()
    surfOldImage = surfToTypeOn.copy()
    curLength = 0
    keySound = SOUNDSDICT['keyStrokes']
    keySound.play()
    while curLength <= len(text):
        checkForQuit()
        for event in pygame.event.get():
            if event.type == KEYDOWN and event.key in (K_SPACE, K_RETURN, K_KP_ENTER):
                # stop animating, reset display and surf
                surfToTypeOn.fill(BGCOLOR)
                surfToTypeOn.blit(surfOldImage, (0,0))
                DISPLAYSURF.fill(BGCOLOR)
                DISPLAYSURF.blit(displayOldImage, (0,0))
                keySound.stop()
                return 0, True
        surfToTypeOn.fill(BGCOLOR)
        surfToTypeOn.blit(surfOldImage, (0,0))
        if curLength < len(text):
            textSoFar = text[:curLength]+'_'
        else:
            textSoFar = text
        textSoFarSurf = fontObj.render(textSoFar, True, textColor)
        surfToTypeOn.blit(textSoFarSurf, topleft)
        DISPLAYSURF.fill(BGCOLOR)
        DISPLAYSURF.blit(displayOldImage, (0,0))
        DISPLAYSURF.blit(surfToTypeOn, surfRect)
        curLength += 1
        
        pygame.display.update()
        FPSCLOCK.tick(charsPerSec)
    keySound.stop()
    return textSoFarSurf.get_height(), False

def getdxdy(address, direction):
    '''Returns (dx, dy) tuple to get to adjacent hex in the given direction.'''
    (x, y) = address
    if direction == RIGHT:
        dx = 1
        dy = 0
    elif direction == UPRIGHT:
        dy = -1
        if y % 2 == 0:
            dx = 0
        else:
            dx = 1
    elif direction == UPLEFT:
        dy = -1
        if y % 2 == 0:
            dx = -1
        else:
            dx = 0
    elif direction == LEFT:
        dx = -1
        dy = 0
    elif direction == DOWNLEFT:
        dy = 1
        if y % 2 == 0:
            dx = -1
        else:
            dx = 0
    elif direction == DOWNRIGHT:
        dy = 1
        if y % 2 == 0:
            dx = 0
        else:
            dx = 1
    return (dx, dy)

def showStartScreen():
    frontTitleColor = BLACK
    backTitleColor = DARKBLUE
    titleSurf1 = TITLEFONT.render('Short Circuit', True, backTitleColor)
    titleSurf2 = TITLEFONT.render('Short Circuit', True, frontTitleColor)

    pleaseWaitSurf = BASICFONT.render('Please wait...', True, frontTitleColor)
    pleaseWaitRect = pleaseWaitSurf.get_rect(midtop = (HALF_WINWIDTH, int(WINHEIGHT*3/4)))

    degrees1 = 0
    degrees2 = 0
    runningtime = 0
    dancerx = HALF_WINWIDTH
    dancery = int(WINHEIGHT*3/4)-20
    animate = False
    flashed = False

    dancer = IMAGESDICT['c'][0]
    dancerRect = dancer.get_rect(center=(dancerx, dancery))
    
    while True:
        DISPLAYSURF.fill(BGCOLOR)
        rotatedSurf1 = pygame.transform.rotate(titleSurf1, degrees1)
        rotatedRect1 = rotatedSurf1.get_rect()
        rotatedRect1.center = (WINWIDTH / 2, WINHEIGHT / 2)
        DISPLAYSURF.blit(rotatedSurf1, rotatedRect1)

        rotatedSurf2 = pygame.transform.rotate(titleSurf2, degrees2)
        rotatedRect2 = rotatedSurf2.get_rect()
        rotatedRect2.center = (WINWIDTH / 2, WINHEIGHT / 2)
        DISPLAYSURF.blit(rotatedSurf2, rotatedRect2)

        DISPLAYSURF.blit(dancer, dancerRect)

        if not animate:
            runningtime = runningtime + 1
            DISPLAYSURF.blit(pleaseWaitSurf, pleaseWaitRect)
            if runningtime > 216:
                animate = True
        elif animate:
            if not flashed: # start off the animation with a bang!
                fadeToColor(WHITE, 67, True)
                flashed = True
                backTitleColor = WHITE
                titleSurf1 = TITLEFONT.render('Short Circuit', True, backTitleColor)
                frontTitleColor = RED
                titleSurf2 = TITLEFONT.render('Short Circuit', True, frontTitleColor)
            
            drawPressKeyMsg()
            degrees1 += 2
            degrees2 += 6

            

            dancerx = dancerx + random.randint(-10, 10)
            dancery = dancery + random.randint(-10, 10)
            if dancerx <= 0:
                dancerx = 0
            elif dancerx >= WINWIDTH:
                dancerx = WINWIDTH
            if dancery <= 0:
                dancery = 0
            elif dancery >= WINHEIGHT:
                dancery = WINHEIGHT

            dancerRect.center = (dancerx, dancery)

        checkForQuit()
        checkForToggleFullscreen()
        for event in pygame.event.get(): # waiting loop
            if event.type == KEYDOWN:
                return

        
        pygame.display.update()
        FPSCLOCK.tick(FPS)

def drawPressKeyMsg():
    pressKeySurf = BASICFONT.render('Press any key to play.', True, WHITE)
    pressKeyRect = pressKeySurf.get_rect()
    pressKeyRect.topleft = (WINWIDTH - 210, WINHEIGHT - 30)
    DISPLAYSURF.blit(pressKeySurf, pressKeyRect)

def showProfileSelectScreen(profiles):
    '''profiles is a list of profile dictionaries
    Returns (possibly updated) profiles and the index of the chosen profile.
    (Also allows for profile creation)'''
    listWidth = 160
    numberShown = 7
    nameHeight = 24
    listHeight = numberShown*(nameHeight + 4) - 4
    listRect = pygame.Rect(HALF_WINWIDTH - int(listWidth/2) - 10, HALF_WINHEIGHT - int(listHeight/2), listWidth, listHeight)

    profileButtons = ButtonGroup([])
    y = listRect.top
    for i in range(numberShown):
        buttonRect = pygame.Rect(listRect.left, y, listWidth, nameHeight)
        profileButtons.add(Button(buttonRect, color=BLACK, textColor=DOSGREEN, highlightColor=None, clickedColor=DARKGRAY))
        profileButtons[i].setFont(MSGFONT)
        y += nameHeight+4

    scrollRect = pygame.Rect(listRect.right, listRect.top, 20, listHeight)

    scrollUpRect = pygame.Rect(listRect.right, listRect.top, 20, 16)
    scrollDownRect = scrollUpRect.copy()
    scrollDownRect.bottom = listRect.bottom
    scrollButtons = ButtonGroup([])
    scrollUpButton = Button(scrollUpRect, '/\\', textColor=BLACK, color=GRAY, highlightColor=None, clickedColor=BLACK)
    scrollDownButton = Button(scrollDownRect, '\\/', textColor=BLACK, color=GRAY, highlightColor=None, clickedColor=BLACK)
    scrollButtons.add(scrollUpButton)
    scrollButtons.add(scrollDownButton)

    scrollStatusMinY = scrollUpRect.bottom + 1
    scrollStatusMaxY = scrollDownRect.top - 1 - 12
    scrollStatusRect = pygame.Rect(scrollUpRect.left, scrollStatusMinY, 20, 12)


    navButtons = ButtonGroup([])
    continueRect = pygame.Rect(0, 0, 140, 22)
    continueRect.center = (HALF_WINWIDTH, listRect.bottom + 21)
    continueButton = Button(continueRect, 'Continue')
    createRect = continueRect.copy()
    createRect.center = (HALF_WINWIDTH, continueRect.bottom + 20)
    createButton = Button(createRect, 'Create New...')
    deleteRect = createRect.copy()
    deleteRect.center = (HALF_WINWIDTH, createRect.bottom + 20)
    deleteButton = Button(deleteRect, 'Delete')
    navButtons.add(continueButton)
    navButtons.add(createButton)
    navButtons.add(deleteButton)
    
    mousePoint = None
    messageShowing = False
    profileSelected = False
    firstProfileIndex = 0
    while True:
        checkForQuit()
        checkForToggleFullscreen()
        maxFirstProfileIndex = len(profiles) - numberShown
        if maxFirstProfileIndex < 0:
           maxFirstProfileIndex = 0
        mouseClicked = False
        for event in pygame.event.get():
            if event.type == MOUSEMOTION:
                mousePoint = event.pos
            elif event.type == MOUSEBUTTONUP:
                mousePoint = event.pos
                mouseClicked = True

        for i in range(len(profileButtons)):
            if firstProfileIndex + i < len(profiles):
                profileButtons[i].setText(profiles[firstProfileIndex + i]['name'])

        if not profileSelected:
            continueButton.setColor(GRAY)
            continueButton.setClickedColor(GRAY)
            continueButton.setHighlightColor(None)
            deleteButton.setColor(GRAY)
            deleteButton.setClickedColor(GRAY)
            deleteButton.setHighlightColor(None)
        else:
            continueButton.setColor(BLUE)
            continueButton.setClickedColor(BLACK)
            continueButton.setHighlightColor(RED)
            deleteButton.setColor(BLUE)
            deleteButton.setClickedColor(BLACK)
            deleteButton.setHighlightColor(RED)

        if maxFirstProfileIndex > 0:
            scrollStatusRect.top = int((float(firstProfileIndex)/maxFirstProfileIndex)*(scrollStatusMaxY - scrollStatusMinY) + scrollStatusMinY)
            

        DISPLAYSURF.fill(BGCOLOR)

        pygame.draw.rect(DISPLAYSURF, BLACK, listRect)
        pygame.draw.rect(DISPLAYSURF, DARKGRAY, scrollRect)
        pygame.draw.rect(DISPLAYSURF, GRAY, scrollStatusRect)

        scrollButtons.update(mousePoint, mouseClicked)
        scrollButtons.draw(DISPLAYSURF)

        profileButtons.update(mousePoint, mouseClicked)
        profileButtons.draw(DISPLAYSURF)

        navButtons.update(mousePoint, mouseClicked)
        navButtons.draw(DISPLAYSURF)

        pygame.draw.rect(DISPLAYSURF, WHITE, listRect, 1)
        pygame.draw.rect(DISPLAYSURF, WHITE, scrollRect, 1)

        drawInLevelMessage('Select your profile from the list to resume a saved game.  Use the "Create New" button to start a new game, or "Delete" to permanently remove a profile.', None, not messageShowing)
        messageShowing = True

        pygame.display.update()
        FPSCLOCK.tick(FPS)

        if mouseClicked:
            profileClickedButton = profileButtons.getClickedButton()
            if profileClickedButton != None:
                i = profileButtons.index(profileClickedButton)
                if firstProfileIndex + i < len(profiles):
                    profileSelected = True
                    selectedIndex = firstProfileIndex + i
            profileClickedButton = None
            # otherwise, nav button?
            navClickedButton = navButtons.getClickedButton()
            if navClickedButton != None:
                if navClickedButton == continueButton:
                    if profileSelected:
                        return profiles, selectedIndex
                if navClickedButton == createButton:
                    profiles = createNewProfile(profiles)
                    return profiles, -1
                if navClickedButton == deleteButton:
                    if profileSelected:
                        profiles = deleteProfile(profiles, selectedIndex)
                        # reset
                        return profiles, 'changeProf'
            navClickedButton = None
            # scroll?
            scrollClickedButton = scrollButtons.getClickedButton()
            if scrollClickedButton == scrollUpButton:
                firstProfileIndex -= 1
                if firstProfileIndex < 0:
                    firstProfileIndex = 0
            elif scrollClickedButton == scrollDownButton:
                firstProfileIndex += 1
                if firstProfileIndex > maxFirstProfileIndex:
                    firstProfileIndex = maxFirstProfileIndex
            scrollClickedButton = None
            profileButtons.setColor(BLACK)
            if profileSelected:
                if selectedIndex - firstProfileIndex not in range(len(profileButtons)):
                    profileSelected = False
                else:
                    profileButtons[selectedIndex - firstProfileIndex].setColor(WHITE)

def createNewProfile(profiles):
    '''width and height are of the textbox.
    Returns updated list of profiles.  Saves the profiles.'''
    entryRect = pygame.Rect(0, 0, 160, 24)
    entryRect.center = (HALF_WINWIDTH, HALF_WINHEIGHT) 
    entryBox = Button(entryRect, textColor=DOSGREEN, color=BLACK, highlightColor=None)
    entryBox.setFont(MSGFONT)


    newName = ''
    done = False
    messageShown = False
    while not done:
        checkForQuit()
        checkForToggleFullscreen()
        for event in pygame.event.get():
            if event.type == KEYDOWN:
                if event.key in (K_KP_ENTER, K_RETURN):
                    if len(newName) > 0:
                        done = True
                elif event.key in (K_BACKSPACE, K_DELETE):
                    if  len(newName) > 0:
                        newName = newName[:-1]
                elif len(newName) < 11:
                    if event.unicode not in (u'\r', u'\n', u'\t'):
                        newName += event.unicode
        DISPLAYSURF.fill(BGCOLOR)
        drawInLevelMessage('Type your name, then press ENTER to begin your training.', None, not messageShown)
        messageShown = True
        entryBox.setText(newName)
        entryBox.update(None, False)
        entryBox.draw(DISPLAYSURF)
        pygame.draw.rect(DISPLAYSURF, WHITE, entryRect, 1)
        pygame.display.update()
        FPSCLOCK.tick(FPS)


    profile = Profile({'name':      newName,
                       'tutLevel':      0,
                       'highestBlock':  -1,
                       'currentLevels': [0]})
    profiles.append(profile)
    saveProfilesFile(profiles, PROFILES_FILENAME)
    return profiles

def deleteProfile(profiles, index):
    '''Returns updated list of profiles.  Saves the profiles.'''
    fadeToColor(DARKGRAY, 300, False, 127)

    darkGrayWidth = 200
    darkGrayHeight = 100
    darkGrayRect = pygame.Rect(HALF_WINWIDTH - int(darkGrayWidth/2),
                               HALF_WINHEIGHT - int(darkGrayHeight/2),
                               darkGrayWidth,
                               darkGrayHeight)
    yesRect = pygame.Rect(darkGrayRect.left + int(darkGrayWidth/8),
                          darkGrayRect.bottom - int(darkGrayHeight/10)-28,
                          64,
                          28)
    cancelRect = yesRect.copy()
    cancelRect.right = darkGrayRect.right - int(darkGrayWidth/8)

    areYouSureSurf = BASICFONT.render('Are you sure?', True, BLACK)
    areYouSureRect = areYouSureSurf.get_rect(midbottom=(HALF_WINWIDTH, HALF_WINHEIGHT - 5))
    
    buttonColor = GRAY
    buttonTextColor = BLACK
    buttonClickedColor = WHITE
    yesButton = Button(yesRect, 'Yes', buttonTextColor, buttonColor, clickedColor=buttonClickedColor)
    cancelButton = Button(cancelRect, 'Cancel', buttonTextColor, buttonColor, clickedColor=buttonClickedColor)

    buttons = ButtonGroup([yesButton, cancelButton])

    mousePoint = None
    while True:
        mouseClicked = False
        clickedRect = None
       
        for event in pygame.event.get(): 
            if event.type == MOUSEMOTION:
                mousePoint = event.pos
            elif event.type == MOUSEBUTTONUP:
                mousePoint = event.pos
                mouseClicked = True

        pygame.draw.rect(DISPLAYSURF, DARKGRAY, darkGrayRect)
        buttons.update(mousePoint, mouseClicked)
        buttons.draw(DISPLAYSURF)
        DISPLAYSURF.blit(areYouSureSurf, areYouSureRect)

        pygame.display.update()
        FPSCLOCK.tick(FPS)
        if mouseClicked:
            clickedButton = buttons.getClickedButton()
            if clickedButton != None:
                if clickedButton == yesButton:
                    break
                elif clickedButton == cancelButton:
                    return profiles
    # they were sure
    profiles.pop(index)
    saveProfilesFile(profiles, PROFILES_FILENAME)
    return profiles

def showLevelSelectScreen(levelCount, profile):
    '''Returns the index of the level selected. (levelNum - 1)'''
    boxWidth = 150
    boxHeight = 50
    boxGap = int(boxWidth/2)

    numberOnScreen = 5

    xOffset = int((WINWIDTH - numberOnScreen*boxWidth - (numberOnScreen - 1)*boxGap)/2)
    yOffset = int((WINHEIGHT - boxHeight)/2)

    levelButtons = ButtonGroup([])
    x = xOffset
    for i in range(numberOnScreen):
        buttonRect = pygame.Rect(x, yOffset, boxWidth, boxHeight)
        levelButtons.add(Button(buttonRect))
        x += boxWidth + boxGap

    navButtons = ButtonGroup([])
    navWidth = int(xOffset/4)
    navHeight = int(boxHeight/2)
    leftRect = pygame.Rect(navWidth, HALF_WINHEIGHT - int(navHeight/2), navWidth, navHeight)
    rightRect = leftRect.copy()
    rightRect.right = WINWIDTH - navWidth
    leftButton = Button(leftRect, '<-', textColor=BLACK, color=WHITE, clickedColor=GRAY)
    rightButton = Button(rightRect,  '->', textColor=BLACK, color=WHITE, clickedColor=GRAY)
    navButtons.add(leftButton)
    navButtons.add(rightButton)

    changeProfRect = pygame.Rect(60, WINHEIGHT - 40, 150, 30)
    changeProfButton = Button(changeProfRect, 'Change Profile')
    navButtons.add(changeProfButton)

    nameSurf = BIGFONT.render(profile['name'], True, OFFWHITE)
    nameRect = nameSurf.get_rect(midbottom=changeProfRect.center)
    nameRect.bottom -= 20

    mousePoint = None
    levelIndex = None
    firstLevelIndex = profile['highestBlock'] + 1
    tutMessageShown = False
    levelMessageShown = False
    while True:
        mouseClicked = False
        checkForQuit()
        checkForToggleFullscreen()
        for event in pygame.event.get():
            if event.type == MOUSEMOTION:
                mousePoint = event.pos
            elif event.type == MOUSEBUTTONUP:
                mousePoint = event.pos
                mouseClicked = True

        DISPLAYSURF.fill(BGCOLOR)

        for i in range(len(levelButtons)):
            levelIndex = firstLevelIndex + i
            levelButtons[i].setText('Level %s' % (str(levelIndex + 1)))
            if profile.isLevelIndexUnlocked(levelIndex):
                if profile.isLevelIndexCompleted(levelIndex):
                    levelButtons[i].setColor(GREEN)
            else:
                levelButtons[i].setColor(GRAY)
                levelButtons[i].setClickedColor(GRAY)
        
        levelButtons.update(mousePoint, mouseClicked)
        navButtons.update(mousePoint, mouseClicked)
        levelButtons.draw(DISPLAYSURF)
        navButtons.draw(DISPLAYSURF)

        DISPLAYSURF.blit(nameSurf, nameRect)

        if firstLevelIndex < 14:
            # in tutorial levels
            drawInLevelMessage('The tutorial levels (1-15) must be completed in succession.  Green levels are completed, gray are locked, and blue are available.', None, not tutMessageShown)
            tutMessageShown = True
            levelMessageShown = False
        else:
            # out of tutorial
            drawInLevelMessage('Levels are unlocked in blocks of five.  Once you have completed all five in a block, the next block becomes available.  Green levels are completed, gray are locked, and blue are available.', None, not levelMessageShown)
            levelMessageShown = True
            tutMessageShown = False

        if mouseClicked:
            levelClickedButton = levelButtons.getClickedButton()
            if levelClickedButton != None:
                for i in range(len(levelButtons)):
                    if levelClickedButton == levelButtons[i] and profile.isLevelIndexUnlocked(firstLevelIndex + i):
                        return firstLevelIndex + i
            levelClickedButton = None
            # otherwise, other button?
            navClickedButton = navButtons.getClickedButton()
            if navClickedButton != None:
                if navClickedButton == rightButton:
                    firstLevelIndex += 5
                    if firstLevelIndex >= int(levelCount/5)*5:
                        firstLevelIndex = int(levelCount/5)*5
                elif navClickedButton == leftButton:
                    firstLevelIndex -= 5
                    if firstLevelIndex <= 0:
                        firstLevelIndex = 0
                elif navClickedButton == changeProfButton:
                    return 'changeProf'
            navClickedButton = None
        pygame.display.update()
        FPSCLOCK.tick(FPS)

        # reset levelButtons
        for i in range(len(levelButtons)):
            levelButtons[i].setColor(BLUE)
            levelButtons[i].setClickedColor(BLACK)

def readLevelsFile(filename):
    '''Based on function of the same name by Al S.
    Returns a list of levelDict's.'''
    assert os.path.exists(filename), 'Cannot find the level file: %s' % (filename)
    levelsFile = open(filename, 'r')
    content = levelsFile.readlines() + ['\r\n']
    levelsFile.close()

    buildingDict = {'red dish'  : ('w', '2', '1', 'q', 'a', 's'),
                    'blue dish' : ('r', '4', '3', 'e', 'd', 'f'),
                    'player'    : '@',
                    'wall'      : '#',
                    'goal'      : '*'}

    levels = [] # list of level dictionaries
    levelNum = 0
    boardTextLines = [] # lines for a single level's board
    levelMessages = [] # list of the messages to be displayed during the level
    # the messages are tuples (turnNumber, personSpeaking, message), and are in
    # chronological order
    for lineNum in range(len(content)):
        line = content[lineNum].rstrip('\r\n')

        if ';' in line:
            # ignore, comment
            line = line[:line.find(';')]

        if line != '':
            if '~' in line:
                # a message, remove the ~ and save the message
                # The format is
                # ~(turnNumber)[personSpeaking]Message to be given
                try:
                    turnNumber = int(line[line.find('(')+1:line.find(')')])
                    personSpeaking = line[line.find('[')+1:line.find(']')]
                except:
                    print 'Error in datafile %s, around line %s' % (filename, lineNum)
                    terminate()

                if personSpeaking == '':
                    personSpeaking = None
                message = line[line.find(']')+1:]
                levelMessages.append((turnNumber, personSpeaking, message))
            else:
                # part of the board
                boardTextLines.append(line)
        elif line == '' and len(boardTextLines) > 0:
            # blank lane -> end of a level's board

            height = len(boardTextLines)
            # find the longest row
            maxWidth = -1
            for i in range(len(boardTextLines)):
                if len(boardTextLines[i]) > maxWidth:
                       maxWidth = len(boardTextLines[i])

            # add spaces to the ends of the shorter rows
            for i in range(len(boardTextLines)):
                boardTextLines[i] += ' ' * (maxWidth - len(boardTextLines[i]))
            
            dishes = [] # list of dish tuples (tint, address, facing) in level
            playerAddress = None
            goalAddresses = [] # list of goal addresses
            wallAddresses = [] # list of wall addresses
            
            for x in range(maxWidth):
                for y in range(height):
                    char = boardTextLines[y][x]
                    if char == '@':
                        playerAddress = (x, y)
                    elif char in buildingDict['red dish']:
                        facing = buildingDict['red dish'].index(char)
                        dishes.append((REDTINT, (x, y), facing))
                    elif char in buildingDict['blue dish']:
                        facing = buildingDict['blue dish'].index(char)
                        dishes.append((BLUETINT, (x, y), facing))
                    elif char == '#':
                        wallAddresses.append((x, y))
                    elif char == '*':
                        goalAddresses.append((x, y))


            # basic level design sanity check
            assert playerAddress != None, 'Level %s (around line %s) in %s is missing a "@" to mark the start point.' % (levelNum+1, lineNum, filename)
            assert len(goalAddresses) > 0, 'Level %s (around line %s) in %s is missing a "*" to mark the goal.' % (levelNum+1, lineNum, filename)
            levelDict = {'width'    : maxWidth,
                         'height'   : height,
                         'wallAddresses'    : wallAddresses,
                         'goalAddresses'    : goalAddresses,
                         'playerAddress'    : playerAddress,
                         'dishes'   : dishes,
                         'messages' : levelMessages}

            levels.append(levelDict)

            # Reset variables for reading next board
            levelNum += 1
            boardTextLines = []
            levelMessages = []
            levelDict = {}

    return levels

def readProfilesFile(filename):
    '''Returns a list of profile objects.  Could be empty.
    In their dictionary:
    'name': profile name
    'tutLevel': level index they're on in the tutorial (0-14, 15 means done)
    'highestBlock': level index of the highest level from the last block of 5 unlocked
    'currentLevels': list of the level indices they have completed from their current block of 5'''
    if os.path.exists(filename):
        profilesFile = open(filename, 'r')
        content = profilesFile.readlines() + ['\r\n']
        profilesFile.close()

        profiles = []
        for line in content:
            line = line.rstrip('\r\n')
            if line != '':
                try:
                    profileList = line.split('_')
                    profileList[3] = profileList[3].split(',')
                
                    assert len(profileList) == 4, 'Error in datafile %s' % (filename)
                    keysList = ['name', 'tutLevel', 'highestBlock', 'currentLevels']
                    profileDict = dict.fromkeys(keysList)
                    profileDict['name'] = profileList[0]
                    profileDict['tutLevel'] = int(profileList[1])
                    profileDict['highestBlock'] = int(profileList[2])
                    profileDict['currentLevels'] = [int(levelNum) for levelNum in profileList[3]]
                except:
                    print 'Error in datafile %s' % (filename)
                    pygame.quit()
                    sys.exit()

                profiles.append(Profile(profileDict))
        return profiles
    else:
        return []

def saveProfilesFile(profiles, filename):
    '''Returns True when done.'''
    profilesFile = open(filename, 'w')
    for profile in profiles:
        line = '_'.join((profile['name'], str(profile['tutLevel']), str(profile['highestBlock']), ','.join(map(str, profile['currentLevels'])))) + '\n'
        profilesFile.write(line)
    profilesFile.close()
    return True

def checkForQuit():
    for event in pygame.event.get(QUIT): # get all the QUIT events
        terminate() # terminate if any QUIT events are present
    for event in pygame.event.get(KEYDOWN): # get all the KEYDOWN events
        if event.key == K_ESCAPE:
            terminate() # terminate if the KEYDOWN event was for the Esc key
        else:
            pygame.event.post(event) # put the other KEYDOWN event objects back

def checkForToggleFullscreen():
    global DISPLAYSURF
    for event in pygame.event.get(KEYDOWN):
        if event.key == K_RETURN and (event.mod&(KMOD_LALT|KMOD_RALT)) != 0:
            DISPLAYSURF = toggleFullscreen()
        else:
            pygame.event.post(event)

def toggleFullscreen():
    '''Toggles between fullscreen and windowed mode.  From pygame.org cookbook.'''
    screen = pygame.display.get_surface()
    tmp = screen.convert()
    caption = pygame.display.get_caption()
    cursor = pygame.mouse.get_cursor()  # Duoas 16-04-2007 
    
    w,h = screen.get_width(),screen.get_height()
    flags = screen.get_flags()
    bits = screen.get_bitsize()
    
    pygame.display.quit()
    pygame.display.init()
    
    screen = pygame.display.set_mode((w,h),flags^FULLSCREEN,bits)
    screen.blit(tmp,(0,0))
    pygame.display.set_caption(*caption)
 
    pygame.key.set_mods(0) #HACK: work-a-round for a SDL bug??
 
    pygame.mouse.set_cursor( *cursor )  # Duoas 16-04-2007
    
    return screen

def fadeToColor(fadeColor, fadetime, fadeBack=False, endAlpha=255):
    '''Fades to the color over the fadetime (in milliseconds).
        Optional boolean can make it fade back to the original screen afterward.'''
    alphaRanges = [(0, endAlpha, 1)]
    if fadeBack:
        alphaRanges.append((endAlpha, 0, -1))

    oldScreen = DISPLAYSURF.copy()
    overlay = DISPLAYSURF.copy()
    for (start, end, multiplier) in alphaRanges:
        for a in range(start, end, multiplier*int(255/(fadetime*FPS/1000))):
            overlay.fill(fadeColor)
            overlay.set_alpha(a)
            DISPLAYSURF.blit(oldScreen, (0, 0))
            DISPLAYSURF.blit(overlay, (0, 0))
            pygame.display.update()
            FPSCLOCK.tick(FPS)

def terminate():
    fadeToColor(BLACK, 1000, False, 127)

    darkGrayWidth = 200
    darkGrayHeight = 100
    darkGrayRect = pygame.Rect(HALF_WINWIDTH - int(darkGrayWidth/2),
                               HALF_WINHEIGHT - int(darkGrayHeight/2),
                               darkGrayWidth,
                               darkGrayHeight)
    yesRect = pygame.Rect(darkGrayRect.left + int(darkGrayWidth/8),
                          darkGrayRect.bottom - int(darkGrayHeight/10)-28,
                          64,
                          28)
    cancelRect = yesRect.copy()
    cancelRect.right = darkGrayRect.right - int(darkGrayWidth/8)

    areYouSureSurf = BASICFONT.render('Quit?', True, BLACK)
    areYouSureRect = areYouSureSurf.get_rect(midbottom=(HALF_WINWIDTH, HALF_WINHEIGHT - 5))
    
    buttonColor = GRAY
    buttonTextColor = BLACK
    buttonClickedColor = WHITE
    yesButton = Button(yesRect, 'Yes', buttonTextColor, buttonColor, clickedColor=buttonClickedColor)
    cancelButton = Button(cancelRect, 'Cancel', buttonTextColor, buttonColor, clickedColor=buttonClickedColor)

    buttons = ButtonGroup([yesButton, cancelButton])

    mousePoint = None
    while True:
        mouseClicked = False
        clickedRect = None
                                                               
        for event in pygame.event.get(): 
            if event.type == MOUSEMOTION:
                mousePoint = event.pos
            elif event.type == MOUSEBUTTONUP:
                mousePoint = event.pos
                mouseClicked = True

        pygame.draw.rect(DISPLAYSURF, DARKGRAY, darkGrayRect)
        buttons.update(mousePoint, mouseClicked)
        buttons.draw(DISPLAYSURF)
        DISPLAYSURF.blit(areYouSureSurf, areYouSureRect)

        pygame.display.update()
        FPSCLOCK.tick(FPS)
        if mouseClicked:
            clickedButton = buttons.getClickedButton()
            if clickedButton != None:
                if clickedButton == yesButton:
                    break
                elif clickedButton == cancelButton:
                    return
    pygame.quit()
    sys.exit()
       
if __name__ == '__main__':
    main()
