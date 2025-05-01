from ursina import *
import math

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
# Stack ground on top of wall objects to stop internal collision
ground = [
    Ground(position=(0, 0, 0), scale=(10, 1, 10)),
    Ground(position=(5, 2.5, 0), scale=(1, 1, 1)),
    Ground(position=(-5, 2.5, 0), scale=(1, 1, 1)),
    Ground(position=(0, 2.5, 5), scale=(1, 1, 1)),
    Ground(position=(0, 2.5, -5), scale=(1, 1, 1)),
]

# Gravity and movement variables
gravity = -39.2  # Gravity acceleration
velocity = 0
is_grounded = False

camera.position = Vec3(-20, 20, -20)  # Initial camera position
camera.rotation = Vec3(0, 0, 0) #Initial camera rotation
camera.look_at(player.position) # Initial look at


def update():
    global velocity, is_grounded, camera_yaw, camera_pitch, current_camera_pos, camera_distance, smoothing

    # Horizontal movement
    move_x = (held_keys['d'] - held_keys['a']) * time.dt * 5
    move_z = (held_keys['w'] - held_keys['s']) * time.dt * 5

    # Check for collisions before moving
    player.x += move_x
    player.z += move_z

    for wall in walls:
        if player.intersects(wall).hit:
            # Undo movement if collision occurs
            player.x -= move_x
            player.z -= move_z
            break

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
    
    camera.look_at(player.position)  # Keep camera looking at player
    camera.position = Vec3(player.x - 20, player.y + 20, player.z - 20)  # Update camera position based on player

    


app.run()