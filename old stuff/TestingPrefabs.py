# start by doing the normal thing
from ursina import *
import math

app = Ursina()



# Create a custom player entity
class Player(Entity):
    def __init__(self, **kwargs):
        super().__init__(
            model='cube',
            color=color.azure,
            scale=(1,1,1),
            position=(0,1,0),
            collider='box',
            **kwargs
        )
        self.speed = 5

    def update(self):
        direction = Vec3(
            held_keys['d'] - held_keys['a'],
            0,
            held_keys['w'] - held_keys['s']
        ).normalized()
        move = direction * time.dt * self.speed

        # Use boxcast to check if the player is grounded
        thickness = (self.scale_x * 0.95, self.scale_z * 0.95)  # slightly smaller than player to avoid edge issues
        hit_info = boxcast(
            origin=self.position + Vec3(0, -self.scale_y / 2, 0),
            direction=Vec3(0, -1, 0),
            distance=0.15,
            thickness=thickness,
            ignore=(self,)
        )

        if hit_info.hit:
            self.x += move.x
            self.z += move.z
        else:
            self.y -= 0.1  # simple gravity

player = Player()

camera = camera
camera.position = (-20, 20, -20)
camera.look_at(player)
camera.parent = player
#custom camera controller
class CameraController(Entity):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.camera_distance = 10
        self.camera_height = 5

    def update(self):
        # Update camera position based on player position
        self.position = Vec3(
            player.x,
            player.y + self.camera_height,
            player.z - self.camera_distance
        )
        self.look_at(player)
camera_controller = CameraController()


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

# Gravity and movement variables
gravity = -39.2  # Gravity acceleration
velocity = 39.2  # Initial vertical velocity
is_grounded = False
move_x = 0.1
def update():
    CameraController.update(camera_controller)



#run
app.run()