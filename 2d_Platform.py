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
player = Entity(model='cube', color=color.orange, scale=(1, 1, 1), collider='box', position=(0, 30, 0))

        
safeGround = Entity(model='MAP.obj', collider='mesh')
safeGround.position = (45, -0.5, 0)
safeGround.show_colliders = True
safeGround.scale = (2, 1, 1)
safeGround.rotation = (0, 270, 0)
vertex_grid = []
grid_size = 2
vertices = safeGround.model.vertices
for vertex in vertices:
    vertex_world_pos = math.floor(safeGround.world_position + Vec3(*vertex) * safeGround.scale)
    grid_x = int(vertex_world_pos.x // grid_size) * 2
    grid_z = int(vertex_world_pos.z // grid_size)
    grid_y = int(vertex_world_pos.y // grid_size)
    coordinate = Vec3(grid_x, grid_y, grid_z)
    listcoordinate = (grid_x, grid_y, grid_z)
    if listcoordinate not in vertex_grid:
        vertex_grid.append(coordinate)

print(vertex_grid)

""" for vertex in vertices:
    vertex_world_pos = math.floor((safeGround.world_position + Vec3(*vertex) * safeGround.scale))
    grid_x = math.floor(int(vertex_world_pos.x // grid_size))
    grid_z = math.floor(int(vertex_world_pos.z // grid_size))
    if (grid_x, grid_z) not in vertex_grid:
        vertex_grid[(grid_x, grid_z)] = []
    vertex_grid[(grid_x, grid_z)].append(math.floor(vertex_world_pos))
    
print(vertex_grid) """


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
    global velocity, is_grounded, return_speed, return_rotation, camera_loc, movementkeyz, camfollowspd, move_x
    return_location = player.position + Vec3(-20, 20, -20)

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
    
    #really shit collision function BUT 
    #it is proof that collision works
    #collision is defined by the player model and needs to be set up in the update function
    #need to consider the x and z axis coordinates of a given point and 
    #set the player to the highest mesh point that corresponds to those coordinates
    #find highest point of the mesh at the player x and z coordinates
    #set player position to the highest point +0.1 in order to keep the player above the collision
    
    # SafeGround collision with multi-layer support
    if safeGround.collider:
        hit_info = player.intersects(safeGround)
        if hit_info.hit:
            player_grid_x = round(int(player.x // grid_size))
            player_grid_z = round(int(player.z // grid_size))
            player_grid_y = round(int(player.y))
            playercell = [player_grid_x, player_grid_y, player_grid_z]
            valid_heights = []
            for dx in range (-2, 2):
                for dz in range(-2, 2):
                    cell = Vec3((3*(playercell[0] + dx)), (playercell[1] - 1), ((5)*(playercell[2] + dz)))
                    print(cell)
                    for i in range(len(vertex_grid)):
                        if cell == vertex_grid[i]:
                            valid_heights.append(vertex_world_pos.y + 0.1)
            
            print(valid_heights)
            
            #parse valid heights to player.y
            mean = math.floor(sum(valid_heights) / len(valid_heights))
            player.y = mean - 1

            
            
        """ for dx in range(-2, 2):
                for dz in range(-2, 2):
                    cell = Vec3((3*(player_grid_x + dx)), (player.y - 1), ((5)*(player_grid_z + dz)))
                    print(cell)
                    #10/05 Vertex grid fills but this if statement does not fulfil
                    #This is possibly due to an invalid comparison of a tuple to a dictionary
                    #9:00 am 12/05 Also could be due to the invalid settings of cell vs vertex, as cell's tracking of the x coordinate seems off by a factor of 4
                    #3:09 pm 12/05 potentially need to simplify to just compare cell to vert grid as they return similar variables, then clamp?? not sure
                    if cell in vertex_grid:
                        for vertex_world_pos in vertex_grid[cell]:
                            if abs(vertex_world_pos.x - player.x) > 2 and abs(vertex_world_pos.z - player.z) > 2:
                                valid_heights.append(vertex_world_pos.y + 0.1)
                    else:
                        pass
                        #print("I don't feel like it today")
            print(valid_heights) """

            # Find all valid heights at the player's x and z coordinates
            #This section is the main point of error -  according to tests, it is able to find the vertices but
            #Can't seem to get anything actually into the append statement for the valid heights.
            #Possibly needs optimisations for vertex locating (e.g. approximate player position based rather than all)
    
            
            
            
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



#FAILED COLLISION MECHANICS #3
#I have trapped it in the timeout corner
""" 
# Access the mesh vertices
            vertices = safeGround.model.vertices
            valid_heights = []
            for vertex in vertices:
                vertex_world_pos = safeGround.world_position + Vec3(*vertex) * safeGround.scale
                if abs(vertex_world_pos.x - player.x) < 2 and abs(vertex_world_pos.z - player.z) < 2:
                    valid_heights.append(vertex_world_pos.y + 0.6)
                #print(f"Vertex world position: {vertex_world_pos}")

            # Sort heights in ascending order
            valid_heights.sort()
            print(f"Valid heights: {valid_heights}")

            # Determine the correct height based on the player's current position and movement
            target_height = None
            for height in valid_heights:
                if player.y >= height - 0.5:  # Player is above or near this layer
                    target_height = height
                else:
                    break

            # If no valid height is found, use the first height in the list
            if target_height is None and valid_heights:
                target_height = valid_heights[0]

            print(f"Target height: {target_height}")

            # Adjust player position if a valid height is found
            if target_height is not None:
                player.y = max(player.y, target_height + 0.1)  # Ensure the player stays above the mesh
                velocity = 0
                is_grounded = True """