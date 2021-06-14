import numpy as np

def render(screen):
    for row in screen:
        print(*row)

width, height = 62,102

# Create Play Canvas
screen = np.array([[' '] * width] * height)
# Print Boundariy delineators
screen[0,:] = '_'
screen[(height - 1),:] = '_'
screen[:,0] = '|'
screen[:,(width-1)] = '|'
# Print corners
screen[0,0], screen[0,(width-1)], screen[(height-1),(width-1)], screen[(height-1),0] = '/','\\','/','\\' 