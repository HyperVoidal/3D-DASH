from ursina import *
from ursina import Button, Slider, destroy, DirectionalLight, lerp, distance
from ursina.shaders import lit_with_shadows_shader, basic_lighting_shader
from panda3d.core import RenderState
from math import radians, cos, sin, isnan, isinf
import time
import threading 
import shutil
import matplotlib.pyplot as plt
import matplotlib as mpl
import json
import os
from PIL import Image, ImageDraw
from ursina.mesh import Mesh
from pathlib import Path

resource_path = Path(__file__).parent.absolute()

#Detect and fix any missing .json files
def dataverify_repair():
    #List of files to check and their important information (set to defaults)
    datafiles = {
        "Assets/Datafiles/playerdata.json": {
            "Volume": 0.5,
            "Sensitivity": 0.5,
            "ButtonControls": ["a", "d", "space"]
        },
        "Assets/Datafiles/level_data.json": {
            f"Level{i + 1}": "0.0" for i in range(4)  # Adjust number of levels as needed
        },
        "Assets/Datafiles/skindata.json": {
            "Orange": [1, 1],
            "Red": [0, 1], 
            "Yellow": [0, 1], 
            "Green": [0, 1], 
            "Azure": [0, 1], 
            "Magenta": [0, 1], 
            "Black": [0, 1], 
            "White": [0, 1], 
            "Pink": [0, 1], 
            "Lime": [0, 1], 
            "Cyan": [0, 1], 
            "Turquoise": [0, 1], 
            "Clear": [0, 0], 
            "StripeBlue": [0, 0], 
            "Warm_Glow": [0, 0], 
            "shit.jpg": [0, 0]
            # Needs to be personally updated. While I wish I could have it all depend on the json file, data integrity is crucial.
        }
    }

    for rel_path, default_data in datafiles.items():
        abs_path = resource_path / rel_path
        # Ensure parent directory exists
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        needs_repair = False
        if not abs_path.exists():
            needs_repair = True
        else:
            try:
                with open(abs_path, "r") as f:
                    json.load(f)
            except Exception:
                needs_repair = True
        if needs_repair:
            with open(abs_path, "w") as f:
                json.dump(default_data, f, indent=2)

# Call before any other file I/O
dataverify_repair()

def setUNIXpath(resource_path):
    resource_path = str(resource_path)
    resource_path = resource_path.replace("\\", "/")
    resource_path = resource_path.replace(":", "")
    resource_path = "/" + resource_path
    return resource_path
    
    

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
    def center_after_resize():
        window.center_on_screen()
    
    invoke(center_after_resize, delay=0.05)

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
    def center_after_resize():
        window.center_on_screen()
    
    invoke(center_after_resize, delay=0.05)

def skinapply(skin):
    global player
    skin = (str(skin)).lower()  
    if skin == 'locked':
        return
    
    # First check if it's a color name
    try:
        color_value = getattr(color, skin)
        player.texture = None
        player.color = color_value
    except AttributeError:
        # Not a color name, try as a texture path
        try:
            # Use relative path for Ursina (it prefers relative paths)
            relative_texture_path = f"Assets/Textures/{skin}.jpg"
            # Use absolute path for file existence check
            absolute_texture_path = resource_path / "Assets" / "Textures" / f"{skin}.jpg"
            
            # Check if the file exists using absolute path
            if absolute_texture_path.exists():
                player.color = color.white  # Reset color to white for texture
                player.texture = relative_texture_path  # Use relative path for Ursina
            else:
                # Try alternative paths or fallback
                fallback_absolute = resource_path / "Assets" / "Textures" / "skinnotfound.png"
                fallback_relative = "Assets/Textures/skinnotfound.png"
                if fallback_absolute.exists():
                    player.texture = fallback_relative
                    player.color = color.white
                else:
                    # Final fallback to color
                    player.texture = None
                    player.color = color.orange
                
        except Exception as e:
            print(f"Error applying texture: {e}")
            # Fallback to a default color
            player.texture = None
            player.color = color.orange
            
    try:
        death_anim.texture = player.texture
        death_anim.color = player.color 
    except:
        pass

    # Update skin data
    with open(f'{resource_path}/Assets/Datafiles/skindata.json', 'r') as f:
        data = json.load(f)
    
    # Reset all values to 0
    for key in data:
        data[key][0] = 0
    
    # Set the selected skin to 1
    skin_found = False
    for key in data:
        if key.lower() == skin.lower():
            data[key][0] = 1
            skin_found = True
            break
    
    if not skin_found:
        print(f"Warning: skin '{skin}' not found in database")
    
    with open(f'{resource_path}/Assets/Datafiles/skindata.json', 'w') as f:
        json.dump(data, f)


def load_playerskins():
    with open(f'{resource_path}/Assets/Datafiles/skindata.json', 'r') as f:
        data = json.load(f)
    
    # find what skin is equipped
    for key, value in data.items():
        if value[0] == 1:
            skinapply(key)
            break


app = Ursina()
window.show_ursina_splash = True
window.title = "3D DASH"
#remember to set a custom icon when exporting this program to an exe, you can't change taskbar icon in normal ursina
window.icon = "window_icon.ico"
skybox_image = load_texture("Assets/Textures/sky_sunset.jpg")


# --- PRE-APP SETUP AND VARIABLES ---

# Model Loading
# Player entity with a collider
#rgba value is set to the blender colour of the player model
class PlayerMarker(Entity):
    def __init__(self):
        super().__init__(
            model='arrowNOBG.obj',  # Using your existing arrow model
            scale=(0.1, 0.1, 0.1),
            color=color.orange,  # Match player color
            texture=None,
            rotation=(0, -45, -90),
            enabled=False,  # Hidden by default
            always_on_top=True,  # Always render on top
        )
        self.pulse_time = 0
        self.base_scale = 0.1
        
    def update_position(self, player_pos):
        """Update marker position above player"""
        if not death_anim.playing:
            self.position = player_pos + Vec3(0, 2, 0)  # 2 units above player
        
    def update_pulse(self):
        """Add pulsing animation to make marker more visible"""
        self.pulse_time += time.dt  # Pulse speed
        pulse_factor = 1 + 0.3 * math.sin(self.pulse_time)  # 30% size variation
        self.scale = Vec3(self.base_scale * pulse_factor, self.base_scale * pulse_factor, self.base_scale * pulse_factor)

sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
sun.shadows = True
sun.color = color.white
sun.intensity = 2.0  # Increase intensity
Sky(texture=skybox_image, scale=0.01)

""" sun.shadow_map_size = (2048, 2048)  # Increase shadow map size
sun.shadow_map_resolution = (1024, 1024)
sun.shadow_camera_size = 100 """

ambient = AmbientLight(color=color.rgba(50, 50, 50, 0.1))

app.fog_density = 0.1  # Much lighter fog

with open (f'{resource_path}/Assets/Datafiles/skindata.json', 'r') as f:
    skindata = json.load(f)

player = Entity(model='cube', 
                texture=None, 
                color=color.orange,
                scale=(1, 1, 1), 
                collider='box', 
                position=(0, 30, 0), 
                shader=lit_with_shadows_shader)

load_playerskins()

player_marker = PlayerMarker()


def create_synthwave_grid_texture(width=512, height=512, grid_size=32):
    """Create a synthwave-style grid texture"""
    # Create image
    img = Image.new('RGBA', (width, height), (0, 0, 0, 255))  # Black background
    draw = ImageDraw.Draw(img)
    
    # Grid colors (synthwave palette)
    grid_color = (255, 0, 255, 255)  # Magenta
    accent_color = (0, 255, 255, 255)  # Cyan
    
    # Draw vertical lines
    for x in range(0, width, grid_size):
        color = accent_color if x % (grid_size * 4) == 0 else grid_color
        draw.line([(x, 0), (x, height)], fill=color, width=2)
    
    # Draw horizontal lines
    for y in range(0, height, grid_size):
        color = accent_color if y % (grid_size * 4) == 0 else grid_color
        draw.line([(0, y), (width, y)], fill=color, width=2)
    
    # Save texture
    img.save('synthwave_grid.png')
    return 'synthwave_grid.png'

def create_procedural_cylinder_skybox():
    """Create a procedural cylinder skybox"""
    
    # Generate the grid texture
    grid_texture = create_synthwave_grid_texture()
   
    # Generate cylinder vertices
    segments = 64  # Higher = smoother cylinder
    height = 200
    radius = 300
    
    vertices = []
    triangles = []
    uvs = []
    
    # Create cylinder vertices
    for i in range(segments + 1):
        angle = (i / segments) * 2 * math.pi
        x = math.cos(angle) * radius
        z = math.sin(angle) * radius
        
        # Bottom vertex
        vertices.append((x, -height/2, z))
        uvs.append((i/segments, 0))
        
        # Top vertex  
        vertices.append((x, height/2, z))
        uvs.append((i/segments, 1))
    
    # Create triangles for cylinder walls
    for i in range(segments):
        # Each quad becomes 2 triangles
        base = i * 2
        next_base = ((i + 1) % segments) * 2
        
        # Triangle 1
        triangles.append((base, base + 1, next_base))
        # Triangle 2  
        triangles.append((next_base, base + 1, next_base + 1))
    
    # Create the mesh
    cylinder_mesh = Mesh(vertices=vertices, triangles=triangles, uvs=uvs)
    
    return Entity(
        model=cylinder_mesh,
        texture=grid_texture,
        rotation = (0, 0, 90),
        position=(0, 0, 0),
        double_sided=True,  # Important: render from inside
        unlit=True,  # No lighting for consistent appearance
        color=color.white,
        scale=(1, 10, 1)
    )

# Replace your cylSky with this:
cylSky = create_procedural_cylinder_skybox()

def check_player_occlusion():
    """Check if player is behind any objects from camera perspective"""
    camera_to_player = player.position - camera.position
    distance_to_player = camera_to_player.length()
    direction = camera_to_player.normalized()
    
    # Raycast from camera toward player
    hit_info = raycast(
        origin=camera.position,
        direction=direction,
        distance=distance_to_player - 0.1,  # Stop just before player
        ignore=[player, player_marker]  # Ignore player and marker
    )
    
    return hit_info.hit

def update_player_marker():
    """Update marker visibility and position"""
    is_occluded = check_player_occlusion()
    
    if is_occluded:
        if not player_marker.enabled:
            player_marker.enabled = True
        
        player_marker.update_position(player.position)
        player_marker.update_pulse()
    else:
        player_marker.enabled = False
        

# Prepare the list of animation frames
#Death animation frames
death_anim_frames = [f'Anims/cubedeathani/miniexplode.f{str(i).zfill(4)}.glb' for i in range(1, 45)]
#main menu loop
startmen_frames = [f"Anims/MenuFrames/{str(i).zfill(4)}.png" for i in range(1, 99)]
mainmenuloop_frames = [f"Anims/MenuFrames/{str(i).zfill(4)}.png" for i in range(100, 158)]
exitmen_frames = [f"Anims/MenuFrames/{str(i).zfill(4)}.png" for i in range(160, 250)]

#Import Json file
with open (f"{resource_path}/Assets/Datafiles/level_data.json", "r") as f:
    data = json.load(f)
       
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

#potato mode flags
shaderstatus = True
playerdeathstatus = True
menuanimstatus = True

#Map Data
MAPLIST = []
for key in data:
    MAPLIST.append(str(key))
MAP = None
main_menu = None
GameMap = None
minx = 0
maxx = 0
current_mapcount = 1
menu_music_playing = True
buttoncontrols = ["a", "d", "space"] #left, right, jump IN THAT ORDER
gravswapping = False
existing_gravswap = None


#Main systems for fps and update control
fixed_dt = 1/60  # 60 updates per second
accumulator = 0

#Options menu systems
with open (f"{resource_path}/Assets/Datafiles/playerdata.json", "r") as f:
    data = json.load(f)
Volume = data["Volume"]
Sensitive = data["Sensitivity"]
buttoncontrols = data["ButtonControls"]
returntogame = False
game_ready = False
Text.default_font = f"{setUNIXpath(resource_path)}/Assets/Font/2TECH2.ttf"

#SFX and Music Loading
def load_audio():
    global buttonclick_sound, menuback_music, warp_sound, death_sound, levelcomp_sound
    try:
        buttonclick_sound = Audio('Assets/Sounds/MenuClick.mp3', autoplay=False, loop=False)
        menuback_music = Audio('Assets/Sounds/MenuBGM.wav', autoplay=True, loop=True)
        warp_sound = Audio("Assets/Sounds/playerwarpsfx.mp3", autoplay=False, loop=False)
        death_sound = Audio("Assets/Sounds/EXPLODE.mp3", autoplay=False, loop=False)
        levelcomp_sound = Audio("Assets/Sounds/LevelComplete.mp3", autoplay=False, loop=False)
    except:
        print("Warning: Some audio files not found. It is possible that certain SFX and Music will not play.")

def applyvolume(Volume):
    buttonclick_sound.volume = Volume
    menuback_music.volume = Volume * 0.25
    warp_sound.volume = Volume * 2
    death_sound.volume = Volume / 3
    levelcomp_sound.volume = Volume



class GravSwapGate(Entity):
    def __init__(self, position, scale):
        super().__init__(
            model='cube', 
            scale=scale, 
            collider='box', 
            color=color.rgba(163, 0, 163, 0.7), 
            position=position, 
            shader=lit_with_shadows_shader
        )
        self.entity_type = 'gravswap'
        self.cooldown = False  # Add cooldown flag to prevent multiple triggers
        
    def start_cooldown(self):
        self.cooldown = True
        invoke(self.reset_cooldown, delay=1.0)  # Reset after 1 second
        
    def reset_cooldown(self):
        self.cooldown = False
        
    def destroy(self):
        self.disable()
        
def gravswap(mapname):
    global existing_gravswap
    
    # Initialize an empty list if it doesn't exist
    if existing_gravswap is None:
        existing_gravswap = []
    
    gates = []
    
    if mapname == "Level3":
        gate = GravSwapGate(position=(100, 5, 0), scale=(1, 16, 10))
        gate.tag = 'gravswap_gate'
        gates.append(gate)
        
    elif mapname == "Level4":
        gate = GravSwapGate(position=(32.5, 5, 0), scale=(1, 10, 10))
        gate.tag = 'gravswap_gate'
        gates.append(gate)

        gate2 = GravSwapGate(position=(56, 5, 2), scale=(1, 10, 2))
        gate2.tag = 'gravswap_gate'
        gates.append(gate2)

        gate3 = GravSwapGate(position=(88, 7.5, 0), scale=(1, 4.5, 2))
        gate3.tag = 'gravswap_gate'
        gates.append(gate3)
    
    else:
        pass

    
    # Store all created gates in the global list
    existing_gravswap = gates
    
    return gates
    
def gravswapper():
    global player, gravity, camera, return_rotation, gravswapping, velocity
    gravity = -gravity
    player.x += 2
    if gravity < 0:
        player.y -= 1
    else:
        player.y += 1
    
    velocity = 0
    
    #Cool screen effect of moving purple quad to show direction of gravity
    if gravity != abs(gravity):
        swap_effect = Entity(model='quad',
                        parent=camera.ui,
                        scale = (2, 0.5),
                        color= color.rgba(163, 0, 163, 0.7),
                        position=(0, 1, -0.1)
                        )
        swap_effect.animate_position(
        Vec3(0, -1.5, -0.1),
        duration=0.5,
        curve=curve.linear
        )
        invoke(destroy, swap_effect, delay=0.6)
        
    else:
        swap_effect = Entity(model='quad',
                         parent=camera.ui,
                         scale = (2, 0.5),
                         color= color.rgba(163, 0, 163, 0.7),
                         position=(0, -1, -0.1)
                         )
            
        swap_effect.animate_position(
            Vec3(0, 1.5, -0.1),
            duration=0.5,
            curve=curve.linear
        )
        invoke(destroy, swap_effect, delay=0.6)
    
    
    if gravity != abs(gravity):
        return_rotation = Vec3(0, 45, 0)
    else:
        return_rotation = Vec3(180, 45, 0)
        
    
    invoke(lambda: globals().update({'gravswapping': False}), delay=0.5) #Update the globals dictionary to set gravswapping to False
    
def renderMap(map_name):
    global GameMap, minx, maxx, sun, existing_gravswap, camera, player, shaderstatus
    x_scale = 2
    
    camera.position = Vec3(-20, 20, -20)  # Initial camera position
    camera.rotation = Vec3(0, 45, 0) #Initial camera rotation
    camera.look_at(player.position) # Initial look at
    
    GameMap = Entity(model=f'{map_name}.obj', collider='mesh')
    GameMap.scale = (x_scale, 1, 1.5)
    GameMap.rotation = (0, 270, 0)

    GameMap.collider = 'mesh'

    if hasattr(GameMap, 'collision'):
        GameMap.collision = None
    GameMap.collision = GameMap.model

    if shaderstatus == True:
        GameMap.shader = lit_with_shadows_shader
        GameMap.cast_shadows = True
        GameMap.receive_shadows = True
    else:
        pass
    
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
    existing_gravswap = gravswap(map_name)
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
    with open (f'{resource_path}/Assets/Datafiles/level_data.json', 'r') as file:
        data = json.load(file)
    if float(data[f"Level{mapcount}"]) < float(perccomp):
        data[f"Level{mapcount}"] = (f"{perccomp}")
        with open (f"{resource_path}/Assets/Datafiles/level_data.json", 'w') as file:
            json.dump(data, file)
    else:
        pass

def saveplayerdata():
    global Sensitive, Volume, buttoncontrols
    data = {
        "Sensitivity": Sensitive,
        "Volume": Volume,
        "ButtonControls": buttoncontrols
    }
    with open (f"{resource_path}/Assets/Datafiles/playerdata.json", "w") as file:
        json.dump(data, file)

def unlock_skins():
    with open(f"{resource_path}/Assets/Datafiles/skindata.json", "r") as f:
        skinsdata = json.load(f)
    with open(f"{resource_path}/Assets/Datafiles/level_data.json", "r") as f:
        levelsdata = json.load(f)
    
    # Get all skin keys as a list and slice from index 12 (13th item) onwards
    all_skins = list(skinsdata.keys())
    skins_13_and_above = all_skins[12:]  # Index 12 = 13th item
    
    # Iterate over the skins and set their status to "unlocked"
    # Map specific levels to specific skins
    for i, skin in enumerate(skins_13_and_above):
        level_key = f"Level{i+1}"  # Level1 unlocks first skin, Level2 unlocks second, etc.
        if level_key in levelsdata and levelsdata[level_key] == "100.0":
            skinsdata[skin][1] = 1
    
    with open (f"{resource_path}/Assets/Datafiles/skindata.json", "w") as f:
        json.dump(skinsdata, f)

    return

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
    endgate_list = [    
        EndGate(position=(forward_dist + 0.5, 0, 0 + 4), scale= (1, 65, 2), color=color.green),
        EndGate(position=(forward_dist + 0.5, 0, 0 + 2), scale= (1, 65, 2), color=color.green),
        EndGate(position=(forward_dist + 0.5, 0, 0 ), scale= (1, 65, 2), color=color.green),
        EndGate(position=(forward_dist + 0.5, 0, 0 - 2), scale= (1, 65, 2), color=color.green),
        EndGate(position=(forward_dist + 0.5, 0, 0 - 4), scale= (1, 65, 2), color=color.green)
    ]
    
    # Set the tag on each individual gate in the list
    for gate in endgate_list:
        gate.tag = "endgate"
        
    return endgate_list


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
        always_on_top = False,
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
        global menuanimstatus
        super().__init__(
            model='Quad',
            scale=(2, 2),
            color=color.rgba(0, 0, 255, 0),  # rgb + opacity
            parent=camera.ui,
            enabled=False
        )
        
        # Create animated background
        if menuanimstatus == False:
            self.color=color.rgba(0, 0, 255, 100)
            self.animated_background = None
        else:
            self.animated_background = AnimatedBackground(startmen_frames, mainmenuloop_frames)
            self.animated_background.parent = self
            self.animated_background.z = 0.1
        

        self.text = None
        self.start_button = None
        self.options_button = None
        self.customise_button = None
        self.quit_button = None
        self.customise_back_button = None
        self.reset_button = None
        self.potatomode_button = None

    def rendermenu(self):
        #globals
        global playlock, menuanimstatus
        playlock = True
        self.enabled = True
        
        #only play animation if it exists and is allowed to play
        if hasattr(self, 'animated_background') and self.animated_background and menuanimstatus:
            self.animated_background.play()

        #Construct the menu button controls
        if not self.text:
            self.text = Text("3D-DASH", origin=(0, -1.5), font=f"{setUNIXpath(resource_path)}/Assets/Font/Techno.ttf", scale=2.5, background=True, parent=self)
        if not self.start_button:
            self.start_button = Button(text="Level Select", scale=(0.25, 0.05), position=(0, -0.05), parent=self, on_click=lambda: (buttonclick_sound.play(), self.open_level_select()))
        if not self.options_button:
            self.options_button = Button(text="Options", scale=(0.25, 0.05), position=(0, -0.1), parent=self, on_click=lambda: (buttonclick_sound.play(), self.open_options()))
        if not self.customise_button:
            self.customise_button = Button(text="Wardrobe", scale=(0.25, 0.05), position=(0, -0.15), parent=self, on_click=lambda: (buttonclick_sound.play(), self.open_customisation()))
        if not self.quit_button:
            self.quit_button = Button(text="Quit", scale=(0.25, 0.05), position=(0, -0.2), parent=self, on_click=lambda: (buttonclick_sound.play(), self.quit_game()))
        if not self.reset_button:
            self.reset_button = Button(text="Reset all data", scale=(0.15, 0.025), position=(-0.3, -0.2), parent=self,  on_click=lambda: (buttonclick_sound.play(), self.resetdata()))
        if not self.potatomode_button:
            self.potatomode_button = Button(text="Potato Mode", scale=(0.15, 0.025), position=(0.3, -0.2), parent=self, on_click=lambda: (buttonclick_sound.play(), self.potatomode()))
        self.enable_menu_components(True)

    def enable_menu_components(self, enabled=True):
        if self.text: self.text.enabled = enabled
        if self.start_button: self.start_button.enabled = enabled
        if self.options_button: self.options_button.enabled = enabled
        if self.customise_button: self.customise_button.enabled = enabled
        if self.quit_button: self.quit_button.enabled = enabled
        if self.reset_button: self.reset_button.enabled = enabled
        if self.potatomode_button: self.potatomode_button.enabled = enabled
        
    def potatomode(self):
        global shaderstatus, playerdeathstatus, menuanimstatus, death_anim, GameMap
        
        # Toggle all potato mode flags
        shaderstatus = not shaderstatus
        playerdeathstatus = not playerdeathstatus
        menuanimstatus = not menuanimstatus
        
        # Handle menu background animation
        if hasattr(self, 'animated_background') and self.animated_background:
            if not menuanimstatus:  # Potato mode ON
                self.animated_background.stop()
                destroy(self.animated_background)
                self.animated_background = None
                self.color = color.rgba(0, 0, 255, 100)  # Solid background
            else:  # Potato mode OFF - this won't trigger in current logic, see fix below
                pass
        elif menuanimstatus:  # Potato mode OFF, need to create animation
            self.color = color.rgba(0, 0, 255, 0)  # Transparent background
            self.animated_background = AnimatedBackground(startmen_frames, mainmenuloop_frames)
            self.animated_background.parent = self
            self.animated_background.z = 0.1
            if self.enabled:
                self.animated_background.play()
        
        # Handle map shaders
        if GameMap and hasattr(GameMap, 'shader'):
            if shaderstatus:
                GameMap.shader = lit_with_shadows_shader
                GameMap.cast_shadows = True
                GameMap.receive_shadows = True
            else:
                GameMap.shader = None
                GameMap.cast_shadows = False
                GameMap.receive_shadows = False
        
        # Handle player shader
        if shaderstatus:
            player.shader = lit_with_shadows_shader
        else:
            player.shader = None
        

        
        

    def open_level_select(self):
        self.enable_menu_components(False)
        if not hasattr(self, 'LSS'):
            self.LSS = LevelSelect(self)
        self.LSS.updatelevelperc()
        self.LSS.show()

    def open_customisation(self):
        self.enable_menu_components(False)
        
        # If CUST exists, properly destroy it first
        if hasattr(self, 'CUST') and self.CUST is not None:
            self.CUST.destroy()
            self.CUST = None
        
        # Create a new Customisation instance
        self.CUST = Customisation(self)
        self.CUST.show()
        

    def open_options(self):
        self.enable_menu_components(False)
        if not hasattr(self, 'OptMen'):
            self.OptMen = Options(self, Volume)
        self.OptMen.backtothing = False
        self.OptMen.show()
    
    def resetdata(self):
        global Volume, Sensitive, buttoncontrols
        #Reset playerdata file to defaults
        with open(f"{resource_path}/Assets/Datafiles/playerdata.json", "w") as file:
            json.dump({"Volume": 0.5, "Sensitivity": 0.5, "ButtonControls": ["a", "d", "space"]}, file)
        
        #Reset level_data file to defaults of 0 on each level
        with open (f'{resource_path}/Assets/Datafiles/level_data.json', 'r') as file:
            data = json.load(file)
        for i in range(len(data.keys())):
            data[f"Level{i+1}"] = "0.0"
        with open(f"{resource_path}/Assets/Datafiles/level_data.json", "w") as file:
            json.dump(data, file)
        
        #Reset skin data file for skins 13 and above to 'locked' (value of 0)
        with open(f"{resource_path}/Assets/Datafiles/skindata.json", "r") as file:
            data = json.load(file)
        all_skins = list(data.keys())
        skins_13_and_above = all_skins[12:]  # This gets skins from index 12 onwards
        
        # Reset unlock status for skins 13 and above
        for skin_key in skins_13_and_above:
            if skin_key in data:
                data[skin_key][1] = 0  # Set to locked
        
        # Equip the first skin (assuming it exists)
        first_skin = all_skins[0] if all_skins else None
        if first_skin and first_skin in data:
            data[first_skin][0] = 1  # Equip first skin
        
        with open(f"{resource_path}/Assets/Datafiles/skindata.json", "w") as file:
            json.dump(data, file)
        
        # Update all variables for reset components
        Volume = 0.5
        Sensitive = 0.5
        buttoncontrols = ["a", "d", "space"]
        
        # Apply the default skin to the player
        if first_skin:
            skinapply(first_skin)
        
        # Apply default volume
        applyvolume(Volume=Volume)
        
        # Update UI components if they exist
        # Update options menu sliders
        if hasattr(self, 'OptMen'):
            if hasattr(self.OptMen, 'volume_slider') and self.OptMen.volume_slider:
                self.OptMen.volume_slider.value = Volume
            if hasattr(self.OptMen, 'sensitivity') and self.OptMen.sensitivity:
                self.OptMen.sensitivity.value = Sensitive
            
            # Update button control text
            if hasattr(self.OptMen, 'rebindleft_button') and self.OptMen.rebindleft_button:
                self.OptMen.rebindleft_button.text = f"Left: {buttoncontrols[0]}"
            if hasattr(self.OptMen, 'rebindright_button') and self.OptMen.rebindright_button:
                self.OptMen.rebindright_button.text = f"Right: {buttoncontrols[1]}"
            if hasattr(self.OptMen, 'rebindjump_button') and self.OptMen.rebindjump_button:
                self.OptMen.rebindjump_button.text = f"Jump: {buttoncontrols[2]}"
        
        # Update level select screen if it exists
        if hasattr(self, 'LSS') and self.LSS:
            self.LSS.updatelevelperc()
        
        # Update customization menu if it exists
        if hasattr(self, 'CUST') and self.CUST:
            # Force recreate the customization menu to refresh skin data
            self.CUST.cleanup()
            self.CUST = None
            # The menu will be recreated when opened next time

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
        
        
        self.left_button = Button(text="", color=color.rgba(128, 128, 128, 0.75), scale=(0.1, 0.1), position=(-0.3, 0), parent=self, on_click=lambda: (buttonclick_sound.play(), self.previous_level()))
        self.left_arrow = Entity(
            model='Assets/Objects/arrowNOBG.obj',
            scale=(0.03, 0.03, 0.03),
            parent=self.left_button,
            position=(0, 0, -0.01),
            rotation=(90, 0, 0),
            color=color.white,
            texture=None
        )

        self.right_button = Button(text="", color=color.rgba(128, 128, 128, 0.75), scale=(0.1, 0.1), position=(0.3, 0), parent=self, on_click=lambda: (buttonclick_sound.play(), self.next_level()))
        self.right_arrow = Entity(
            model='Assets/Objects/arrowNOBG.obj',
            scale=(0.03, 0.03, 0.03),  
            parent=self.right_button,
            position=(0, 0, -0.01),    
            rotation=(90, 180, 0),
            color=color.white,
            texture=None
        )
        self.levelperc = Entity(
            model = 'Assets/Objects/ProgressBar.obj',
            scale=(0.08, 0.03, 0.03),
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
        with open (f"{resource_path}/Assets/Datafiles/level_data.json", "r") as f:
            data = json.load(f)
        
        levelpercent = data[f"Level{self.mapcount}"]
        x_scaling = 9.95 * (float(levelpercent)/100)
        self.levelcomp.scale = (x_scaling, 1.2, 1.2)
        self.levelcomp.x = -4.95 + x_scaling / 2
        self.levelpercentage.text = (f"{str(levelpercent)}")
        
        self.level_text = Text(f"Level {self.mapcount}", position=(0, 0.04, 0), origin=(0, 0.5), scale=2, background=True, parent=self, color=color.black)
        self.start_level_button = Button(text="Start Level", scale=(0.5, 0.1), position=(0, -0.2), parent=self, on_click=self.start_game)
        self.back_button = Button(text="Back", scale=(0.1, 0.1), position=(-0.35, 0.2), parent=self, on_click=lambda: (buttonclick_sound.play(), self.back_to_menu()))
        self.PlayerMap = None
        self.colorscale = None
        self.hide()
    
    def updatelevelperc(self):
        # Level data loading
        with open (f"{resource_path}/Assets/Datafiles/level_data.json", "r") as f:
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
        global game_ready, playlock, GameMap, minx, maxx, levelprog, current_mapcount, existing_gate, existing_gravswap
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
        global returntogame, playlock, paused, buttoncontrols
        self.main_menu = main_menu
        self.volume = Volume
        self.backtothing = returntogame
        playlock = True
        self.button_controls = buttoncontrols
        
        with open (f"{resource_path}/Assets/Datafiles/playerdata.json", "r") as file:
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
            options=["1600x900", "1536x960", "1280x720", "800x600"],
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
            text="Save",
            scale=(0.1, 0.1),
            position=(0.35, 0.2, -0.3),
            parent=self,
            on_click=lambda: (buttonclick_sound.play(), saveplayerdata())
        )
        self.back_button = Button(
            text="Back", 
            scale=(0.1, 0.1), 
            position=(-0.35, 0.2, -0.3), 
            parent=self, 
            on_click=lambda: (buttonclick_sound.play(), self.back())
        )
        
        # ControlButton LEFT
        self.rebindleft_button = Button(
            text=f"Left: {self.button_controls[0]}",
            scale=(0.15, 0.075),
            position=(-0.2, 0.2, -0.3),
            parent=self,
            on_click=lambda: (buttonclick_sound.play(), self.rebind_control("left"))
        )
        
        # ControlButton RIGHT
        self.rebindright_button = Button(
            text=f"Right: {self.button_controls[1]}",
            scale=(0.15, 0.075),
            position=(0, 0.2, -0.3),
            parent=self,
            on_click=lambda: (buttonclick_sound.play(), self.rebind_control("right"))
        )
        
        # ControlButton JUMP
        self.rebindjump_button = Button(
            text=f"Jump: {self.button_controls[2]}",
            scale=(0.15, 0.075),
            position=(0.2, 0.2, -0.3),
            parent=self,
            on_click=lambda: (buttonclick_sound.play(), self.rebind_control("jump"))
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
        updategraphics(value)
    
    def on_windowprop_select(self, Value):
        updatewindow(Value)
    
    def set_volume(self):
        self.volume = self.volume_slider.value
        global Volume
        Volume = round(self.volume_slider.value, 2)
        applyvolume(Volume=Volume)
    
    def set_sens(self):
        self.sens = self.sensitivity.value
        global Sensitive
        Sensitive = round(self.sensitivity.value, 2)
        
    def rebind_control(self, control_name):
        global buttoncontrols
        # Get all keys currently being pressed
        def after_delay(input_key):
            if input_key == 'control':
                input_key = 'space'
            if control_name == "left":
                self.button_controls[0] = input_key
            elif control_name == "right":
                self.button_controls[1] = input_key
            elif control_name == "jump":
                self.button_controls[2] = input_key
            self.rebindleft_button.text = f"Left: {self.button_controls[0]}"
            self.rebindjump_button.text = f"Jump: {self.button_controls[2]}"
            self.rebindright_button.text = f"Right: {self.button_controls[1]}"
            buttoncontrols = self.button_controls
            saveplayerdata()
                
        invoke(lambda: after_delay(returnheldkeys()), delay=0.5)
        

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
        global returntogame
        self.hide()
        if self.backtothing:
            if not hasattr(app, 'pause_menu') or app.pause_menu is None:
                app.pause_menu = PauseMenu()
            app.pause_menu.show()
            app.pause_menu.enable()
            return
        else:
            self.disable()
            self.main_menu.enable_menu_components(True)
            returntogame=False
            
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
            on_click=lambda: (buttonclick_sound.play(), self.back_to_menu()),
            enabled=True
        )  
        
        self.playerrep = Entity(
            model='cube',
            scale=(0.15, 0.15, 0.15),
            position=(0, 0.1, -0.3),
            rotation=(62.5, 0, 45),
            texture=player.texture,
            color=player.color,
            parent=self,
            shader=lit_with_shadows_shader,
            always_on_top = True,
            enabled=True
        )  
        
        add_wireframe_border(self.playerrep, color.dark_gray, 0.02)
        
        
        with open (f"{resource_path}/Assets/Datafiles/skindata.json", 'r') as f:
            data = json.load(f)
            
        namelist = []
        for key in data:
            #update a new list for all of the skins. If a skin has "0" in the second entry of it's value list, replace with the name 'locked'
            if data[key][1] == 0 or str(data[key][1]) == '0':
                # This is a locked skin
                namelist.append('Locked')
            else:
                # This is an unlocked skin
                namelist.append(key)
        # Create CustomisationButtons instance
        self.custbutt = CustomisationButtons(
            player, 
            position=(0, 0, -0.7), 
            scale=(0.05, 0.05), 
            parent=self,
            skindata = namelist
        )
        self.custbutt.enabled = True
        self.custbutt.generate_buttons()
        
    def updatethis(self, left, vel0, vel1):
        if left and self.enabled:
            rotation_speed = 10000
            self.playerrep.rotation_x += vel1 * Sensitive * rotation_speed * time.dt
            self.playerrep.rotation_z -= vel0 * Sensitive * rotation_speed * time.dt
        if not left:
            self.playerrep.rotation_z -= 10 * time.dt
    
    def updateplayerref(self, player):
        self.playerrep.texture = player.texture
        self.playerrep.color = player.color
        
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
        self.cleanup()
        self.main_menu.CUST = None
        self.main_menu.rendermenu()
        
    def cleanup(self):     
        if hasattr(self.playerrep, 'wireframe_border'):
            destroy(self.playerrep.wireframe_border)
            self.playerrep.wireframe_border = None
    
        self.enabled = False
        self.back_button.enabled = False
        self.playerrep.enabled = False

        if hasattr(self, 'custbutt') and self.custbutt:
            self.custbutt.removeall()
            destroy(self.custbutt)
            self.custbutt = None
        
    def destroy(self):
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
            model = 'Assets/Objects/ProgressBar.obj',
            scale=(0.09, 0.03, 0.03),
            position=(0, 0.45, 3),
            rotation=(90, 0, 0),
            parent=camera.ui,
            color=color.white,
            texture=None,
            enabled=True
        )
        self.loadingbar = Entity(
            model ='Cube',
            position = (0, 0.45, 0),
            rotation=(90, 0, 0),
            color=color.orange,
            parent=self.BarFrame,
            enabled=True
        )
        self.textpercent = Text(
            text="0.0",
            parent=camera.ui,
            position=(0.45, 0.46, 1),
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
    global velocity, currentztelpos, camera_locked, rot_locked, playlock, game_ready, accumulator, GameMap, main_menu, camera_loc, menu_music_playing, existing_gravswap, gravity

    if GameMap:
        GameMap.disable()
        destroy(GameMap)
        GameMap = None
    
    for gate in existing_gate:
        destroy(gate)
    existing_gate.clear()
    
    if existing_gravswap:
        for gate in existing_gravswap:
            destroy(gate)
        existing_gravswap = None
    
    #return gravity to normal if resetting while player is gravflipped
    if gravity == abs(gravity):
        gravity = -gravity
    
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
    player.visible = True
    
    # Reset camera
    camera.position = Vec3(-20, 20, -20)
    camera.rotation = Vec3(0, 45, 0)
    camera.look_at(player.position)
    camera_loc = player.position + Vec3(-20, 20, -20)
    
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
        menu_music_playing = False
        if menuback_music.playing:
            menuback_music.stop()
        menu_music_playing = True
        menuback_music.play()
        applyvolume(Volume=Volume)
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
            on_click=lambda: (buttonclick_sound.play(), self.disable(), reset_game_state(True))
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
            on_click=lambda: (buttonclick_sound.play(), self.disable())
        )
        self.options_button = Button(
            text = "Options",
            scale=(0.6, 0.1),
            position=(0, 0.11),
            parent=self,
            on_click=lambda: (buttonclick_sound.play(), self.hide(), self.optionpull())
        )
        self.mainmenubutton = Button(
            text="Main Menu",
            scale=(0.6, 0.1),
            position=(0, -0.11),
            parent=self,
            on_click=lambda: (buttonclick_sound.play(), reset_game_state(True))
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
        self.hide()
        if not hasattr(self, 'OptMen'):
            self.OptMen = Options(self, Volume)
        else:
            self.OptMen.backtothing = True
        self.OptMen.show()
    
    def removeopt(self):
        if hasattr(self, 'OptMen') and self.OptMen:
            destroy(self.OptMen)
            self.OptMen = None

    def show(self):
        global playlock, paused, death_sound
        self.enabled = True
        paused = True
        self.resume_button.enabled = True
        self.mainmenubutton.enabled = True
        self.exittodesktop_button.enabled = True
        self.options_button.enabled = True
        try:
            if death_sound.playing:
                death_sound.pause()
        except:
            #If death_sound fails to load
            pass
        
    def hide(self):
        global playlock, paused, death_sound
        self.enabled = False
        self.resume_button.enabled = False
        self.mainmenubutton.enabled = False
        self.exittodesktop_button.enabled = False
        self.options_button.enabled = False
        playlock = True
        paused = True
        if hasattr(death_sound, 'playing') and not death_sound.playing:
            death_sound.play()

    def disable(self):
        global playlock, paused
        self.enabled = False
        self.resume_button.enabled = False
        self.mainmenubutton.enabled = False
        self.exittodesktop_button.enabled = False
        self.options_button.enabled = False
        
        #Only unlock if player is actually enabled and visible
        if player.enabled and player.visible and not death_anim.playing:
            playlock = False
        paused = False

#Rather than a name, fill  the button with a cube of the texture/colour of the button's assigned skin
#This also means adding a lock icon to the ones without skins, though that would be the same as a grey colour + lock texture
#and a tooltip that shows the name of the skin (already implemented)
class CustomisationButtons(Entity):
    def __init__(self, player, position=(0, 0, 0), scale=(0.1, 0.1), parent=None, skindata=None):
        super().__init__(parent=parent)
        self.player = player
        self.position = position
        self.button_size = scale
        if skindata is None:
            skindata = []
        self.skindata = skindata
        self.totalskins = len(skindata)
        self.numofrow = 2
        self.numperrow = self.totalskins // self.numofrow
        self.button_spacing = (1/self.numperrow) - 0.04
        
        # Store all buttons in a 2D grid for easier access
        self.buttons = []
        self.allent = []
        
        # Create tooltip once
        self.tooltip = Tooltip(parent=camera.ui)
            
    def generate_buttons(self):
        # Clear existing buttons first
        self.removeall()
        
        # Load skin data for tooltips
        with open(f"{resource_path}/Assets/Datafiles/skindata.json", 'r') as f:
            self.skin_data = json.load(f)
        
        # Calculate rows and columns
        rows = min(self.numofrow, math.ceil(self.totalskins / self.numperrow))
        cols = min(self.numperrow, self.totalskins)
        
        # Generate all buttons in a grid layout
        button_index = 0
        for row in range(rows):
            button_row = []
            for col in range(cols):
                if button_index >= self.totalskins:
                    break
                    
                skin_name = self.skindata[button_index]
                
                # Calculate position based on grid
                button_position = (
                    (self.position[0] - 0.3) + self.button_spacing * col, 
                    self.position[1] - 0.1 - (0.1 * row), 
                    self.position[2]
                )
                
                button_container = Entity(
                    parent = self,
                    position = button_position,
                    scale = self.button_size,
                    model = 'quad',
                    color=color.dark_gray,
                    enabled = True,
                )
                
                skin_preview = Entity(
                    parent=button_container,
                    model='quad',
                    scale=(0.7, 0.7, 0.7),
                    position=(0, 0, -0.01),
                    rotation=(0, 0, 0),
                    enabled=True
                )
                
                if skin_name.lower() == 'locked':
                    skin_preview.color = color.gray
                    skin_preview.texture = None
                    lock_icon = Entity(
                        parent=button_container,
                        model='quad',
                        texture='Assets/Textures/LockIconImage.png',
                        scale=(0.75, 0.5),
                        position = (0, 0, -0.02),
                        enabled=True
                    )
                    self.allent.append(lock_icon)
                else:
                    try:
                        color_value = getattr(color, skin_name.lower(), None)
                        if color_value:
                            skin_preview.color= color_value
                            skin_preview.texture = None
                        else:
                            if os.path.exists(f"Assets/Textures/{skin_name}.jpg"):
                                skin_preview.color = color.white
                                skin_preview.texture = f"Assets/Textures/{skin_name}.jpg"
                            else:
                                skin_preview.color = None
                                skin_preview.texture = f"Assets/Textures/skinnotfound.png"
                    except:
                        skin_preview.color = color.white
                        skin_preview.texture = f"Assets/Textures/skinnotfound.png"
                        
                #wireframe preview border
                add_wireframe_border(skin_preview, color.black, 0.05)
                if hasattr(skin_preview, 'wireframe_border'):
                    self.allent.append(skin_preview.wireframe_border)
                
                #invisible button for click handling
                button = Button(
                    parent=button_container,
                    model='quad',
                    scale=(1, 1),
                    color=color.rgba(96, 96, 96, 0.7),
                    position = (0, 0, -0.005),
                    enabled=True,
                    on_click=lambda skin=skin_name: self.on_button_click(skin)
                )
                
                # Store button index and skin name for hover handling
                button.skin_name = skin_name
                button.button_position = button_position
                button.index = button_index
                
                # Set hover handlers
                button.on_mouse_enter = lambda button=button: self.on_hover(button)
                button.on_mouse_exit = self.tooltip.hide
                
                button_row.append(button)
                self.allent.append(button)
                self.allent.append(button_container)
                self.allent.append(skin_preview)
                button_index += 1
                
            self.buttons.append(button_row)
    
    def on_hover(self, button):
        """Handle hover event for any button"""
        skin = button.skin_name
        
        # Get description or use default if not available
        if skin == 'Locked':
            desc = "Unlock this skin first!"
        else:
            # Safely get description from skin data
            try:
                desc = self.skin_data.get(skin, ["", "", "No description"])[2]
            except (IndexError, KeyError):
                desc = f"Skin: {skin}"
        
        # Show tooltip with description
        if button.index < self.numperrow:
            self.tooltip.show(text=desc, position=(button.button_position[0] * 2, (float(button.button_position[1]))), scale_multiplier=1.2)
        else:
            self.tooltip.show(text=desc, position=(button.button_position[0] * 2, button.button_position[1] - 0.1), scale_multiplier=1.2)
    def on_button_click(self, skin):
        # Handle button click event
        buttonclick_sound.play()
        skinapply(skin)
        
        # Update the player representation in the customization menu
        if hasattr(self.parent, 'playerrep'):
            self.parent.playerrep.texture = self.player.texture
            self.parent.playerrep.color = self.player.color
    
    def removeall(self):
        for entity in self.allent:
            if entity and hasattr(entity, 'enabled'):
                try:
                    entity.enabled = False
                    destroy(entity)
                except Exception as e:
                    print(f"Error destroying entity: {e}")
        
        # Clear the lists
        self.buttons.clear()
        self.allent.clear()

    def destroy(self):
        self.removeall()
        if hasattr(self, 'tooltip') and self.tooltip:
            destroy(self.tooltip)
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
            on_click=lambda: (buttonclick_sound.play(), self.toggle_options())
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
                        on_click=lambda opt=option: (buttonclick_sound.play(), self.select_option(opt))
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

class Tooltip(Entity):
    def __init__(self, text='', parent=camera.ui, **kwargs):
        super().__init__(
            parent=parent,
            model='quad',
            scale=(0, 0),  # Start with zero scale
            color=color.black66,
            origin=(0, 0),
            z=-1,  # Make sure it appears in front of other UI elements
            **kwargs
        )
        
        # Create text entity as child
        self.text_entity = Text(
            parent=self,
            text=text,
            color=color.white,
            origin=(0, 0),
            position = (0, 0, -0.05),
            scale=(4, 15),
            font=f"{setUNIXpath(resource_path)}/Assets/Font/Poppins-Medium.ttf",
            enabled = True
        )
        
        # Set initial state
        self.target_scale = (0, 0)
        self.original_text = text
        self.background = None
        
    def show(self, text=None, position=None, scale_multiplier=1.0):
        """Show the tooltip with optional new text and position"""
        self.enabled = True
        if text:
            self.text_entity.text = text
        else:
            self.text_entity.text = self.original_text
            
        # Calculate background size based on text length
        text_width = len(self.text_entity.text) * 0.015 * scale_multiplier
        text_height = 0.05 * scale_multiplier
        self.target_scale = (text_width, text_height)
        
        if position:
            self.position = position
            
        self.text_entity.enabled = True
        
        #Animate in
        self.scale = (0, 0)  # Start small for animation
        self.animate_scale(self.target_scale, duration=0.1)
        
    def hide(self):
        self.enabled = False
        self.text_entity.enabled = False


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
    playing = False

    def __init__(self, frame_files, frame_time=0.03, **kwargs):
        global playerdeathstatus
        super().__init__(model=frame_files[0], **kwargs)
        self.frame_files = frame_files
        self.frame_time = frame_time
        self.current_frame = 0
        self.time_accum = 0
        self.playing = False
        self.finished_callback = None
        if playerdeathstatus == True:
            self.simple_mode = False
        else:
            self.simple_mode = True
        
        # Create wireframe overlay animation
        self.wireframe_overlay = Entity(
            model=frame_files[0],
            parent=self,
            position=(0, 0, 0),
            scale=(1.01, 1.01, 1.01),  # Slightly larger to avoid z-fighting
            wireframe=True,
            color=color.black,
            enabled=False
        )
        
        self.disable()

    def play(self, position, finished_callback=None):
        self.position = position
        self.finished_callback = finished_callback
        self.playing = True
        self.enable()
        self.current_frame = 0
        self.time_accum = 0
        
        if self.simple_mode:
            return
        # Full animation
        self.model = self.frame_files[0]
        self.wireframe_overlay.model = self.frame_files[0]
        self.wireframe_overlay.enable()
    
    def set_simple_mode(self, simple=True):
        self.simple_mode = simple
        if simple:
            self.wireframe_overlay.disable()

    def update(self):
        global player, paused
        if playerdeathstatus == True:
            self.simple_mode = False
        else:
            self.simple_mode = True
        if not hasattr(self, 'playing') or not self.playing:
            return
        if paused:
            return
        if self.simple_mode:
            self.wireframe_overlay.disable()
            self.time_accum += time.dt
            if self.time_accum >= self.frame_time * (4/3):
                self.time_accum = 0
                self.current_frame += 1
                self.model = 'cube'
                self.scale = (1, 1, 1)
                self.texture = player.texture
                self.color = player.color
                if self.current_frame < 40:
                    x = self.current_frame
                    #function for a custom in-out animation using 1/|f(x)| principle on a quadratic function
                    #full equation is 15(11/((3*|(-5*((((x/2)-10)**2) - 2)/9) - 10|) + 1))
                    fx = (-5 * (((x/2) - 4)**2))-2
                    f2x = 3 * abs((fx/9)-10)
                    f3x = 50 * (11/f2x + 1)
                    scale_factor = f3x - 59.5
                    if scale_factor <= 0:
                        scale_factor = 0.01
                    self.scale = Vec3(scale_factor, scale_factor, scale_factor)
                    
                else:
                    self.playing = False
                    self.disable()
                    self.scale = Vec3(1, 1, 1)
                    self.color = player.color
                    if self.finished_callback:
                        self.finished_callback()
        else:
            self.time_accum += time.dt
            if self.time_accum >= self.frame_time:
                self.time_accum = 0
                self.current_frame += 1
                if self.current_frame < len(self.frame_files):
                    # Update both the main animation and wireframe overlay
                    self.model = self.frame_files[self.current_frame]
                    self.wireframe_overlay.model = self.frame_files[self.current_frame]
                else:
                    self.playing = False
                    self.disable()
                    self.wireframe_overlay.disable()
                    if self.finished_callback:
                        self.finished_callback()

class AnimatedBackground(Entity):
    def __init__(self, intro_frames, loop_frames, frame_time=0.033, **kwargs):
        super().__init__(
            model='quad',
            scale=(1.78, 1),  # Same as main menu background
            color=color.white,  # Keep white so texture shows properly
            parent=camera.ui,
            z=1,  # Behind other UI elements
            shader=None,
            **kwargs
        )
        
        self.intro_frames = intro_frames
        self.loop_frames = loop_frames
        self.current_frames = intro_frames
        self.frame_time = frame_time
        self.current_frame = 0
        self.time_accum = 0
        self.playing = False
        self.is_intro = True

        # Start with first frame
        if intro_frames:
            self.texture = intro_frames[0]

    def play(self):
        self.current_frame = 0
        self.time_accum = 0
        self.playing = True
        self.enabled = True
        self.is_intro = True
        self.current_frames = self.intro_frames
        if self.intro_frames:
            self.texture = self.intro_frames[0]

    def stop(self):
        self.playing = False
        self.enabled = False

    def update(self):
        if not self.playing or not self.enabled:
            return
            
        self.time_accum += time.dt
        if self.time_accum >= self.frame_time:
            self.time_accum = 0
            self.current_frame += 1
            
            # Check if we've finished the current sequence
            if self.current_frame >= len(self.current_frames):
                if self.is_intro:
                    # Switch to loop frames
                    self.is_intro = False
                    self.current_frames = self.loop_frames
                    self.current_frame = 0
                else:
                    # Loop the loop frames
                    self.current_frame = 0
            
            # Update texture
            if self.current_frame < len(self.current_frames):
                self.texture = self.current_frames[self.current_frame]


def respawn_player():
    global velocity, currentztelpos, camera_locked, rot_locked, playlock, paused, camera_loc, gravity, return_rotation, paused
    
    if paused:
        return
    
    # Reset player position and physics
    player.position = Vec3(0, 30, 0)
    velocity = 0
    player.z = zTelPos[2][2]
    currentztelpos = 2
    
    # Reset gravity to normal if it's flipped
    if gravity == abs(gravity):  # If gravity is positive (flipped)
        gravity = -gravity
    
    # Force stop playing sounds
    if warp_sound.playing:
        warp_sound.stop()

    # Proper camera reset based on gravity state
    if gravity != abs(gravity):  # Normal gravity
        camera.position = Vec3(-20, 20, -20)
        camera.rotation = Vec3(0, 45, 0)
        camera_loc = player.position + Vec3(-20, 20, -20)
        return_rotation = Vec3(0, 45, 0)
    else:  # Flipped gravity
        camera.position = Vec3(-20, -20, -20)
        camera.rotation = Vec3(180, 45, 0)
        camera_loc = player.position + Vec3(-20, -20, -20)
        return_rotation = Vec3(180, 45, 0)
    
    # Force camera to look at player
    camera.look_at(player.position)

    # FIXED: Proper sequencing of player re-enabling
    # First make player visible
    player.visible = True
    
    # Then enable player (but only if not paused)
    if not paused:
        player.enable()
        
    # Unlock camera and movement
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
    global camera_locked, rot_locked, playlock, camera_loc, return_rotation
    
    # Don't run respawn animation if camera is already being reset
    if camera_locked and rot_locked:
        return
        
    camera_locked = True
    rot_locked = True
    playlock = True
    
    # Calculate target position based on current gravity
    if gravity != abs(gravity):
        target_camera_pos = player.position + Vec3(-20, 20, -20)
        return_rotation = Vec3(0, 45, 0)
    else:
        target_camera_pos = player.position + Vec3(-20, -20, -20)
        return_rotation = Vec3(180, 45, 0)
    
    # FIXED: Use smooth interpolation with bounds checking
    current_distance = distance(camera.position, target_camera_pos)
    rotation_distance = distance(camera.rotation, return_rotation)
    
    if current_distance > 0.1:
        camera_loc = lerp(camera.position, target_camera_pos, time.dt * return_speed)
        camera.position = camera_loc
    
    if rotation_distance > 0.5:
        camera.rotation = lerp(camera.rotation, return_rotation, time.dt * return_speed)
    
    # Check if animation is complete
    if current_distance < 0.1 and rotation_distance < 0.5:
        # Force final position and unlock
        camera.position = target_camera_pos
        camera.rotation = return_rotation
        camera.look_at(player.position)
        camera_locked = False
        rot_locked = False
        playlock = False

def input(key):
    global currentztelpos, rot_locked, camera_locked, playlock, buttoncontrols, playerdeathstatus
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
                # Save progress before reset
                savehigh(current_mapcount, levelprog.percentagecompletion)
                
                # Disable and hide player
                player.disable()
                player.visible = False
                
                try:
                    if not death_sound.playing:
                        death_sound.play()
                except:
                    pass
                
                # Lock controls and start death animation
                camera_locked = True
                rot_locked = True
                playlock = True
                death_anim.play(player.position, finished_callback=respawn_player)
            else:
                pass  # Ignore input if death animation is playing
            
        if key == buttoncontrols[1]:
            # position shifts one lane further away from the camera
            # if at the furthest possible lane, instead stay in the same place
            if currentztelpos == 4:
                # Create a semi-transparent red tint
                tint = Tint(opacity=0.2)
                camera.shake(duration=0.5)
                invoke(tint.disable, delay=0.5)  # Disable the tint after the shake duration
            else:
                currentztelpos += 1
            #play teleport sfx
            if not warp_sound.playing:
                warp_sound.play()
        if key == buttoncontrols[0]:
            # position shifts one lane closer to camera
            # if at the closest possible lane, instead stay in the same place
            if currentztelpos == 0:
                # Create a semi-transparent red tint
                tint = Tint(opacity=0.2)
                camera.shake(duration=0.5)
                invoke(tint.disable, delay=0.5)  # Disable the tint after the shake duration
            else:
                currentztelpos -= 1
            #play teleport sfx
            if not warp_sound.playing:
                warp_sound.play()
        player.z = zTelPos[currentztelpos][2]

    

# Create and keep a reference for loadingscreen and levelprogress
loading_screen = LoadingScreen()  
levelprog = LevelProgress()

# set a function to all variables
# apply it to a thread and call the loading screen while it's running
#upon finish, invoke finish_loading to hide the loading screen and set game_ready to True

def prerendering():
    global death_anim, loading_screen, startmen_frames, mainmenuloop_frames
    loading_screen.enable()

    # Add progress tracking
    total_items = len(death_anim_frames) + len(startmen_frames) + len(mainmenuloop_frames) + 2
    current_item = [0]  # Use list to allow modification in nested functions
    original_pos = Vec3(0.5, -0.3, 0)

    #loading screen ui features
    # Create progress UI
    progress_bar = Entity(
        model='cube',
        scale=(0, 0.02, 0.01),
        position=(0, -0.3, -0.1),
        color=color.white,
        parent=loading_screen
    )
    progress_bg = Entity(
        model='cube',
        scale=(0.05, 0.05, 0.05),
        position=(0, -0.3, 0),
        rotation=(45, 0, 45),
        color=player.color,
        texture=player.texture,
        parent=loading_screen
    )

    add_wireframe_border(progress_bg, color.black, 0.02)

    progress_text = Text(
        "Loading... 0%",
        parent=loading_screen,
        position=(0, -0.4, -0.1),
        origin=(0, 0),
        scale=1.5
    )

    def update_progress():
        try:
            current_item[0] += 1
            progress = current_item[0] / total_items
            progress_bar.scale_x = 0.8 * progress
            progress_bar.x = -0.4 + (0.4 * progress)
            progress_text.text = f"Loading... {int(progress * 100)} percent"
        except:
            print("Error in preloading for update progress")
            pass

    # Add spinning jump animation to the cube because I felt silly
    # Add jumping and spinning animation
    def jump_and_spin():
        if progress_bg.enabled:
            # Jump up while spinning
            progress_bg.animate_position(
                Vec3(0.5, -0.15, 0),  # Jump up (keep same x, change y)
                duration=0.5,
                curve=curve.out_quad
            )
            progress_bg.animate_rotation(
                progress_bg.rotation + Vec3(0, 0, 360),  # Full spin
                duration=1.0
            )
            
            # Fall back down after reaching peak
            invoke(lambda: progress_bg.animate_position(
                original_pos,  # Fall back to original position
                duration=0.5,
                curve=curve.in_quad
            ) if progress_bg.enabled else None, delay=0.5)
            
            # Schedule next jump after complete cycle
            invoke(jump_and_spin, delay=1.2)
    
    jump_and_spin()

    # --- PRELOAD all animation frames to avoid first-run lag ---
    for frame in death_anim_frames:
        update_progress()
        e = Entity(model=frame, enabled=True)

        invoke(e.disable, delay=0.1)  # Let it render for one frame, then disable
        
    #Force Load Audio
    load_audio()
    applyvolume(Volume=Volume)

    death_anim = BakedMeshAnimation(death_anim_frames, scale=(1,1,1), texture=player.texture, color=player.color, shader=lit_with_shadows_shader)
    death_anim.disable()

    for frame in startmen_frames:
        update_progress()
        e = Entity(model='quad', enabled=True, texture=frame)
        invoke(e.disable, delay=0.1)  # Let it render for one frame, then disable
    
    for frame in mainmenuloop_frames:
        update_progress()
        e = Entity(model='quad', enabled=True, texture=frame)
        invoke(e.disable, delay=0.1)  # Let it render for one frame, then disable

    # After all loading is done, schedule finish_loading
    invoke(finish_loading, delay=0.1)
    
def returnheldkeys():
    inputkey = []
    inputkey = [k for k in held_keys.keys()]
    try:
        inputkey.remove("shift")
    except:
        pass
    try:
        inputkey.remove("left mouse")
    except:
        pass
    try:
        held_keys.clear()
        return inputkey[-1]
    except:
        held_keys.clear()
        return None

def finish_loading():
    global main_menu, loading_screen
    #trigger skin update on finish loading
    load_playerskins()
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
        main_menu.CUST.updateplayerref(player)
    
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
    global velocity, is_grounded, currentztelpos, camera_loc, camera_locked, rot_locked, Sensitive, playlock, menu_music_playing, buttoncontrols, gravswapping, existing_gravswap, playerdeathstatus

    if not playlock:

        #disable music if playing
        if game_ready:
            if menu_music_playing:
                menuback_music.fade_out(duration=0.5)
                menu_music_playing = False

        # --- All movement and physics logic goes here ---
        player.x += move_x * dt

        # Jumping
        if is_grounded and held_keys[buttoncontrols[2]]:
            if gravity != abs(gravity):
                velocity = 15  # Jump velocity
            else:
                velocity -= 15

        # Apply gravity
        velocity += gravity * dt
        player.y += velocity * dt

        is_grounded = False

        update_player_marker()

        # --- Improved boxcast for highest ground point; this is the under-player cast---
        if gravity != abs(gravity):
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
            boxcast_distance = 0.3
            boxcast_origin = player.position + Vec3(0, 0.3, 0)
            hit_info = boxcast(
                origin=boxcast_origin,
                direction=Vec3(0, 1, 0),
                distance=boxcast_distance,
                thickness=(player.scale_x, player.scale_z),
                ignore=(player,),
                debug=False
            )

            if hit_info.hit:
                is_grounded = True
                player.y = hit_info.world_point.y - player.scale_y / 2 - 0.01
                velocity = 0
                
            # --- Secondary box cast for collision correction - orients player during clipping to avoid instakill ---
            castdist = 0.3
            castorig = player.position + Vec3(0, 0, 0)
            hit_info = boxcast(
                origin=castorig,
                direction=Vec3(0, 1, 0),
                distance=castdist,
                thickness=(player.scale_x, player.scale_z),
                ignore=(player,),
                debug=True
            )

            if hit_info.hit:
                is_grounded = True
                player.y -= 0.3
                velocity = 0
            
    else:
        
        # When immobilized, prevent all movement and physics
        velocity = 0
        is_grounded = False
        menuback_music.play()

    # --- Boxcast for wall collision (instakill) ---
    # (This can remain outside, so death still triggers when immobilized)
    if gravity != abs(gravity):
        deathboxcast_d = 0.5
        hit_info_death = boxcast(
            origin=player.position + Vec3(0, 0.5, 0),
            direction=Vec3(1, 0, 0),
            distance=deathboxcast_d,
            thickness=(player.scale_x / 2, player.scale_y / 2),
            ignore=(player,),
            debug=False
        )
    else:
        deathboxcast_d = 0.5
        hit_info_death = boxcast(
            origin=player.position + Vec3(0, -0.5, 0),
            direction=Vec3(1, 0, 0),
            distance=deathboxcast_d,
            thickness=(player.scale_x / 2, player.scale_y/2),
            ignore=(player,),
            debug=False
        )
        
    if not gravswapping:
        if hit_info_death.hit and not death_anim.playing:
            if hasattr(hit_info_death.entity, 'tag'):
                if hit_info_death.entity.tag == 'gravswap_gate' and not hit_info_death.entity.cooldown:
                    hit_info_death.entity.start_cooldown()
                    gravswapping = True
                    gravswapper()
                    return
                elif hit_info_death.entity.tag == 'endgate':
                    if not levelcomp_sound.playing:
                        levelcomp_sound.play()
                    levelprog.percentagecompletion = "100.0"
                    reset_game_state(False)
                    respawn_player()
                    player.disable()
                    WinScreen().enable()
                    savehigh(current_mapcount, "100.0")
                    unlock_skins()
                    return
                    
            # Save highscore
            savehigh(current_mapcount, levelprog.percentagecompletion)

            player.disable()
            # Set camera lock only when starting death animation
            camera_locked = True
            rot_locked = True
            playlock = True
            try:
                if not death_sound.playing:
                    death_sound.play()
            except:
                pass
            
            
            death_anim.play(player.position, finished_callback=respawn_player)
            
    #player OOB check for levels. This would need to be changed if I add lowered levels but for now it will suffice.
    # Replace the OOB check section with:
    if (player.y < 0 or player.y > 100) and not death_anim.playing:
        
        # Save highscore before respawn
        savehigh(current_mapcount, levelprog.percentagecompletion)
        
        # Disable and hide player
        player.disable()
        player.visible = False
        
        # Move player to safe position for death animation
        player.position = Vec3(0, 30, 0)
        
        # Lock controls
        camera_locked = True
        rot_locked = True
        playlock = True
        
        try:
            if not death_sound.playing:
                death_sound.play()
        except:
            pass
        
        death_anim.play(player.position, finished_callback=respawn_player)

    #Map Integrity Verification
    if GameMap.collider:
        pass
    else:
        print("Game MAP collider is not set. Please check the collider settings.")
        
    # Camera movement logic (mouse controls)
    #camera return location
    if gravity != abs(gravity):
        return_location = player.position + Vec3(-20, 20, -20)
    else:
        return_location = player.position + Vec3(-20, -20, -20)
    
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
