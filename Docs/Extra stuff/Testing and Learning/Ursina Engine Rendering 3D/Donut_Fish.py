from ursina import *

app = Ursina()

player = Entity(model='Donut_Practice.blend', texture='FISH/fish_texture.png', scale_y=2)
axisnum = 0  # Tracks the current axis (0 for x, 1 for y, 2 for z)

def update():
    player.x += held_keys['d'] * time.dt
    player.x -= held_keys['a'] * time.dt
    player.y += held_keys['w'] * time.dt
    player.y -= held_keys['s'] * time.dt
    player.z += held_keys['q'] * time.dt
    player.z -= held_keys['e'] * time.dt


def input(key):
    global axisnum
    axes = ['x', 'y', 'z']  # List of axes to cycle through

    if key == 'space':  # Cycle through axes
        axisnum = (axisnum + 1) % 3
        print(f"Current axis: {axes[axisnum]}")  # Debugging output to show the selected axis

    current_axis = axes[axisnum]  # Get the current axis based on axisnum

    if key == 'x':  # Rotate positively on the selected axis
        invoke(setattr, player, f'rotation_{current_axis}', getattr(player, f'rotation_{current_axis}') + 90)

    if key == 'c':  # Rotate negatively on the selected axis
        invoke(setattr, player, f'rotation_{current_axis}', getattr(player, f'rotation_{current_axis}') - 90)
        


app.run()