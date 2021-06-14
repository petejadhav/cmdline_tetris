import numpy as np
import time
import sys
import os
#import threading
import queue
import random
import copy
from kbhit import KBHit

# TODO - 
# at higher speeds post-collision revert leads to gaps in rows
# continuous key presses
class Tetris():
    """
    Tetris in the terminal.
    Notes:
    Handling is Row major.

    Functions:
    render, input_loop, run, blit_screen, clear, update -> move_obj,rotate_obj

    Classes:
    Object
    """
    def __init__(self, screen_width, screen_height):
        self.logger = open("game.log",'w')
        self.width, self.height = screen_width+2, screen_height+2
        self.min_speed = 1 # Rows per second
        self.max_speed = 3
        self.curr_speed = self.min_speed
        self.score = 0

        # Create Play Canvas
        self.screen = np.array([[' '] * self.width] * self.height)
        # Print Boundary delineators
        self.ground_chars = ['=','\\','/']
        self.wall_char = '|'
        self.screen[0,:] = '='
        self.screen[(self.height - 1),:] = '='
        self.screen[:,0] = self.wall_char
        self.screen[:,(self.width-1)] = self.wall_char
        # Print corners
        self.screen[0,0], self.screen[0,(self.width-1)], self.screen[(self.height-1),(self.width-1)], self.screen[(self.height-1),0] = '/','\\','/','\\' 
        

        self.input_queue = queue.Queue()
        self.game_running = False
        self.input_controls = {'s':'down', 'a':'left', 'd':'right', 'w':'up', 'e':'clockwise', 'q':'anti_clockwise'}
        
        self.block_char = 'X'
        self.block_objs = {
            'I' : np.array([self.block_char] * 4).reshape((1,4)),
            'J' : np.vstack(([self.block_char, ' ', ' ', ' '], [self.block_char] * 4)),
            'L' : np.vstack(([' ', ' ', ' ', self.block_char], [self.block_char] * 4)),
            'O' : np.vstack(([self.block_char] * 2, [self.block_char] * 2)),
            'S' : np.vstack(([' ',self.block_char,self.block_char], [self.block_char,self.block_char, ' '])),
            'Z' : np.vstack(([self.block_char,self.block_char, ' '], [' ',self.block_char,self.block_char])),
            'T' : np.vstack(([' ',self.block_char, ' '], [self.block_char,self.block_char,self.block_char]))
        }
        self.block_object_types = list(self.block_objs.keys())

        self.spawn_pos = np.array([1, self.width//2])
        self.active_obj = {
            'pos' : self.spawn_pos.copy(),
            'type' : None,
            'arr' : []
        }
        # self.input_thread = threading.Thread(target=self.input_loop)
        # self.input_thread.daemon = True
        self.last_render_timestamp = self.get_timestamp()

        # Keyboard handler
        self.keyboard = KBHit()

    def log(self, string):
        self.logger.write(string + '\n')

    def get_timestamp(self):
        return int(time.time()*1000)

    def clear(self):  
        # for windows
        if os.name == 'nt':
            _ = os.system('cls')    
        # for mac and linux(here, os.name is 'posix')
        else:
            _ = os.system('clear')

    def blit_screen(self,pos,arr):
        # pos refers to top-left corner of array
        bound = arr.shape
        self.screen[pos[0]:(pos[0]+bound[0]), pos[1]:(pos[1]+bound[1])] = arr.copy()

    def blit_object(self, pos, arr, clear=False):
        # clear flag used to clear object from screen
        # pos refers to top-left corner of array
        arr = arr.copy()
        bound = arr.shape
        #for i, row in enumerate(self.screen[pos[0]:(pos[0]+bound[0]), pos[1]:(pos[1]+bound[1])]):
        for i in range(bound[0]):
            #for j, cell in enumerate(row):
            for j in range(bound[1]):
                if arr[i,j] != ' ':
                    if clear: arr[i,j] = ' '
                    self.screen[(pos[0]+i),(pos[1]+j)] = arr[i,j]
                
    def render(self):
        self.clear()
        print("SCORE -",self.score,"  Use A D for left/right. Q E to rotate. W S to speed up/down")
        for row in self.screen:
            print(*row)
        print("Press ESC to quit.")
        self.last_render_timestamp = self.get_timestamp()

    def update(self, delta, input):
        # Save curr pos of active obj
        active_obj_prev_data = copy.deepcopy(self.active_obj)
        # Clear curr_pos of active obj using blit_screen
        #self.blit_screen(self.active_obj['pos'] , np.full_like(self.active_obj['arr'],' '))
        self.blit_object(self.active_obj['pos'], self.active_obj['arr'], clear=True)

        # HANDLE INPUT : calc. new pos using input & delta -> check if moving out of screen
        if input == 'anti_clockwise':
            self.active_obj['arr'] = np.rot90(self.active_obj['arr'],1)
        if input == 'clockwise':
            self.active_obj['arr'] = np.rot90(self.active_obj['arr'],-1)
        if input == 'up':
            self.curr_speed = max(self.min_speed, (self.curr_speed-1))
        if input == 'down':
            self.curr_speed = min(self.max_speed, (self.curr_speed+1))
        if input == 'left':
            self.active_obj['pos'][1] -= 1
        if input == 'right':
            self.active_obj['pos'][1] += 1
        
        self.active_obj['pos'][0] += self.curr_speed 
        
        # Check for collisions and boundary conditions
        collisionChar = self.check_collision()
        if collisionChar != '':
            # revert to prev pos
            self.active_obj = copy.deepcopy(active_obj_prev_data)
            # check if there are complete rows & update score
            completed_rows = self.check_rows()
            self.score += len(completed_rows)
            # Clear complete rows, bring the upper rows down
            if len(completed_rows) > 0:
                for i in completed_rows:
                    # shift upper rows down by 1 row
                    self.blit_screen([2,1], self.screen[1:i,1:-1])
                    # Fill Empty row at top - NOT NEEDED
                    #self.blit_screen([1,1], [' '*(self.width-2)])
            if (collisionChar =='g') or (collisionChar == self.block_char):
                # Blit old obj to screen before spawning new obj
                self.blit_object(self.active_obj['pos'] , self.active_obj['arr'])
                self.spawn_new_block_obj()

        # Write active_obj to new_pos using blit_screen
        self.blit_object(self.active_obj['pos'] , self.active_obj['arr'])
        return 

    def input_loop(self):
        while self.game_running:
            self.input_queue.put(sys.stdin.read(1))
        return

    def check_collision(self):
        # If overlap with 'X' or boundary_chars then true
        shape = self.active_obj['arr'].shape
        pos = self.active_obj['pos']

        for i,row in enumerate(self.screen[pos[0]:(pos[0]+shape[0]), pos[1]:(pos[1]+shape[1])]):
            for j,cell in enumerate(row):
                if self.active_obj['arr'][i,j] == ' ':
                    # if block obj has a space, ignore it
                    continue
                if cell == self.block_char:
                    return self.block_char
                if cell == self.wall_char: return self.wall_char
                if cell in self.ground_chars: 
                    return 'g'                
        return ''

    def check_rows(self):
        # TODO : Check only rows where obj is present after collision
        completed_rows = []
        for i, row in enumerate(self.screen[1:-1,1:-1]):
            s = sum([1 for cell in row if cell == self.block_char])
            if s == len(row): completed_rows.append(i)
        return completed_rows
    
    def cleanup(self):
        #self.input_thread.stop()
        print("Game Ended. Score:",self.score)
        self.logger.close()

    def spawn_new_block_obj(self):
        self.log("spawning")
        self.active_obj['type'] = random.choice(self.block_object_types)
        self.active_obj['pos'] = self.spawn_pos.copy()
        self.active_obj['arr'] = self.block_objs[self.active_obj['type']].copy()

    def run(self):
        try:
            self.clear()
            self.game_running=True
            #self.input_thread.start()
            while self.game_running:

                curr_input = ''
                if self.keyboard.kbhit():
                    c = self.keyboard.getch()
                    if ord(c) == 27: # ESC
                        break
                    self.input_queue.put(c)

                if not self.input_queue.empty():
                    curr_input = self.input_controls.get(self.input_queue.get())

                # Create new object
                if self.active_obj['type'] == None:
                    self.spawn_new_block_obj()                

                # Quit game
                if curr_input == 'esc':
                    self.game_running = False
                    self.cleanup()
                
                self.update(self.get_timestamp()-self.last_render_timestamp, curr_input)
                self.render()
                time.sleep(0.2)
        except Exception as e:
            print(e)
        finally:
            self.game_running = False
            self.cleanup()


