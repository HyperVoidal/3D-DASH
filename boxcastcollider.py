from ursina import *
from ursina import Button 
from direct.actor.Actor import Actor
from ursina import Slider
from ursina import destroy
from ursina.shaders import lit_with_shadows_shader, basic_lighting_shader
from ursina import DirectionalLight
from math import radians, cos, sin
import time
import threading 
import shutil
import matplotlib.pyplot as plt
import matplotlib as mpl
import json

#cache clearing function - clean up the compressed models folder on startup
def cache_clear(folder):
    try:
        shutil.rmtree(folder)
    except:
        print(f"WARNING\nCache clearing error detected - please restart the game!")
cache_clear(folder="models_compressed")

def updategraphics(sizing):
    value = sizing.split("x")
    numval = (int(value[0]), int(value[1]))
    window.size = numval

#Bug with the window sizing - switching to fullscreen and then back out from a value that isnt 1920x1080
#will leave the value of the dropdown select at the non 1920x1080 variable. This has no effect on experience besides
#being an odd visual bug that needs fixing.
def updatewindow(Value):
    retainsizing = window.size
    if Value == "Fullscreen":
        window.fullscreen = True
    elif Value == "Borderless Windowed":
        window.borderless = True
        window.fullscreen = False
        window.size = retainsizing
    elif Value == "Windowed":
        window.borderless = False
        window.fullscreen = False
        window.size = retainsizing
    else:
        pass
    

app = Ursina()
window.show_ursina_splash = True
window.title = "3D DASH"
#remember to set a custom icon when exporting this program to an exe, you can't change taskbar icon in normal ursina
window.icon = "window_icon.ico"


# --- PRE-APP SETUP AND VARIABLES ---

# Model Loading
# Player entity with a collider
#rgba value is set to the blender colour of the player model
sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
sun.shadows = True
app.fog_color=color.light_gray
app.fog_density = 0.5

player = Entity(model='cube', 
                texture=None, 
                color=(0.906, 0.501, 0.070, 1), 
                scale=(1, 1, 1), 
                collider='box', 
                position=(0, 30, 0), 
                shader=lit_with_shadows_shader)

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
main_menu = None
GameMap = None
largestx = 0
minx = 0
maxx = 0
current_mapcount = 1
LARGESTX = 0

#Main systems for fps and update control
fixed_dt = 1/60  # 60 updates per second
accumulator = 0

#Options menu systems
with open ("playerdata.json", "r") as f:
    data = json.load(f)
Volume = data["Volume"]
Sensitive = data["Sensitivity"]
returntogame = False
game_ready = False
Text.default_font = "2TECH2.ttf"

#ERROR IN LEVEL 2 - Panda3D detects objects too close together. Take a look at level 2 and see any invalid collision
def renderMap(map_name):
    global GameMap, largestx, minx, maxx
    x_scale = 2
    GameMap = Entity(model=f'{map_name}.obj', collider='mesh')
    GameMap.scale = (x_scale, 1, 1.5)
    GameMap.rotation = (0, 270, 0)
    #Create shaders for map
    GameMap.shader = lit_with_shadows_shader
    if hasattr(GameMap.model, 'generate_normals'):
        GameMap.model.generate_normals()
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
    LARGESTX = maxx
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

def savehigh(mapcount, perccomp):
    with open ('level_data.json', 'r') as file:
        data = json.load(file)
    if float(data[f"Level{mapcount}"]) < float(perccomp):
        data[f"Level{mapcount}"] = (f"{perccomp}")
        with open ('level_data.json', 'w') as file:
            json.dump(data, file)
    else:
        pass

def saveplayerdata():
    global Sensitive, Volume
    data = {
        "Sensitivity": Sensitive,
        "Volume": Volume
    }
    with open ("playerdata.json", "w") as file:
        json.dump(data, file)

    
    

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
        super().__init__(model='cube', scale=scale, collider='box', color=color, position=position, shader=lit_with_shadows_shader)

    def destroy(self):
        self.disable()
class Wall(Entity):
    def __init__(self, position, scale, color):
        super().__init__(model='cube', scale=scale, collider='box', color=color, position=position, shader=lit_with_shadows_shader)

    def destroy(self):
        self.disable()
class EndGate(Entity):
    def __init__(self, position, scale, color):
        super().__init__(model='cube', scale=scale, collider='box', color=color, position=position, shader=lit_with_shadows_shader)
        
    def destroy(self):
        self.disable()
        

zTelPos = [
    [0, 0, 4],
    [0, 0, 2],
    [0, 0, 0],
    [0, 0, -2],
    [0, 0, -4]
]
# Create walls
walls = [
    Wall(position=(4.5, 0.5, 0), scale=(1, 2, 1), color=color.black),
    Wall(position=(-3, 2, 0), scale=(1, 5, 10), color=color.red),
]

# Create ground
ground = [
    Ground(position=(zTelPos[0]), scale=(65, 1, 2), color = color.black),
    Ground(position=(zTelPos[1]), scale=(65, 1, 2), color = color.gray),
    Ground(position=(zTelPos[2]), scale=(65, 1, 2), color = color.black),
    Ground(position=(zTelPos[3]), scale=(65, 1, 2), color = color.gray),
    Ground(position=(zTelPos[4]), scale=(65, 1, 2), color = color.black)
]

existing_gate = []
def endgates(maxx):
    forward_dist = maxx
    endgate = [
        EndGate(position=(forward_dist + 0.5, 0, 0 + 4), scale= (1, 65, 2), color=color.green),
        EndGate(position=(forward_dist + 0.5, 0, 0 + 2), scale= (1, 65, 2), color=color.green),
        EndGate(position=(forward_dist + 0.5, 0, 0 ), scale= (1, 65, 2), color=color.green),
        EndGate(position=(forward_dist + 0.5, 0, 0 - 2), scale= (1, 65, 2), color=color.green),
        EndGate(position=(forward_dist + 0.5, 0, 0 - 4), scale= (1, 65, 2), color=color.green)
    ]
    return endgate


# Add this function after your existing classes
def add_wireframe_border(entity, border_color=color.black, scale_offset=0.01):
    """Add a wireframe border to any entity"""
    if hasattr(entity, 'wireframe_border'):
        return  # Already has border
    
    entity.wireframe_border = Entity(
        model='wireframe_cube',
        parent=entity,
        color=border_color,
        scale=1 + scale_offset,
        always_on_top=True
    )

# Apply to your player after creation
add_wireframe_border(player, color.dark_gray, 0.02)

# --- Main Classes ---
# Loading Screen
class LoadingScreen(Entity):
    def __init__(self):
        super().__init__(parent=camera.ui, enabled=True)

        # Background quad
        self.background = Entity(
            model='quad',
            scale=(2, 2),
            color=color.black,
            z=0,  # In UI space, higher z = behind
            parent=self
        )

        # Text on top of background
        self.text = Text(
            "Loading...",
            origin=(0, 0),
            scale=2,
            background=True,
            z=-1,  # In front of background
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
        self.customise_back_button = None

    def rendermenu(self):
        global playlock
        playlock = True
        self.enabled = True
        if not self.text:
            self.text = Text("3D-DASH", origin=(0, -3), font="Techno.ttf", scale=2.5, background=True, parent=self)
        if not self.start_button:
            self.start_button = Button(text="Level Select", scale=(0.5, 0.1), position=(0, 0.1), parent=self, on_click=self.open_level_select)
        if not self.options_button:
            self.options_button = Button(text="Options", scale=(0.5, 0.1), position=(0, 0), parent=self, on_click=self.open_options)
        if not self.customise_button:
            self.customise_button = Button(text="Wardrobe", scale=(0.5, 0.1), position=(0, -0.1), parent=self, on_click=self.open_customisation)
        if not self.quit_button:
            self.quit_button = Button(text="Quit", scale=(0.5, 0.1), position=(0, -0.2), parent=self, on_click=self.quit_game)
        self.enable_menu_components(True)

    def enable_menu_components(self, enabled=True):
        if self.text: self.text.enabled = enabled
        if self.start_button: self.start_button.enabled = enabled
        if self.options_button: self.options_button.enabled = enabled
        if self.customise_button: self.customise_button.enabled = enabled
        if self.quit_button: self.quit_button.enabled = enabled

    def open_level_select(self):
        self.enable_menu_components(False)
        if not hasattr(self, 'LSS'):
            self.LSS = LevelSelect(self)
        self.LSS.updatelevelperc()
        self.LSS.show()

    def open_customisation(self):
        self.enable_menu_components(False)
        print("Opening customisation menu...")  # Debug
        
        # If CUST exists, properly destroy it first
        if hasattr(self, 'CUST') and self.CUST is not None:
            print("Destroying existing CUST...")  # Debug
            self.CUST.destroy()
            self.CUST = None
        
        # Create a new Customisation instance
        self.CUST = Customisation(self)
        self.CUST.show()
        

    def open_options(self):
        self.enable_menu_components(False)
        if not hasattr(self, 'OptMen'):
            self.OptMen = Options(self, Volume)
        self.OptMen.show()

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
            parent=self,
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
        
        self.levelpercentage = Text(text="0.0", parent=self, position=(-0.03, -0.065, -0.2), color=color.black, enabled=True)
        
        # Level data loading
        with open ("level_data.json", "r") as f:
            data = json.load(f)
        
        levelpercent = data[f"Level{self.mapcount}"]
        x_scaling = 9.95 * (float(levelpercent)/100)
        self.levelcomp.scale = (x_scaling, 1.2, 1.2)
        self.levelcomp.x = -4.95 + x_scaling / 2
        self.levelpercentage.text = (f"{str(levelpercent)}")
        
        self.level_text = Text(f"Level {self.mapcount}", position=(0, 0.04, 0), origin=(0, 0.5), scale=2, background=True, parent=self, color=color.black)
        self.start_level_button = Button(text="Start Level", scale=(0.5, 0.1), position=(0, -0.2), parent=self, on_click=self.start_game)
        self.back_button = Button(text="Back", scale=(0.1, 0.1), position=(-0.35, 0.2), parent=self, on_click=self.back_to_menu)
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
        self.levelpercentage.text = (f"{str(levelpercent)}")

    def show(self):
        self.enabled = True
        self.left_button.enabled = True
        self.right_button.enabled = True
        self.right_arrow.enabled = True
        self.left_arrow.enabled = True
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
        self.right_arrow.enabled = False
        self.left_arrow.enabled = False
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
        global game_ready, playlock, GameMap, minx, maxx, levelprog, current_mapcount, existing_gate
        self.MAP = self.MAPLIST[(int(self.mapcount) -1)]
        current_mapcount = self.mapcount
        # Render the selected map before starting the game
        if GameMap:
            GameMap.disable()
            destroy(GameMap)
            GameMap = None
        GameMap = renderMap(self.MAP)
        existing_gate = endgates(maxx)
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

#Controls the 'options' screen and the related effects on gameplay.
class Options(Entity):
    def __init__(self, main_menu, Volume):
        global returntogame, playlock, paused
        self.main_menu = main_menu
        self.volume = Volume
        self.backtothing = returntogame
        playlock = True
        
        with open ("playerdata.json", "r") as file:
            self.data = json.load(file)
        
        super().__init__(
            model='Quad',
            scale=(2, 2),
            color=color.rgba(0, 0, 255, 1),
            parent=camera.ui,
            enabled=False
        )
        
        # Initialize UI elements as None
        self.volume_slider = None
        self.sensitivity = None
        self.windowsizingdrop = None
        self.windowprop = None
        self.save = None
        self.back_button = None
        
        # Create UI elements when first shown
        self.create_ui_elements()
    
    def create_ui_elements(self):
        # Volume slider
        self.volume_slider = Slider(
            min=0, max=1, step=0.01, default=self.data["Volume"],
            text='Volume',
            scale=(0.7, 0.7, 0.7),
            position=(-0.35, -0.22, -0.3),
            parent=self,
            vertical=True,
            on_value_changed=self.set_volume 
        )

        # Slider for sensitivity
        self.sensitivity = Slider(
            min=0, max=1, step=0.01, default=self.data["Sensitivity"],
            text="Sensitivity",
            scale=(0.7, 0.7, 0.7),
            position=(0.35, -0.22, -0.3),
            parent=self,
            vertical=True,
            on_value_changed=self.set_sens
        )

        # Dropdown menu for window sizing
        self.windowsizingdrop = SimpleDropdown(
            label='Graphics',
            options=['1920x1080', "1600x900", "1536x960", "1280x720"],
            position=(-0.15, 0.1, -0.1),
            parent=self,
            on_select=self.on_windowsizingdrop_select
        )
        
        # Dropdown menu for alternate window properties
        self.windowprop = SimpleDropdown(
            label='Border',
            options=["Fullscreen", "Windowed", "Borderless Windowed"],
            position=(0.15, 0.1, -0.2),
            parent=self,
            on_select=self.on_windowprop_select
        )
        
        self.save = Button(
            text="Save Options",
            scale=(0.1, 0.1),
            position=(0.35, 0.2, -0.3),
            parent=self,
            on_click=saveplayerdata
        )

        self.back_button = Button(
            text="Back", 
            scale=(0.1, 0.1), 
            position=(-0.35, 0.2, -0.3), 
            parent=self, 
            on_click=self.back
        )
        
        # Volume slider params for the label
        if self.volume_slider and hasattr(self.volume_slider, 'label'):
            self.volume_slider.label.rotation_z = 90
            self.volume_slider.label.position = (-0.025, -0.04, 0)

        # Sens slider params for label
        if self.sensitivity and hasattr(self.sensitivity, 'label'):
            self.sensitivity.label.rotation_z = 90
            self.sensitivity.label.position = (-0.025, -0.06, 0)
    
    def on_windowsizingdrop_select(self, value):
        print(f"Selected graphics: {value}")
        updategraphics(value)
    
    def on_windowprop_select(self, Value):
        print(f"WindowSystemSelected: {Value}")
        updatewindow(Value)
    
    def set_volume(self):
        self.volume = self.volume_slider.value
        global Volume
        Volume = round(self.volume_slider.value, 2)
    
    def set_sens(self):
        self.sens = self.sensitivity.value
        global Sensitive
        Sensitive = round(self.sensitivity.value, 2)

    def show(self):
        self.enabled = True
        
        # If UI elements don't exist, create them
        if not self.volume_slider:
            self.create_ui_elements()
        
        # Enable all UI elements
        if self.volume_slider: self.volume_slider.enabled = True
        if self.sensitivity: self.sensitivity.enabled = True
        if self.windowsizingdrop: self.windowsizingdrop.enabled = True
        if self.windowprop: self.windowprop.enabled = True
        if self.save: self.save.enabled = True
        if self.back_button: self.back_button.enabled = True

    def hide(self):
        # Just disable elements instead of destroying them
        self.enabled = False
        if self.volume_slider: self.volume_slider.enabled = False
        if self.sensitivity: self.sensitivity.enabled = False
        if self.windowsizingdrop: self.windowsizingdrop.enabled = False
        if self.windowprop: self.windowprop.enabled = False
        if self.save: self.save.enabled = False
        if self.back_button: self.back_button.enabled = False

    def back(self):
        self.hide()
        if self.backtothing:
            if not hasattr(app, 'pause_menu') or app.pause_menu is None:
                app.pause_menu = PauseMenu()
            app.pause_menu.show()
            app.pause_menu.enable()
            return
        else:
            self.main_menu.enable_menu_components(True)
            
class Customisation(Entity):
    def __init__(self, main_menu):
        self.main_menu = main_menu
        self.player = player
        super().__init__(
            model='Quad',
            scale=(2, 2),
            color=color.rgba(0, 0, 255, 1),
            parent=camera.ui,
            enabled=True
        )
        
        self.back_button = Button(
            text="Back",
            scale=(0.1, 0.1),
            position=(-0.35, 0.2, -0.3),
            parent=self,
            on_click=self.back_to_menu,
            enabled=True
        )  
        
        self.playerrep = Entity(
            model='cube',
            scale=(0.15, 0.15, 0.15),
            position=(0, 0.1, -0.3),
            rotation=(62.5, 0, 45),
            texture=None,
            color=color.rgba(0, 255, 0, 1),
            parent=self,
            shader=lit_with_shadows_shader,
            enabled=True
        )  
        
        # Create CustomisationButtons instance
        self.custbutt = CustomisationButtons(
            player, 
            position=(0, 0, -0.7), 
            scale=(0.05, 0.05), 
            parent=self,
            row1name=["Blue", "Yellow", "Orange", "Purple", "Pink", "Black", "White", "Red"],
            row2name=["Christmas", "Skin1", "Skin2", "Skin3", "Skin4", "Skin5", "Skin6", "shit.png"],
        )
        self.custbutt.enabled = True
        self.custbutt.generate_buttons()
        
        print(f"Customisation created with {len(self.custbutt.allent)} button entities")  # Debug
        
    def updatethis(self, left, vel0, vel1):
        if left and self.enabled:
            rotation_speed = 400
            self.playerrep.rotation_x += vel1 * Sensitive * rotation_speed * time.dt
            self.playerrep.rotation_z -= vel0 * Sensitive * rotation_speed * time.dt
        
    def show(self):
        self.enabled = True
        self.back_button.enabled = True
        self.playerrep.enabled = True
        if hasattr(self, 'custbutt') and self.custbutt:
            self.custbutt.enabled = True
            # Don't regenerate if buttons already exist
            if not self.custbutt.allent:
                self.custbutt.generate_buttons()
    
    def back_to_menu(self):
        print("Customisation.back_to_menu() called")  # Debug
        self.cleanup()
        self.main_menu.CUST = None
        self.main_menu.rendermenu()
        
    def cleanup(self):
        print("Customisation.cleanup() called")  # Debug
        self.enabled = False
        self.back_button.enabled = False
        self.playerrep.enabled = False
        
        if hasattr(self, 'custbutt') and self.custbutt:
            self.custbutt.removeall()
            destroy(self.custbutt)
            self.custbutt = None
        
    def destroy(self):
        print("Customisation.destroy() called")  # Debug
        self.cleanup()
        super().destroy()


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
            text="0.0",
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
            self.textpercent.text = f"{self.percentagecompletion}"
            self.percentagebar()
            

def reset_game_state(menu):
    global velocity, currentztelpos, camera_locked, rot_locked, playlock, game_ready, accumulator, GameMap, main_menu

    if GameMap:
        GameMap.disable()
        destroy(GameMap)
        GameMap = None
    
    for gate in existing_gate:
        destroy(gate)
    existing_gate.clear()
    
    # Clean up PauseMenu
    if hasattr(app, 'pause_menu') and app.pause_menu:
        destroy(app.pause_menu)
        app.pause_menu = None
        
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

    if menu == True:
        # Show main menu (reuse existing)
        main_menu.enabled = True
        main_menu.enable_menu_components(True)
    else:
        pass
    
class WinScreen(Entity):
    def __init__(self):
        super().__init__(
            model='Quad',
            scale=(2, 2),
            color=color.rgba(0, 255, 0, 180),
            parent=camera.ui,
            enabled=True
        )

        self.text = Text("You Win!", origin=(0, 0), scale=2, color=color.black, parent=self, enabled = True)
        self.menu_button = Button(
            text="Main Menu",
            scale=(0.5, 0.1),
            position=(0, -0.2),
            parent=self,
            enabled = True,
            on_click=lambda: (self.disable(), reset_game_state(True))
        )

    def back_to_menu(self):
        self.enabled = False
        self.text.enabled = False
        self.menu_button.enabled = False
        main_menu.rendermenu()
    
    def disable(self):
        global playlock, paused
        self.enabled = False
        self.text.enabled = False
        self.menu_button.enabled = False
        playlock = False
        paused = False
        
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
            scale=(0.6, 0.1),
            position=(0, 0.33),
            parent=self,
            on_click=self.disable
        )
        self.options_button = Button(
            text = "Options",
            scale=(0.6, 0.1),
            position=(0, 0.11),
            parent=self,
            on_click=lambda: (self.hide(), self.optionpull())
        )
        self.mainmenubutton = Button(
            text="Main Menu",
            scale=(0.6, 0.1),
            position=(0, -0.11),
            parent=self,
            on_click=lambda: (reset_game_state(True))
        )
        self.exittodesktop_button = Button(
            text="Exit to Desktop",
            scale=(0.6, 0.1),
            position=(0, -0.33),
            parent=self,
            on_click=quit
        )
        
    def rendermenu(self):
        global playlock, paused
        playlock = True
        self.enabled = True
        self.resume_button.enabled = True
        self.mainmenubutton.enabled = True
        self.exittodesktop_button.enabled = True
        self.options_button.enabled = True
        paused = True
    
    def optionpull(self):
        global returntogame
        returntogame = True
        self.hide
        if not hasattr(self, 'OptMen'):
            self.OptMen = Options(self, Volume)
        self.OptMen.show()
    
    def removeopt(self):
        if hasattr(self, 'OptMen') and self.OptMen:
            destroy(self.OptMen)
            self.OptMen = None

    def show(self):
        global playlock, paused
        self.enabled = True
        paused = True
        self.resume_button.enabled = True
        self.mainmenubutton.enabled = True
        self.exittodesktop_button.enabled = True
        self.options_button.enabled = True
        
    def hide(self):
        global playlock, paused
        self.enabled = False
        self.resume_button.enabled = False
        self.mainmenubutton.enabled = False
        self.exittodesktop_button.enabled = False
        self.options_button.enabled = False
        playlock = True
        paused = True

    def disable(self):
        global playlock, paused
        self.enabled = False
        self.resume_button.enabled = False
        self.mainmenubutton.enabled = False
        self.exittodesktop_button.enabled = False
        self.options_button.enabled = False
        playlock = False
        paused = False

#class to generate a bunch of buttons where each one corresponds to changing the player character texture
class CustomisationButtons(Entity):
    def __init__(self, player, position=(0, 0, 0), scale=(0.1, 0.1), parent=None, row1name=[], row2name=[]):
        super().__init__(parent=parent)
        self.player = player
        self.position = position
        self.button_size = scale
        self.numperrow = 8
        self.button_spacing = (1/self.numperrow) - 0.04
        self.row1name = row1name
        self.row2name = row2name
        self.buttonrow1 = []
        self.buttonrow2 = []
        self.allent = []
        
    def generate_buttons(self):
        # Clear existing buttons first
        try:
            print("removing buttons")
            self.removeall()
        except:
            print("removal error")
            pass
        
        # Generate the buttons for the first row
        for i in range(self.numperrow):
            # Create a function that captures the current button
            def make_click_handler(btn_index):
                return lambda: self.on_button_click(f'{self.row1name[btn_index]}')
            
            button = Button(
                text=self.row1name[i],
                scale=self.button_size,
                position=(
                    (self.position[0] - 0.3) + self.button_spacing * (i % self.numperrow), 
                    self.position[0] -0.1, 
                    self.position[2]
                ),
                enabled=True,
                parent=self,
                on_click=make_click_handler(i)
            )
            self.buttonrow1.append(button)
            self.allent.append(button)
        
        # Generate the buttons for the second row
        for i in range(self.numperrow):
            # Create a function that captures the current button
            def make_click_handler(btn_index):
                return lambda: self.on_button_click(f'{self.row2name[btn_index]}')
            
            button = Button(
                text=self.row2name[i],
                scale=self.button_size,
                position=(
                    (self.position[0] - 0.3) + self.button_spacing * (i % self.numperrow), 
                    self.position[1] - 0.2, 
                    self.position[2]
                ),
                enabled=True,
                parent=self,
                on_click=make_click_handler(i)
            )
            self.buttonrow2.append(button)
            self.allent.append(button)
        
        print(f"Created {len(self.allent)} buttons")

    def on_button_click(self, button):
        # Handle button click event
        print(f'{button} clicked')
        
    #create a tooltip to show the name of the button
    def on_button_hover(self, button):
        # Handle button hover event
        print(f'{button} hovered')
    
    def removeall(self):
        print(f"Attempting to destroy {len(self.allent)} buttons")
        destroyed_count = 0
        for entity in self.allent:
            if entity and hasattr(entity, 'enabled'):
                try:
                    entity.enabled = False
                    destroy(entity)
                    destroyed_count += 1
                except Exception as e:
                    print(f"Error destroying entity: {e}")
        
        # Clear the lists
        self.buttonrow1.clear()
        self.buttonrow2.clear()
        self.allent.clear()
        
        print(f"Destroyed {destroyed_count} entities")  # Debugging line

    def destroy(self):
        self.removeall()
        super().destroy()
    
        
    
class SimpleDropdown(Entity):
    currently_open_dropdown = None
    
    def __init__(self, label, options, position=(0, 0), parent=None, on_select=None):
        super().__init__(parent=parent)
        self.label = label
        self.options = options
        self.selected = options[2]
        self.on_select = on_select
        self.main_button = Button(
            text=f'{self.label}: {self.selected}',
            position=position,
            scale=(0.25, 0.07),
            parent=self,
            on_click=self.toggle_options
        )
        self.option_buttons = []
        self.options_visible = False
    
    def toggle_options(self):
        if SimpleDropdown.currently_open_dropdown and SimpleDropdown.currently_open_dropdown is not self:
            SimpleDropdown.currently_open_dropdown.hide_options()
        if self.options_visible:
            self.hide_options()
        else:
            if not self.option_buttons:
                for i, option in enumerate(self.options):
                    b = Button(
                        text=option,
                        position=(self.main_button.x, self.main_button.y - (i+1)*0.08, -1),
                        scale=(0.2, 0.05),
                        parent=self,
                        enabled=True,
                        on_click=Func(self.select_option, option)
                    )
                    self.option_buttons.append(b)
            else:
                for b in self.option_buttons:
                    b.enable()
            self.options_visible = True
            SimpleDropdown.currently_open_dropdown = self
    
    def hide_options(self):
        for b in self.option_buttons:
            b.disable()
        self.options_visible = False
        if SimpleDropdown.currently_open_dropdown is self:
            SimpleDropdown.currently_open_dropdown = None

    def select_option(self, option):
        self.selected = option
        self.main_button.text = f'{self.label}: {self.selected}'
        self.toggle_options()
        if self.on_select:
            self.on_select(option)

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
            # Ensure pause_menu exists
            if not hasattr(app, 'pause_menu') or app.pause_menu is None:
                app.pause_menu = PauseMenu()

            try:
                # Check if menu is already active
                if app.pause_menu.enabled:
                    app.pause_menu.disable()
                else:
                    # Make sure the menu is still valid
                    if app.pause_menu.children:
                        app.pause_menu.rendermenu()
                    else:
                        # Recreate it if the node got cleaned up
                        app.pause_menu = PauseMenu()
                        app.pause_menu.rendermenu()
            except Exception as e:
                print(f"Pause menu error: {e}")
                app.pause_menu = PauseMenu()
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

# Create and keep a reference for loadingscreen and levelprogress
loading_screen = LoadingScreen()  
levelprog = LevelProgress()

# set a function to prerender all variables
# apply it to a thread and call the loading screen while it's running
#upon finish, invoke finish_loading to hide the loading screen and set game_ready to True

def prerendering():
    global death_anim, loading_screen
    loading_screen.enable()
    # --- PRELOAD all animation frames to avoid first-run lag ---
    for frame in death_anim_frames:
        e = Entity(model=frame, enabled=True)
        invoke(e.disable, delay=0.1)  # Let it render for one frame, then disable

    death_anim = BakedMeshAnimation(death_anim_frames, scale=(1,1,1), texture=None, color=(0.906, 0.501, 0.070, 1), shader=lit_with_shadows_shader)
    death_anim.disable()

    # After all loading is done, schedule finish_loading
    invoke(finish_loading, delay=0.1)



def finish_loading():
    global main_menu, loading_screen
    loading_screen.disable()  # Disable the correct instance
    #load main menu
    main_menu = MainMenu()
    main_menu.rendermenu()

renderthread = threading.Thread(target=prerendering, daemon=True)
renderthread.start()


# --- Main Update Loop ---
def update():
    global accumulator, main_menu

    if (hasattr(main_menu, 'CUST') and main_menu.CUST and main_menu.CUST.enabled and hasattr(main_menu.CUST, 'updatethis')):
        # Only update when customisation menu is active
        main_menu.CUST.updatethis(mouse.left, mouse.velocity[0], mouse.velocity[1])
    
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
    global velocity, is_grounded, currentztelpos, camera_loc, camera_locked, rot_locked, Sensitive
    
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
        #Determine whether this collision is the endgate or a real death
        if hit_info_death.entity in existing_gate:
            levelprog.percentagecompletion = "100.0"
            #Force respawn the player to avoid multi-checking the winscreen function over multiple iterations
            reset_game_state(False)
            respawn_player()
            player.disable()
            WinScreen().enable()
            savehigh(current_mapcount, "100.0")
            return
        
        #Save highscore
        savehigh(current_mapcount, levelprog.percentagecompletion)
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
            camera_loc.x -= mouse.velocity[0] * return_speed * 3000 * Sensitive * time.dt
            camera_loc.y += mouse.velocity[1] * return_speed * 3000 * Sensitive * time.dt
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
