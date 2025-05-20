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
    def __init__(self, opacity):
        super().__init__(
                model='Quad',
                scale=(2, 2),  # Adjust scale to fit the camera view
                color=color.rgba(255, 0, 0, opacity),  # Red tint
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
player = Entity(model='cube', color=color.orange, scale=(1, 1, 1), collider='box', position=(0, 30, 0))

        
safeGround = Entity(model='MAP.obj', collider='mesh')
safeGround.position = (45, -0.5, 0)
safeGround.show_colliders = True
safeGround.scale = (2, 1, 1)
safeGround.rotation = (0, 270, 0)



# Gravity and movement variables
gravity = -39.2  # Gravity acceleration
velocity = 39.2  # Initial vertical velocity
is_grounded = False
move_x = 0.1

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
            tint = Tint(opacity=0.2)
            camera.shake(duration=0.5)
            invoke(tint.disable, delay=0.5)  # Disable the tint after the shake duration
        else:
            currentztelpos += 1
        # position shifts one lane further away from the camera
        # if at the furthest possible lane, instead stay in the same place
    if key == 'w':
        if currentztelpos == 0:
            # Create a semi-transparent red tint
            tint = Tint(opacity=0.2)
            camera.shake(duration=0.5)
            invoke(tint.disable, delay=0.5)  # Disable the tint after the shake duration
        else:
            currentztelpos -= 1
        # position shifts one lane closer to camera
        # if at the closest possible lane, instead stay in the same place
    player.z = zTelPos[currentztelpos][2]
    
    
    

def update():
    global velocity, is_grounded, return_speed, return_rotation, camera_loc, movementkeyz, camfollowspd, move_x
    global currentztelpos
    return_location = player.position + Vec3(-20, 20, -20)

    # Check for collisions before moving
    player.x += move_x

    # Jumping
    if is_grounded and held_keys['space']:
        velocity = 15  # Jump velocity

    # Apply gravity
    velocity += gravity * time.dt
    player.y += velocity * time.dt

    is_grounded = False

    # --- Improved boxcast for highest ground point ---
    # Cast a short box just below the player
    boxcast_distance = 0.3  # Only check just below the player
    boxcast_origin = player.position + Vec3(0, -0.2, 0)  # Slightly below feet
    hit_info = boxcast(
        origin=boxcast_origin,
        direction=Vec3(0, -1, 0),
        distance=boxcast_distance,
        thickness=(player.scale_x, player.scale_z),
        ignore=(player,),
        debug=False # Hide the debugging hitbox
    )

    if hit_info.hit:
        is_grounded = True
        # Always set to the highest point found
        player.y = hit_info.world_point.y + player.scale_y / 2 + 0.01  # 0.01 to avoid clipping
        velocity = 0
        
    # --- Boxcast for wall collision (instakill) ---
    # Add a secondary box collider at the top half of the player model (to avoid accidental floor collisions)
    # Use to detect anything in front of the player in an incredibly short range. 
    # This could be implemented by forming a boxcast at the player's xyz coordinates but limiting the scale to 
    # x/2, y/2, z (where each coordinate value is derived from the playermodel)
    # The boxcast collider volume could extend inside the player and not forwards from it
    # Thus causing the boxcast to only trigger once the player actively intersects with a wall.
    deathboxcast_d = 0.5
    hit_info_death = boxcast(
        origin=player.position + Vec3(0, 0.5, 0),  # Start from the top half of the player
        direction=Vec3(1, 0, 0),  # Cast forward
        distance=deathboxcast_d,
        thickness=(player.scale_x / 2, player.scale_y / 2),
        ignore=(player,),
        debug=False  # Hide the debugging hitbox
    )
    
    if hit_info_death.hit:
        # If the player collides with a wall, reset position to start of level
        player.position = (0, 30, 0)
        currentztelpos = 2        
        # stand-in for a proper death animation - literally just red tint
        tint = Tint(opacity=0.7)
        invoke(tint.disable, delay=0.5)  # Disable the tint after the shake duration
    
    #safeground verification
    if safeGround.collider:
        pass
    else:
        print("SafeGround collider is not set. Please check the collider settings.")
        
        
    # Camera movement logic (mouse controls)
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
