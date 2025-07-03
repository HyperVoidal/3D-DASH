from ursina import *
import math
from ursina import Button 

app = Ursina()

# Player entity with a collider
player = Entity(model='cube', color=color.orange, scale=(1, 1, 1), collider='box', position=(0, 10, 0))

class Ground(Entity):
    def __init__(self, position, scale):
        super().__init__(model='cube', scale=scale, collider='box', color=color.black, position=position)

    def destroy(self):
        self.disable()
class Wall(Entity):
    def __init__(self, position):
        super().__init__(model='cube', scale=(1, 2, 1), collider='box', color=color.red, position=position)

    def destroy(self):
        self.disable()


# Create walls
walls = [
    Wall(position=(5, 1, 0)),
    Wall(position=(-5, 1, 0)),
    Wall(position=(0, 1, 5)),
    Wall(position=(0, 1, -5)),
]

# Create ground
ground = [
    Ground(position=(0, 0, 0), scale=(10, 1, 10)),
]

# Gravity and movement variables
gravity = -39.2  # Gravity acceleration
velocity = 0
is_grounded = False

camera.position = Vec3(-20, 10, -20)  # Initial camera position
camera.rotation = Vec3(0, 45, 0) #Initial camera rotation
camera.look_at(player.position) # Initial look at
return_location = player.position + Vec3(-20, 10, -20)
return_rotation = Vec3(0, 45, 0)
return_speed = 5
camera_loc = return_location




def update():
    global velocity, is_grounded, return_speed, return_location, return_rotation, camera_loc

    # Horizontal movement
    move_x = (held_keys['d'] - held_keys['a']) * time.dt * 5
    move_z = (held_keys['w'] - held_keys['s']) * time.dt * 5

    # Check for collisions before moving
    player.x += move_x
    player.z += move_z
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
            if player.y > wall_top_y + (player.scale_y/2.5):  # Ensure the player is above the wall
                player.y = wall_top_y + player.scale_y / 2  # Place player on top of the wall
                velocity = 0
                is_grounded = True
            else:
                # Undo movement if side collision occurs
                player.x -= move_x
                player.z -= move_z
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