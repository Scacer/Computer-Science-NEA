import pygame
import random
from enum import Enum
import time
import tensorflow as tf

pygame.font.init()

# global variables


# AI Global Variables
MAX_MEMORY = 100_000
BATCH_SIZE = 1000
LR = 0.001

SPEED = 20 # Sets game speed.

################################################################################
################################################################################

# This class uses Enum to predefine constants for directions later in the program
class Direction(Enum):
    RIGHT = 1
    LEFT = 2
    UP = 3
    DOWN = 4

################################################################################
################################################################################

class Piece():

    # Shapes stored as Arrays, 0s represent empty space, anything else represents
    # a block.
    pieces = [
        [[1, 1, 0],
         [0, 1, 1]], # Z

        [[0, 2, 2],
         [2, 2, 0]], # S

        [[3],
         [3],
         [3],
         [3]],        # I

        [[4, 4],
         [4, 4]],     # O

        [[5, 0, 0],
         [5, 5, 5]],  # J

        [[0, 0, 6],
         [6, 6, 6]],  # L

        [[0, 7, 0],
         [7, 7, 7]]  # T
    ]

    piece_colours = [
        (255, 255, 106),
        (255, 255, 0),
        (147, 88, 254),
        (54, 175, 144),
        (255, 0, 0),
        (102, 217, 238),
        (254, 151, 32),
        (0, 0, 255)
    ]
    
    # When creating a piece object, a random piece identifer 0 - 6 is created.
    # This value is then used to index the pieces array such that a random
    # piece may be chosen.
    # Due to the design of the piece_colours array, this means that the same index
    # can be used to ensure the pieces' colours remain consistent.
    def __init__(self, piece_id):
        if piece_id == -1:
            piece_id = random.randint(0, 6)
        
        self.piece = Piece.pieces[piece_id]
        self.colour = Piece.piece_colours[piece_id]
        self.x = 4
        self.y = len(self.piece) - 1
        self.piece_id = piece_id

    # The function inverts the number of rows and columns by assigning them to
    # new variables, and then creating each new row based on the information of
    # the existing piece.
    def rotate(self):
        piece = self.piece
        # Checks to ensure the piece is not an O piece, as the O piece has
        # no rotations.
        if self.piece_id != 3:
            # Rotates once for clockwise rotation.
            num_rows = num_cols_new = len(piece)
            num_rows_new = len(piece[0])
            rotated_piece = []

            for i in range(0, num_rows_new):
                new_row = [0] * num_cols_new
                for j in range(0, num_cols_new):
                    new_row[j] = piece[(num_rows-1) - j][i]
                rotated_piece.append(new_row)
        else:
            return self.piece

        return rotated_piece

################################################################################
################################################################################

class Tetris():
        
    def __init__(self, mode):

        if mode == 'player':
            self.SPEED = 20
        elif mode == 'machine': 
            self.SPEED = 2      #The game is sped up by a factor of 10 if machine learning is used.
        self.WIDTH = 300
        self.HEIGHT = 720
        self.BLOCK_SIZE = 30 # Used for drawing later in the program
        self.PLAY_AREA_START = 120 # Combined with BLOCK_SIZE, this allows for blocks for
                                   # graphics above the play area.
        self.display = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption('Tetris')
        self.clock = pygame.time.Clock()
        self.reset()

    def reset(self):

        # Initialises the grid, making it entirely empty
        self.locked_positions = {}
        self.grid = self._create_grid()
        self.score = 0
        self.level = 0
        self.next_level = 4
        self.lines_cleared = 0
        self.fall_speed = 0.1
        self._draw_window()

        self.change_piece = False
        self.current_piece = Piece(-1)
        self.fall_time = 0
        self.direction = None

    def step(self, move=None):
        reward = 0
        # Recreates the grid each step in case new "blocks" in the grid are locked
        self.grid = self._create_grid(self.locked_positions)

        #1. Check Move input
        self.direction = self._determine_move(move)

        self._move(self.direction) # moves the piece
        
        self.shape_pos = self._shape_reformat(self.current_piece.piece)

        # Adds the the colours for blocks to the grid for the shape as it enters the screen
        for i in range(len(self.shape_pos)):
            x, y, = self.shape_pos[i]
            # If a part of the shape is above the screen, it will not be drawn.
            if y > -1 and y < 20:
                self.grid[y][x] = self.current_piece.colour
            elif y > 20:
                self.change_piece = True


        # Adds location and colour data to the locked_positions array for use in grid creation
        if self.change_piece:
            for pos in self.shape_pos:
                p = (pos[0], pos[1])
                self.locked_positions[p] = self.current_piece.colour
            # Changes over the pieces
            self.current_piece = Piece(-1)
            is_rowsCleared = self._clear_rows()
            if is_rowsCleared:
                reward = 10
            self.change_piece = False
        

        if self._is_gameOver(self.locked_positions):
            reward = -10
            self.reset()

        # get_rawtime() gets the time elapsed since the last clock tick, giving us a CPU relative
        # measurement in order to determine fps.
        self.fall_time += self.clock.get_rawtime()
        self.clock.tick(SPEED)
        self._draw_window()
        self._is_pieceDrop()

        height = self._get_height()
        
        return reward, height, self.shape_pos, self.locked_positions

    # create_grid takes a dictionary as an argument which will be used for
    # identifying which blocks should not be changed when drawing each frame
    def _create_grid(self, locked_pos = {}):

        # Creates 20 Sublists of 10 Colours for drawing the rows for tetris
        grid = [[(0, 0, 0) for x in range(10)] for x in range(20)]

        for i in range(len(grid)):
            for j in range(len(grid[i])):
                # j represents the column, and i represents the row
                # this loop ensures that if a value in the grid has already
                # been marked as locked in locked_pos, the empty space will
                # be overridden, and the correct grid data will be written.
                if (j, i) in locked_pos:
                    locked_value = locked_pos[(j, i)]
                    grid[i][j] = locked_value
        return grid

    def _draw_grid(self, grid):

        for i in range(len(grid)):
            for j in range(len(grid[i])):
                # In order this line, sets the X co-ordinate, sets the Y co-ordinate
                # sets the rectangle width, sets the rectangle height, sets the
                # fill to full.
                pygame.draw.rect(self.display, grid[i][j], ((0 + j * self.BLOCK_SIZE), (self.PLAY_AREA_START + i * self.BLOCK_SIZE), self.BLOCK_SIZE, self.BLOCK_SIZE), 0)
        # Draws the playable area Border
        pygame.draw.rect(self.display, (211,211,211), (0, self.PLAY_AREA_START, 300, 600), 4)
        self._draw_gridLines()
        pygame.display.flip()

    def _draw_window(self):

        self.display.fill((0, 0, 0))
        # Creates a label to display the title of 'Tetris'
        pygame.font.init()
        font = pygame.font.SysFont('fixedsys', 30)
        scoreString = 'Score: ' + str(self.score)
        levelString = 'Level: ' + str(self.level)
        lineString = 'Lines Cleared: ' + str(self.lines_cleared)
        label = font.render('tetris', 1, (255, 255, 255))
        score_label = font.render(scoreString, 1, (255, 255, 255))
        level_label = font.render(levelString, 1, (255, 255, 255))
        lines_label = font.render(lineString, 1, (255, 255, 255))

        self._draw_grid(self.grid)

        # Places the label at the correct position.
        self.display.blit(label, ((self.WIDTH / 2) -  (label.get_width() / 2), (self.PLAY_AREA_START / 4) - (label.get_height() / 2)))
        self.display.blit(score_label, (0, 0))
        self.display.blit(level_label, (self.WIDTH - level_label.get_width(), 0))
        self.display.blit(lines_label, ((self.WIDTH / 2) -  (lines_label.get_width() / 2), (self.PLAY_AREA_START / 2) - (lines_label.get_height() / 2)))
        # Updates the pygame window with the newly drawn frame.
        pygame.display.flip()

    def _draw_gridLines(self):
        x = 0
        y = self.PLAY_AREA_START

        for i in range(len(self.grid)):
            # Draws the Horizontal grid lines.
            pygame.draw.line(self.display, (128, 128, 128), (x, y + i * self.BLOCK_SIZE), (x + self.WIDTH, y + i * self.BLOCK_SIZE))
            for j in range(len(self.grid[i])):
                # Draws the Vertical grid lines.
                pygame.draw.line(self.display, (128, 128, 128), (x + j * self.BLOCK_SIZE, y), (x + j * self.BLOCK_SIZE, y + 600))


    def _move(self, direction):

        # Ensures the movement is valid, if so the piece will move into its
        # new position.
        if not self.change_piece:
            if direction == Direction.RIGHT:
                self.current_piece.x += 1
                if not(self._valid_space(self.current_piece.piece)):
                    self.current_piece.x -= 1
            elif direction == Direction.LEFT:
                self.current_piece.x -= 1
                if not(self._valid_space(self.current_piece.piece)):
                    self.current_piece.x += 1
            elif direction == Direction.DOWN:
                self.current_piece.y += 1
                # Ensures the user does not encounter a "double drop" where the piece
                # drops a second time immediately after pressing down
                if not(self._valid_space(self.current_piece.piece)):
                    self.current_piece.y -= 1
            elif direction == Direction.UP:
                pre_rotation = self.current_piece.piece
                self.current_piece.piece = self.current_piece.rotate()
                if not(self._valid_space(self.current_piece.piece)):
                    self.current_piece.piece = pre_rotation

    def _shape_reformat(self, shape):
        positions = []
        #Creates a list containing the co-ordinates for which the shape exists.
        for i in range(0, len(shape)):
            for j in range(0, len(shape[i])):
                if shape[i][j] != 0:
                    positions.append((self.current_piece.x + j, self.current_piece.y + i))
                           
        # As it currently exists, the array contains co-ordinates relative to their
        # own data structure, not the grid. The loop below fixes this.
        for i, pos in enumerate(positions):
            positions[i] = (pos[0], pos[1] - len(shape))
        return positions

    def _valid_space(self, shape):
        grid = self._create_grid(self.locked_positions)

        # Creates a 2-Dimensional list representing the grid's accepted (empty) positions.
        valid_pos = [[(j, i) for j in range(10) if grid[i][j] == (0, 0, 0)] for i in range(20)]
        # Converts the 2-Dimensional array into a 1D array for easy reading.
        valid_pos = [j for sub in valid_pos for j in sub]

        formatted = self._shape_reformat(self.current_piece.piece)

        # Checks to ensure the piece is within bounds of the grid
        for i in formatted:
            f_tuple = i
            x, y = f_tuple
            if x > 9:
                return False
            elif x < 0:
                return False
            elif y > 19:
                return False
            elif f_tuple not in valid_pos and y > -1:
                return False
            
        return True

    def _is_gameOver(self, positions):

        for pos in positions:
            x, y = pos
            if y < 1:
                return True

        return False

    def _is_pieceDrop(self):
        # Checks each tick to see if enough time has elapsed for the current piece to drop
        if self.fall_time / 1000 > self.fall_speed:
            # Resets fall_time so that the next drop  can be calculated
            self.fall_time = 0
            self.current_piece.y += 1
            # Prevents downward movement from occuring if it causes the piece to
            # move into an invalid space.
            if not(self._valid_space(self.current_piece.piece)) and self.current_piece.y > 0:
                self.current_piece.y -= 1
                # Will indicate on the next step() iteration that the piece needs to be
                # locked in place and the next one needs to be spawned.
                self.change_piece = True

    def _clear_rows(self):
        # need to see if row is clear the shift every other row above down one
        is_clearedRows = False
        cleared_rows = 0
        inc = 0
        for i in range(len(self.grid)-1,-1,-1):
            row = self.grid[i]
            if (0, 0, 0) not in row:
                cleared_rows += 1
                self.lines_cleared += 1
                inc += 1
                # add positions to remove from locked
                ind = i
                for j in range(len(row)):
                    try:
                        del self.locked_positions[(j, i)]
                    except:
                        continue
        if inc > 0:
            for key in sorted(list(self.locked_positions), key=lambda x: x[1])[::-1]:
                x, y = key
                if y < ind:
                    newKey = (x, y + inc)
                    self.locked_positions[newKey] = self.locked_positions.pop(key)

        if cleared_rows > 0:
            is_clearedRows = True
                    
        self._calcScore(cleared_rows, self.level)
        return is_clearedRows

    def _calcScore(self, noRowsCleared, level):
        if noRowsCleared == 1:
            base_score = 40
        elif noRowsCleared == 2:
            base_score = 100
        elif noRowsCleared == 3:
            base_score = 300
        elif noRowsCleared == 4:
            base_score = 1200
        else:
            base_score = 0
        self.score += base_score * (level + 1)

        self._is_levelIncrement(self.lines_cleared)

    def _is_levelIncrement(self, rows_cleared):
        if rows_cleared >= self.next_level:
            self.level += 1
            self.next_level += 5
            self.fall_speed *= 0.9

    def _get_height(self):
        height = 0
        locked_pos = list(self.locked_positions)
        for i in range(0, len(locked_pos)):
            y = locked_pos[i][1]
            index_height = 19 - y
            if height < index_height:
                height = index_height
        return height
                
    def _determine_move(self, move):
        translated_move = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN and move == None:
                if event.key == pygame.K_LEFT:
                   translated_move = Direction.LEFT
                elif event.key == pygame.K_RIGHT:
                    translated_move = Direction.RIGHT
                elif event.key == pygame.K_UP:
                    translated_move = Direction.UP
                elif event.key == pygame.K_DOWN:
                    translated_move = Direction.DOWN
            else:
                if move == [1, 0, 0, 0]:
                    translated_move = Direction.UP
                elif move == [0, 1, 0, 0]:
                    translated_move = Direction.RIGHT
                elif move == [0, 0, 1, 0]:
                    translated_move = Direction.LEFT
                elif move == [0, 0, 0, 1]:
                    translated_move = Direction.DOWN

        return translated_move
            
###################################################
###################################################
class Agent():

    def __init__(self, episodes, max_steps, learning_rate, gamma, epsilon):
        self.episodes = epsiodes
        self.max_steps = max_steps
        self.alpha = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon #The probability of choosing a random action
        self.game = Tetris('machine')

    def get_state(self, game):
        pass

    def remember(self, state, action, reward, next_state, done):
        pass

    def train_long_memory(self):
        pass

    def train_short_memory(self):
        pass

    def get_action(self, state):
        pass

def setReinforcementVariables():
    pass

def getReinforcementVariables():
    with open("variables.rl", 'r') as f:
        lines = f.readlines()
        episodes = lines[0]
        max_steps = lines[1]
        learning_rate = lines[2]
        discount_factor = lines[3]
        epsilon = lines[4]
    return episodes, max_steps, learning_rate, discount_factor, epsilon
            


###################################################
###################################################

class Model():

    def __init__(self):
        pass
    
                
if __name__ == '__main__':
    temp = input("yos")
    if temp == 'play':
        game = Tetris('player')
        while True:
            reward, height, posit, locked_posit = game.step()

    elif temp == 'train':
        episodes, max_steps, learning_rate, discount_factor, epsilon = getReinforcementVariables()
        Agent = Agent(episodes, max_steps, learning_rate, discount_factor, epsilon)

    else:
        quit()

    #game loop
    
