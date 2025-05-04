from ursina import *
import math
from ursina import Button 

app = Ursina()

class Ground(Entity):
    def __init__(self, position, scale, color):
        super().__init__(model='cube', scale=scale, collider='box', color=color, position=position)

    def destroy(self):
        self.disable()
class Wall(Entity):
    def __init__(self, position, scale, color):
        super().__init__(model='cube', scale=scale, collider='box', color=color, position=position)

    def destroy(self):
        self.disable()

class Tint(Entity):
    def __init__(self):
        super().__init__(
                model='Quad',
                scale=(2, 2),  # Adjust scale to fit the camera view
                color=color.rgba(255, 0, 0, 0.2),  # Red with 50% opacity
                parent=camera.ui,  # Attach to the camera's UI layer
                enabled=True
            )

col1 = color.black
col2 = color.gray
col3 = color.red
zTelPos = [
    [0, 0, 4],
    [0, 0, 2],
    [0, 0, 0],
    [0, 0, -2],
    [0, 0, -4]
]
# Create walls
walls = [
    Wall(position=(4.5, 0.5, 0), scale=(1, 2, 1), color=col1),
    Wall(position=(-3, 2, 0), scale=(1, 5, 10), color=col3),
]

# Create ground
ground = [
    Ground(position=(zTelPos[0]), scale=(60, 1, 2), color = col1),
    Ground(position=(zTelPos[1]), scale=(60, 1, 2), color = col2),
    Ground(position=(zTelPos[2]), scale=(60, 1, 2), color = col1),
    Ground(position=(zTelPos[3]), scale=(60, 1, 2), color = col2),
    Ground(position=(zTelPos[4]), scale=(60, 1, 2), color = col1)
]

time.sleep(2)
# Player entity with a collider
player = Entity(model='cube', color=color.orange, scale=(1, 1, 1), collider='box', position=(0, 5, 0))

# Gravity and movement variables
gravity = -39.2  # Gravity acceleration
velocity = 0
is_grounded = False

camera.position = Vec3(-20, 20, -20)  # Initial camera position
camera.rotation = Vec3(0, 45, 0) #Initial camera rotation
camera.look_at(player.position) # Initial look at
return_rotation = Vec3(0, 45, 0)
return_speed = 5
camera_loc = player.position + Vec3(-20, 20, -20)
movementkeyz = None
camfollowspd = 2

currentztelpos = 2
def input(key):
    global currentztelpos
    if key == 's':
        if currentztelpos == 4:
            # Create a semi-transparent red tint
            tint = Tint()
            camera.shake(duration=0.5)
            invoke(tint.disable, delay=0.5)  # Disable the tint after the shake duration
        else:
            currentztelpos += 1
        # position shifts one lane further away from the camera
        # if at the furthest possible lane, instead stay in the same place
    if key == 'w':
        if currentztelpos == 0:
            # Create a semi-transparent red tint
            tint = Tint()
            camera.shake(duration=0.5)
            invoke(tint.disable, delay=0.5)  # Disable the tint after the shake duration
        else:
            currentztelpos -= 1
        # position shifts one lane closer to camera
        # if at the closest possible lane, instead stay in the same place
    player.z = zTelPos[currentztelpos][2]
    
def update():
    global velocity, is_grounded, return_speed, return_rotation, camera_loc, movementkeyz, camfollowspd
    return_location = player.position + Vec3(-20, 20, -20)
    # Horizontal movement
    move_x = (held_keys['d'] - held_keys['a']) * time.dt * 5

    # Check for collisions before moving
    player.x += move_x

    # Jumping
    if is_grounded and held_keys['space']:
        velocity = 15  # Jump velocity

    # Apply gravity
    velocity += gravity * time.dt
    player.y += velocity * time.dt

    # Ground collision
    is_grounded = False
    for g in ground:
        hit_info = player.intersects(g)
        if hit_info.hit:
            player.y = g.world_y + g.scale_y  # Place player on top of the ground
            velocity = 0
            is_grounded = True
            break
    
    # Wall collision
    for wall in walls:
        hit_info = player.intersects(wall)
        if hit_info.hit:
            wall_top_y = wall.world_y + wall.scale_y / 2  # Calculate the top of the wall
            if player.y > wall_top_y + 0.3:  # Ensure the player is above the wall
                player.y = wall_top_y + player.scale_y / 2  # Place player on top of the wall
                velocity = 0
                is_grounded = True
            else:
                # Undo movement if side collision occurs
                player.x -= move_x
            break

    # Camera movement logic
    if mouse.left:  # Check if the left mouse button is held
        # Update the camera location continuously based on mouse movement
        camera_loc.x -= mouse.velocity[0] * return_speed * 1000 * time.dt
        camera_loc.y += mouse.velocity[1] * return_speed * 1000 * time.dt
        camera.position = camera_loc  # Apply the updated location immediately
    else:
        # Smoothly return the camera to its original position
        camera_loc = lerp(camera_loc, return_location, time.dt * return_speed)
        camera.position = camera_loc

        camerarot = camera.rotation
        camera_rot = lerp(camerarot, return_rotation, time.dt * return_speed)
        camera.rotation = camera_rot 

    camera.look_at(player.position)
        


app.run()