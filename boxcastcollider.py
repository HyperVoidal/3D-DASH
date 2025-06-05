from ursina import *
from math import radians, cos, sin
from ursina import Button 
from direct.actor.Actor import Actor
import time
import threading 
import shutil
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
import json


#cache clearing function - clean up the compressed models folder on startup
def cache_clear(folder):
    try:
        shutil.rmtree(folder)
    except:
        print(f"WARNING\nCache clearing error detected - please restart the game!")

cache_clear(folder="models_compressed")

#Loading screen asset caller - used later
game_ready = False
window.vsync = True
window.icon = "window_icon.ico"
window.title = "3D DASH"
app = Ursina()


#Window Variables
#window.borderless = True
#monitorlist = window.monitors
#window.size = (1280, 720)


# --- PRE-APP SETUP AND VARIABLES ---

# Model Loading
# Player entity with a collider
#rgba value is set to the blender colour of the player model
player = Entity(model='cube', color=(0.906, 0.501, 0.070, 1), scale=(1, 1, 1), collider='box', position=(0, 30, 0))
# Prepare the list of animation frames
death_anim_frames = [f'cubedeathani/miniexplode.f{str(i).zfill(4)}.glb' for i in range(1, 45)]

#Import Json file
with open ("level_data.json", "r") as f:
    data = json.load(f)

#Map Data
MAPLIST = []
for key in data:
    MAPLIST.append(str(key))
MAP = None
GameMap = None
largestx = 0
minx = 0
maxx = 0
current_mapcount = 1

#ERROR IN LEVEL 2 - Panda3D detects objects too close together. Take a look at level 2 and see any invalid collision
def renderMap(map_name):
    global GameMap, largestx, minx, maxx
    x_scale = 2
    GameMap = Entity(model=f'{map_name}.obj', collider='mesh')
    GameMap.scale = (x_scale, 1, 1.5)
    GameMap.rotation = (0, 270, 0)
    # Temporarily position at origin to calculate min/max
    GameMap.position = (0, -0.5, 0)
    minx, maxx = calcpoints(GameMap)
    # Desired starting X position in world space
    desired_start_x = 32.5
    # Shift so minx aligns with desired_start_x
    shift = desired_start_x - minx
    GameMap.position = (shift, -0.5, 0)
    # Recalculate minx, maxx after shifting
    minx, maxx = calcpoints(GameMap)
    return GameMap

def calcpoints(map):        
    vertexmap = map.combine().vertices
    rotated_vertices = []
    angle = radians(map.rotation_y if hasattr(map, 'rotation_y') else map.rotation[1])
    cos_a = cos(angle)
    sin_a = sin(angle)
    for v in vertexmap:
        # Apply scale
        scaled = Vec3(v[0] * map.scale_x, v[1] * map.scale_y, v[2] * map.scale_z)
        # Apply Y rotation manually
        x = scaled.x * cos_a - scaled.z * sin_a
        z = scaled.x * sin_a + scaled.z * cos_a
        rotated = Vec3(x, scaled.y, z)
        # Apply position
        world_pos = map.position + rotated
        rotated_vertices.append(world_pos.x)
    minx = min(rotated_vertices)
    maxx = max(rotated_vertices)
    return minx, maxx

def get_hsv_color(fraction):
    """
    Map a value between 0 and 1 to an RGB color from the hsv colormap.
    :param fraction: float between 0 and 1
    :return: (r, g, b) tuple, each in range [0, 1]
    """
    cmap = plt.get_cmap('hsv')
    norm = mpl.colors.Normalize(vmin=0, vmax=1)
    rgba = cmap(norm(fraction))
    rgb = [round(float(x), 3) for x in rgba[:3]]  # Convert to float and round
    return rgb # Return only RGB, ignore alpha
    

# Gravity and movement variables
gravity = -39.2  # Gravity acceleration
velocity = 39.2  # Initial vertical velocity
is_grounded = False
move_x = 6 #movespeed
playlock = False
paused = False

#Camera Positioning
camera.position = Vec3(-20, 20, -20)  # Initial camera position
camera.rotation = Vec3(0, 45, 0) #Initial camera rotation
camera.look_at(player.position) # Initial look at
return_rotation = Vec3(0, 45, 0)
return_speed = 5 #how fast the camera returns to equilibrium position
camera_loc = player.position + Vec3(-20, 20, -20)
camera_locked = False
rot_locked = False
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
    Ground(position=(zTelPos[0]), scale=(65, 1, 2), color = col1),
    Ground(position=(zTelPos[1]), scale=(65, 1, 2), color = col2),
    Ground(position=(zTelPos[2]), scale=(65, 1, 2), color = col1),
    Ground(position=(zTelPos[3]), scale=(65, 1, 2), color = col2),
    Ground(position=(zTelPos[4]), scale=(65, 1, 2), color = col1)
]



# --- Main Classes ---
# Loading Screen
class LoadingScreen(Entity):
    def __init__(self):
        super().__init__(
            model='Quad',
            scale=(2, 2),
            color=color.rgba(0, 0, 0, 1),
            parent=camera.ui,
            enabled=True
        )
        # Create background first, with lower z
        self.background = Entity(
            model='Quad',
            scale=(10, 10),
            color=color.black,
            position=(0, 0, -2),  # Lower z to be behind text
            parent=self,
            enabled=True
        )
        # Then create text
        self.text = Text(
        "Loading...",
        origin=(0, 0),
        color=color.white,
        scale=2,
        background=False,
        parent=self
        )

    def disable(self):
        self.enabled = False
        self.text.enabled = False
        self.background.enabled = False
        
# Run main menu before ALMOST everything else
# Main menu should freeze player and then render an interactive menu with mouse clickable options for 
# Level Select, options, and player customisation
class MainMenu(Entity):
    def __init__(self):
        super().__init__(
            model='Quad',
            scale=(2, 2),
            color=color.rgba(0, 0, 255, 1),  # rgb + opacity
            parent=camera.ui,
            enabled=False
        )
        self.text = None
        self.start_button = None
        self.options_button = None
        self.customise_button = None
        self.quit_button = None
        self.options_back_button = None
        self.customise_back_button = None

    def rendermenu(self):
        global playlock
        playlock = True
        self.enabled = True
        self.text = Text("Main Menu", origin=(0, -4), scale=2, background=True, parent=self)
        self.start_button = Button(text="Level Select", scale=(0.5, 0.1), position=(0, 0.1), parent=self, on_click=self.open_level_select)
        self.options_button = Button(text="Options", scale=(0.5, 0.1), position=(0, 0), parent=self, on_click=self.open_options)
        self.customise_button = Button(text="Wardrobe", scale=(0.5, 0.1), position=(0, -0.1), parent=self, on_click=self.open_customisation)
        self.quit_button = Button(text="Quit", scale=(0.5, 0.1), position=(0, -0.2), parent=self, on_click=self.quit_game)

    def enable_menu_components(self, enabled=True):
        if self.text: self.text.enabled = enabled
        if self.start_button: self.start_button.enabled = enabled
        if self.options_button: self.options_button.enabled = enabled
        if self.customise_button: self.customise_button.enabled = enabled
        if self.quit_button: self.quit_button.enabled = enabled

    def open_level_select(self):
        self.enable_menu_components(False)
        if not hasattr(self, 'level_select_screen'):
            self.level_select_screen = LevelSelect(self)
        self.level_select_screen.show()

    def open_customisation(self):
        self.enable_menu_components(False)
        if not self.customise_back_button:
            self.customise_text = Text("Customisation menu opened (not implemented yet).", origin=(0, 0), scale=1.5, background=True, parent=self)
            self.customise_back_button = Button(text="Back", scale=(0.3, 0.1), position=(0, -0.2), parent=self, on_click=self.close_customisation)
        else:
            self.customise_text.enabled = True
            self.customise_back_button.enabled = True

    def close_customisation(self):
        self.customise_text.enabled = False
        self.customise_back_button.enabled = False
        self.enable_menu_components(True)

    def open_options(self):
        self.enable_menu_components(False)
        if not self.options_back_button:
            self.options_text = Text("Options menu opened (not implemented yet).", origin=(0, 0), scale=1.5, background=True, parent=self)
            self.options_back_button = Button(text="Back", scale=(0.3, 0.1), position=(0, -0.2), parent=self, on_click=self.close_options)
        else:
            self.options_text.enabled = True
            self.options_back_button.enabled = True

    def close_options(self):
        self.options_text.enabled = False
        self.options_back_button.enabled = False
        self.enable_menu_components(True)

    def quit_game(self):
        quit()

# Comprises the level select screen, which allows players to choose a level from a list of maps.

class LevelSelect(Entity):
    def __init__(self, main_menu):
        self.main_menu = main_menu
        self.MAPLIST = MAPLIST
        self.MAP = self.MAPLIST[0]
        self.mapcount = 1  
        super().__init__(
            model='Quad',
            scale=(2, 2),
            color=color.rgb(*get_hsv_color(int(self.mapcount) / len(self.MAPLIST))),
            parent=camera.ui,
            enabled=False
        )
        
        
        self.left_button = Button(text="", color=color.rgba(128, 128, 128, 0.75), scale=(0.1, 0.1), position=(-0.3, 0), parent=self, on_click=self.previous_level)
        self.left_arrow = Entity(
            model='arrowNOBG.obj',
            scale=(0.03, 0.03, 0.03),
            parent=self.left_button,
            position=(0, 0, -0.01),
            rotation=(90, 0, 0),
            color=color.white,
            texture=None
        )

        self.right_button = Button(text="", color=color.rgba(128, 128, 128, 0.75), scale=(0.1, 0.1), position=(0.3, 0), parent=self, on_click=self.next_level)
        self.right_arrow = Entity(
            model='arrowNOBG.obj',
            scale=(0.03, 0.03, 0.03),  
            parent=self.right_button,
            position=(0, 0, -0.01),    
            rotation=(90, 180, 0),
            color=color.white,
            texture=None
        )
        self.levelperc = Entity(
            model = 'ProgressBar.obj',
            scale=(0.09, 0.03, 0.03),
            position=(0, -0.075, -0.1),
            rotation=(90, 0, 0),
            parent=camera.ui,
            color=color.white,
            texture=None,
            enabled=True
        )
        
        self.levelcomp = Entity(
            model = 'cube',
            position = (0, 0.45, 0),
            rotation = (90, 0, 0),
            color=color.orange,
            parent=self.levelperc,
            enabled=True
        )
        
        self.levelpercentage = Text(text="0.0%", parent=camera.ui, position=(0, -0.07, -0.1), color=color.black, enabled=True)
        
        # Level data loading
        with open ("level_data.json", "r") as f:
            data = json.load(f)
        
        levelpercent = data[f"Level{self.mapcount}"]
        x_scaling = 9.95 * (float(levelpercent)/100)
        self.levelcomp.scale = (x_scaling, 1.2, 1.2)
        self.levelcomp.x = -4.95 + x_scaling / 2
        self.levelpercentage.text = (f"{str(levelpercent)} %")
        
        self.level_text = Text(f"Level {self.mapcount}", position=(0, 0.04, 0), origin=(0, 0.5), scale=2, background=True, parent=self, color=color.black)
        self.start_level_button = Button(text="Start Level", scale=(0.5, 0.1), position=(0, -0.2), parent=self, on_click=self.start_game)
        self.back_button = Button(text="Back", scale=(0.1, 0.1), position=(-0.35, 0.2), parent=self, on_click=self.back_to_menu)
        self.score = None # Placeholder for distance value, work with json file when implemented
        self.PlayerMap = None
        self.colorscale = None
        self.hide()
    
    def updatelevelperc(self):
        # Level data loading
        with open ("level_data.json", "r") as f:
            data = json.load(f)
        
        levelpercent = data[f"Level{self.mapcount}"]
        x_scaling = 9.95 * (float(levelpercent)/100)
        self.levelcomp.scale = (x_scaling, 1.2, 1.2)
        self.levelcomp.x = -4.95 + x_scaling / 2
        self.levelpercentage.text = (f"{str(levelpercent)} %")

    def show(self):
        self.enabled = True
        self.left_button.enabled = True
        self.right_button.enabled = True
        self.level_text.enabled = True
        self.start_level_button.enabled = True
        self.back_button.enabled = True
        self.levelperc.enabled = True
        self.levelcomp.enabled = True
        self.levelpercentage.enabled = True

    def hide(self):
        self.enabled = False
        self.left_button.enabled = False
        self.right_button.enabled = False
        self.level_text.enabled = False
        self.start_level_button.enabled = False
        self.back_button.enabled = False
        self.levelperc.enabled = False
        self.levelcomp.enabled = False
        self.levelpercentage.enabled = False

    def previous_level(self):
        if self.mapcount == 1:
            self.mapcount = len(self.MAPLIST)
        else:
            self.mapcount -= 1
        #update level text
        self.level_text.text = f"Level {self.mapcount}"
        
        self.color=color.rgb(*get_hsv_color(int(self.mapcount) / len(self.MAPLIST)))
        
        self.updatelevelperc()
        
    def next_level(self):
        if self.mapcount == len(self.MAPLIST):
            self.mapcount = 1
        else:
            self.mapcount += 1
        #update level text  
        self.level_text.text = f"Level {self.mapcount}"
        self.color=color.rgb(*get_hsv_color(int(self.mapcount) / len(self.MAPLIST)))
        
        self.updatelevelperc()

    def start_game(self):
        global game_ready, playlock, GameMap, minx, maxx, levelprog, current_mapcount
        self.MAP = self.MAPLIST[(int(self.mapcount) -1)]
        current_mapcount = self.mapcount
        # Render the selected map before starting the game
        if GameMap:
            GameMap.disable()
            destroy(GameMap)
            GameMap = None
        GameMap = renderMap(self.MAP)
        # Update level progress bar bounds
        levelprog.gamemap = GameMap
        levelprog.minX = minx
        levelprog.maxX = maxx
        self.hide()
        self.main_menu.enable_menu_components(False)
        self.main_menu.enabled = False
        game_ready = True
        playlock = False

    def back_to_menu(self):
        self.hide()
        self.main_menu.enable_menu_components(True)

# Multipurpose class for level progress tracking
# Detects the total size of level, compares player progress through position, and updates the level progress file
# Also provides a UI for after-death to show furthest progress
# Also Also renders a progressbar for level movement and provides a percentage value
class LevelProgress(Entity):
    def __init__(self):
        super().__init__()
        global GameMap, minx, maxx
        self.gamemap = GameMap
        #default state for level start
        self.percentagecompletion = 0 
        self.maxX = maxx
        self.minX = minx
        #create percentage bar entity ONCE
        self.BarFrame = Entity(
            model = 'ProgressBar.obj',
            scale=(0.09, 0.03, 0.03),
            position=(0, 0.45, 0),
            rotation=(90, 0, 0),
            parent=camera.ui,
            color=color.white,
            texture=None,
            enabled=True
        )
        self.loadingbar = Entity(
            model = 'cube',
            position = (0, 0.45, 0),
            rotation = (90, 0, 0),
            color=color.orange,
            parent=self.BarFrame,
            enabled=True
        )
        self.textpercent = Text(
            text="0.0%",
            parent=camera.ui,
            position=(0.45, 0.46, 0),
            color=color.black,
            enabled=True
        )
    
    def percentagebar(self):
        # Only X scale changes, Y and Z should stay visible
        x_scaling = 9.95 * (self.percentagecompletion/100)
        self.loadingbar.scale = (x_scaling, 1.2, 1.2)
        self.loadingbar.x = -4.95 + x_scaling / 2

    def findpercentage(self):
        if not death_anim.playing:
            #pull tuple returns from calcpoints using GameMap as the interpreted vertices
            # Calculate progress as a value between 0 and 1
            progress = (player.x - self.minX) / (self.maxX - self.minX) if self.maxX != self.minX else 0
            progress = max(0, min(1, progress))  # Clamp to [0, 1]
            self.percentagecompletion = round(progress * 100, 1)
            self.textpercent.text = f"{self.percentagecompletion}%"
            self.percentagebar()
            
            

def reset_game_state():
    global velocity, currentztelpos, camera_locked, rot_locked, playlock, game_ready, accumulator, GameMap
    # Reset player state
    player.position = Vec3(0, 30, 0)
    player.z = zTelPos[2][2]
    velocity = 39.2
    currentztelpos = 2
    player.enable()
    # Reset camera
    camera.position = Vec3(-20, 20, -20)
    camera.rotation = Vec3(0, 45, 0)
    camera.look_at(player.position)
    # Reset flags
    camera_locked = False
    rot_locked = False
    playlock = False
    game_ready = False
    accumulator = 0
    LevelSelect.mapcount = 0
    LevelSelect.MAP = None
    if GameMap:
        GameMap.disable()
        destroy(GameMap)
        GameMap = None
    # Show main menu
    main_menu.rendermenu()
    

class PauseMenu(Entity):
    def __init__(self):
        super().__init__(
            model='Quad',
            scale=(0.5, 0.8),
            color=color.rgba(128, 128, 128, 0.5),
            parent=camera.ui,
            enabled=True
        )
        self.resume_button = Button(
            text="Resume",
            scale=(0.4, 0.1),
            position=(0, 0.25),
            parent=self,
            on_click=self.resume_game
        )
        self.mainmenubutton = Button(
            text="Main Menu",
            scale=(0.4, 0.1),
            position=(0, 0),
            parent=self,
            on_click=lambda: (self.disable(), reset_game_state())
        )
        self.exittodesktop_button = Button(
            text="Exit to Desktop",
            scale=(0.4, 0.1),
            position=(0, -0.25),
            parent=self,
            on_click=quit
        )

    def rendermenu(self):
        global playlock, paused
        playlock = True
        self.enabled = True
        self.resume_button.enabled = True
        paused = True

    def disable(self):
        global playlock, paused
        self.enabled = False
        self.resume_button.enabled = False
        playlock = False
        paused = False

    def resume_game(self):
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
        
class BakedMeshAnimation(Entity):
    playing = False  # <-- Add this line to ensure the attribute always exists

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
        if not hasattr(self, 'playing') or not self.playing:
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

def respawn_player():
    global velocity, currentztelpos, camera_locked, rot_locked, playlock, paused
    player.position = Vec3(0, 5, 0)
    player.movement = Vec3(0, 10, 0) 
    velocity = 0
    player.z = zTelPos[2][2]
    currentztelpos = 2
    # Allow movement after respawn animation - circumvents pausing error during death animation
    if not paused:
        player.enable()
        camera_locked = False
        rot_locked = False
        playlock = False  

def checkrotation(from_pos, to_pos):
    temp = Entity(position=from_pos)
    temp.look_at(to_pos)
    rot = temp.rotation
    destroy(temp)
    return rot

def respawn_anim():
    global camera_locked, rot_locked, playlock
    camera_locked = True
    rot_locked = True
    playlock = True  # Immobilize player during respawn animation
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
        playlock = False  # Re-enable player movement

def input(key):
    global currentztelpos, rot_locked, camera_locked, playlock
    # ---- Independent Controls ----
    #exit game
    if key == 'escape':
        quit()
        
    #toggle fullscreen mode
    if key == 'f':
        # Toggle fullscreen mode
        window.fullscreen = not window.fullscreen
    
    # ---- Must be in game ----
    #pause menu
    if game_ready:
        if key == 'tab':
            if not hasattr(app, 'pause_menu'):
                app.pause_menu = PauseMenu()
            if app.pause_menu.enabled:
                app.pause_menu.disable()
            else:
                app.pause_menu.rendermenu()

        
    #main controls: d for left and a for right
    if game_ready and not playlock:
        
        #reset - instakills and respawns player
        if key == 'r':
            if not death_anim.playing:
                player.disable()
                death_anim.play(player.position, finished_callback=respawn_player)
                camera_locked = True  # Lock camera when player dies
                rot_locked = True
            else:
                pass  # Ignore input if death animation is playing
            
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
    
# set a function to prerender all variables
# apply it to a thread and call the loading screen while it's running
#upon finish, invoke finish_loading to hide the loading screen and set game_ready to True
def prerendering():
    global death_anim
    # --- PRELOAD all animation frames to avoid first-run lag ---
    for frame in death_anim_frames:
        e = Entity(model=frame, enabled=True)
        invoke(e.disable, delay=0.1)  # Let it render for one frame, then disable

    death_anim = BakedMeshAnimation(death_anim_frames, scale=(1,1,1), texture=None, color=(0.906, 0.501, 0.070, 1))
    death_anim.disable()

    # After all loading is done, schedule finish_loading
    invoke(finish_loading, delay=0.1)

loading_screen = LoadingScreen()  # Create and keep a reference
levelprog = LevelProgress()

def finish_loading():
    global main_menu
    loading_screen.disable()  # Disable the correct instance
    #load main menu
    main_menu = MainMenu()
    main_menu.rendermenu()

renderthread = threading.Thread(target=prerendering, daemon=True)
renderthread.start()


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
    
    if not playlock:
        # --- All movement and physics logic goes here ---
        player.x += move_x * dt

        # Jumping
        if is_grounded and held_keys['space']:
            velocity = 15  # Jump velocity

        # Apply gravity
        velocity += gravity * dt
        player.y += velocity * dt

        is_grounded = False

        # --- Improved boxcast for highest ground point; this is the under-player cast---
        boxcast_distance = 0.3
        boxcast_origin = player.position + Vec3(0, -0.3, 0)
        hit_info = boxcast(
            origin=boxcast_origin,
            direction=Vec3(0, -1, 0),
            distance=boxcast_distance,
            thickness=(player.scale_x, player.scale_z),
            ignore=(player,),
            debug=False
        )

        if hit_info.hit:
            is_grounded = True
            player.y = hit_info.world_point.y + player.scale_y / 2 + 0.01
            velocity = 0
            
        # --- Secondary box cast for collision correction - orients player during clipping to avoid instakill ---
        castdist = 0.3
        castorig = player.position + Vec3(0, 0, 0)
        hit_info = boxcast(
            origin=castorig,
            direction=Vec3(0, -1, 0),
            distance=castdist,
            thickness=(player.scale_x, player.scale_z),
            ignore=(player,),
            debug=True
        )

        if hit_info.hit:
            is_grounded = True
            player.y += 0.3
            velocity = 0
    else:
        # When immobilized, prevent all movement and physics
        velocity = 0
        is_grounded = False

    # --- Boxcast for wall collision (instakill) ---
    # (This can remain outside, so death still triggers when immobilized)
    deathboxcast_d = 0.5
    hit_info_death = boxcast(
        origin=player.position + Vec3(0, 0.5, 0),
        direction=Vec3(1, 0, 0),
        distance=deathboxcast_d,
        thickness=(player.scale_x / 2, player.scale_y / 2),
        ignore=(player,),
        debug=False
    )

    if hit_info_death.hit and not death_anim.playing:
        #Save highscore
        with open ('level_data.json', 'r') as file:
            data = json.load(file)
        if float(data[f"Level{current_mapcount}"]) < float(levelprog.percentagecompletion):
            data[f"Level{current_mapcount}"] = (f"{levelprog.percentagecompletion}")
            with open ('level_data.json', 'w') as file:
                json.dump(data, file)
        else:
            pass
        
        #Trigger death animation
        player.disable()
        death_anim.play(player.position, finished_callback=respawn_player)
        camera_locked = True
        rot_locked = True
        

    #Map Integrity Verification
    if GameMap.collider:
        pass
    else:
        print("Game MAP collider is not set. Please check the collider settings.")
        
    # Camera movement logic (mouse controls)
    #camera return location
    return_location = player.position + Vec3(-20, 20, -20)
    
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
    
    levelprog.findpercentage()

    
app.run()
