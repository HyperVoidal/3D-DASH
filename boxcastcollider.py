from ursina import *
import math
from ursina import Button 
from direct.actor.Actor import Actor
import time

#Loading screen asset caller - used later
game_ready = False
# Cap fps to 60 to avoid frame stuttering on heavy model rendering
# Game objects are currently dependent on frame rate so capping it to 60 will help with consistency across devices and parity while developing on different devices
window.vsync = True
window.fps_limit = 60
application.fps_limit = 60
app = Ursina()
camera_locked = False
rot_locked = False




# --- PRE-APP SETUP AND VARIABLES ---
# Player entity with a collider
player = Entity(model='cube', color=(0.906, 0.501, 0.070, 1), scale=(1, 1, 1), collider='box', position=(0, 30, 0))
#rgba value is set to the blender colour of the player model



#Collision map for the ground entity. 
# Replace with an automated replacement of the model once level select screen is implemented and multiple maps are made        
safeGround = Entity(model='MAP.obj', collider='mesh')
safeGround.position = (52.5, -0.5, 0)
safeGround.show_colliders = True
safeGround.scale = (2, 1, 1.5)
safeGround.rotation = (0, 270, 0)

# Gravity and movement variables
gravity = -39.2  # Gravity acceleration
velocity = 39.2  # Initial vertical velocity
is_grounded = False
move_x = 6 #movespeed

#Camera Positioning
camera.position = Vec3(-20, 20, -20)  # Initial camera position
camera.rotation = Vec3(0, 45, 0) #Initial camera rotation
camera.look_at(player.position) # Initial look at
return_rotation = Vec3(0, 45, 0)
return_speed = 5 #how fast the camera returns to equilibrium position
camera_loc = player.position + Vec3(-20, 20, -20)
currentztelpos = 2


#Starting ground functions for rendering (TO BE PUT INTO A CLASS OR SEPERATE FILE FOR "LEVEL START")
#This component will be maintained at the start of all levels
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







# --- Main Classes ---

class Tint(Entity):
    def __init__(self, opacity):
        super().__init__(
                model='Quad',
                scale=(2, 2),  # Adjust scale to fit the camera view
                color=color.rgba(255, 0, 0, opacity),  # Red tint
                parent=camera.ui,  # Attach to the camera's UI layer
                enabled=True
                
            )
        
class BakedMeshAnimation(Entity):
    def __init__(self, frame_files, frame_time=0.03, **kwargs):
        super().__init__(model=frame_files[0], **kwargs)
        self.frame_files = frame_files
        self.frame_time = frame_time
        self.current_frame = 0
        self.time_accum = 0
        self.playing = False
        self.finished_callback = None
        self.disable()  # Hide by default

    def play(self, position, finished_callback=None):
        self.position = position
        self.current_frame = 0
        self.time_accum = 0
        self.model = self.frame_files[0]
        self.playing = True
        self.enable()
        self.finished_callback = finished_callback

    def update(self):
        if not self.playing:
            return
        self.time_accum += time.dt
        if self.time_accum >= self.frame_time:
            self.time_accum = 0
            self.current_frame += 1
            if self.current_frame < len(self.frame_files):
                self.model = self.frame_files[self.current_frame]
            else:
                self.playing = False
                self.disable()
                if self.finished_callback:
                    self.finished_callback()

player_immobilized = False  # Add this global flag

def respawn_player():
    global velocity, currentztelpos, camera_locked, rot_locked, player_immobilized
    player.position = Vec3(0, 5, 0)
    player.movement = Vec3(0, 10, 0) 
    velocity = 0
    player.z = zTelPos[2][2]
    currentztelpos = 2
    player.enable()
    camera_locked = False  # Unlock camera on respawn
    rot_locked = False
    player_immobilized = False  # Allow movement after respawn animation

def checkrotation(from_pos, to_pos):
    temp = Entity(position=from_pos)
    temp.look_at(to_pos)
    rot = temp.rotation
    destroy(temp)
    return rot

def respawn_anim():
    global camera_locked, rot_locked, player_immobilized
    camera_locked = True
    rot_locked = True
    player_immobilized = True  # Immobilize player during respawn animation
    deathpos = camera.position
    camerarot = camera.rotation
    playercampos = player.position + Vec3(-20, 20, -20)
    return_rotation = checkrotation(playercampos, player.position)
    
    camera_loc = lerp(deathpos, playercampos, time.dt * return_speed)
    camera.position = camera_loc
    camerarot = camera.rotation
    camera_rot = lerp(camerarot, return_rotation, time.dt * return_speed)
    camera.rotation = camera_rot

    # Check if camera is close enough to target position and rotation
    if (distance(camera.position, playercampos) < 0.1 and 
        distance(camera.rotation, return_rotation) < 0.5):
        camera_locked = False
        rot_locked = False
        player_immobilized = False  # Re-enable player movement

def input(key):
    global currentztelpos, rot_locked, camera_locked, player_immobilized
    
    #reset - instakills and respawns player
    if key == 'r':
        if not death_anim.playing:
            player.disable()
            death_anim.play(player.position, finished_callback=respawn_player)
            camera_locked = True  # Lock camera when player dies
            rot_locked = True
        else:
            pass  # Ignore input if death animation is playing
        
    #exit game
    if key == 'escape':
        quit()
        
    #toggle fullscreen mode
    if key == 'f':
        # Toggle fullscreen mode
        window.fullscreen = not window.fullscreen
        
    #main controls: d for left and a for right
    if key == 'd':
        if currentztelpos == 4:
            # Create a semi-transparent red tint
            tint = Tint(opacity=0.2)
            camera.shake(duration=0.5)
            invoke(tint.disable, delay=0.5)  # Disable the tint after the shake duration
        else:
            currentztelpos += 1
        # position shifts one lane further away from the camera
        # if at the furthest possible lane, instead stay in the same place
    if key == 'a':
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

# --- Prerender Animations before game start ---

# Prepare the list of animation frames
death_anim_frames = [f'cubedeathani/miniexplode.f{str(i).zfill(4)}.glb' for i in range(1, 45)]
loading_text = Text("Loading...", origin=(0,0), scale=2, background=True)
loading_text.enabled = True

def finish_loading():
    global game_ready
    loading_text.enabled = False
    game_ready = True

# --- PRELOAD all animation frames to avoid first-run lag ---
for frame in death_anim_frames:
    Entity(model=frame, enabled=False)  # Load and cache the model

death_anim = BakedMeshAnimation(death_anim_frames, scale=(1,1,1), texture=None, color=(0.906, 0.501, 0.070, 1))
death_anim.disable()

# After all loading is done, schedule finish_loading
invoke(finish_loading, delay=0.1)



fixed_dt = 1/60  # 60 updates per second
accumulator = 0

# --- Main Update Loop ---
def update():
    global accumulator
    if not game_ready:
        return

    # Forcefully set the maximum number of game updates per second to 60. 
    # Update function runs at max available fps but the game logic is capped to 60 updates per second. 
    # Anything reliant on framerates works in the game logic step function. 
    # If necessary, something requiring a higher framerate can be run in the update function
    accumulator += time.dt
    while accumulator >= fixed_dt:
        game_logic_step(fixed_dt)
        accumulator -= fixed_dt

def game_logic_step(dt):
    global velocity, is_grounded, currentztelpos, camera_loc, camera_locked, rot_locked
    # Use dt instead of time.dt everywhere in your logic

    if not player_immobilized:
        player.x += move_x * dt

    #camera return location
    return_location = player.position + Vec3(-20, 20, -20)

    # Jumping
    if is_grounded and held_keys['space'] and not player_immobilized:
        velocity = 15  # Jump velocity

    # Apply gravity
    velocity += gravity * dt
    player.y += velocity * dt

    is_grounded = False

    # --- Improved boxcast for highest ground point ---
    # Cast a short box just below the player
    boxcast_distance = 0.3  # Only check just below the player
    boxcast_origin = player.position + Vec3(0, -0.3, 0)  # Slightly below feet
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
    
    if hit_info_death.hit and not death_anim.playing:
        player.disable()
        death_anim.play(player.position, finished_callback=respawn_player)
        camera_locked = True  # Lock camera when player dies
        rot_locked = True

    #safeground verification
    if safeGround.collider:
        pass
    else:
        print("SafeGround collider is not set. Please check the collider settings.")
        
    # Camera movement logic (mouse controls)
    if not camera_locked:
        if mouse.left:
            camera_loc.x -= mouse.velocity[0] * return_speed * 1500 * time.dt
            camera_loc.y += mouse.velocity[1] * return_speed * 1500 * time.dt
            camera.position = camera_loc
        else:
            camera_loc = lerp(camera_loc, return_location, time.dt * return_speed)
            camera.position = camera_loc

            camerarot = camera.rotation
            camera_rot = lerp(camerarot, return_rotation, time.dt * return_speed)
            camera.rotation = camera_rot
    if not rot_locked:
        camera.look_at(player.position)

    
app.run()
