import numpy as np
import random
import arcade
import time

class Game(arcade.Window):

    def __init__(self, grid_size, num_agents, goal_state):
        # Adjust window size to match the tilemap size
        self.tilemapname = "Maze_Tilemap.tmx"
        self.tile_map = arcade.load_tilemap(self.tilemapname, scaling=1.0)
        map_width = self.tile_map.width * self.tile_map.tile_width
        map_height = self.tile_map.height * self.tile_map.tile_height
        super().__init__(map_width, map_height, "Q-Learning Path Finding")
        self.grid_size = grid_size
        self.cell_size = self.tile_map.tile_width  # Use tile width for cell size
        self.n_states = self.grid_size * self.grid_size
        self.n_actions = 4
        self.num_agents = num_agents
        self.Q_tables = [np.random.uniform(low=-1, high=1, size=(self.n_states, self.n_actions)) for _ in range(num_agents)]  # Initialize Q-tables with small random values
        self.learning_rate = 0.8
        self.discount_factor = 0.95
        self.exploration_prob = 0.5  # Increase Exploration Probability
        self.last_actions = [-1] * num_agents  # Track last actions to prevent immediate reversal
        self.actions = {
            0: -self.grid_size,  # Up
            1: self.grid_size,  # Down
            2: -1,  # Left
            3: 1  # Right
        }
        self.iterations = [0] * num_agents
        self.colors = [arcade.color.BLUE, arcade.color.GRAY, arcade.color.RED, arcade.color.YELLOW, arcade.color.ORANGE]  # Add more colors if needed
        self.darker_colors = [arcade.color.DARK_BLUE, arcade.color.DARK_GRAY, arcade.color.DARK_RED, arcade.color.DARK_YELLOW, arcade.color.DARK_ORANGE]  # Add corresponding darker colors
        self.goal_reached = [False] * num_agents
        self.start_time = time.time()
        self.goal_state = goal_state
        self.max_time = 20  # Maximum time allowed to reach the goal
        self.walls = set()  # Initialize walls as an empty set
        self.scene = None  # Initialize scene
        self.initial_positions = []
        self.current_states = []
        self.paths = []
        self.visited_states = [set() for _ in range(num_agents)]  # Track visited states for each agent

    def setup(self):
        arcade.set_background_color(arcade.color.BLACK)
        map_name = self.tilemapname  # Ensure this file exists in the correct path
        layer_options = {"Walls": {"use_spatial_hash": True}}

        # Adjust the scaling factor if necessary
        self.tile_map = arcade.load_tilemap(map_name, scaling=1.0, layer_options=layer_options)
        self.scene = arcade.Scene.from_tilemap(self.tile_map)

        # Extract wall positions
        for wall in self.scene["Walls"]:
            row, col = int(wall.center_y // self.cell_size), int(wall.center_x // self.cell_size)
            self.walls.add(row * self.grid_size + col)

        # Ensure agents and goal do not spawn inside walls
        self.initial_positions = self.get_valid_positions(self.num_agents)
        self.current_states = self.initial_positions.copy()
        self.paths = [[pos] for pos in self.initial_positions]
        self.goal_state = self.get_valid_positions(1)[0]

        print(f"Walls: {self.walls}")
        print(f"Initial positions: {self.initial_positions}")
        print(f"Goal state: {self.goal_state}")

    def get_valid_positions(self, count):
        def is_surrounded_by_walls(pos):
            row, col = divmod(pos, self.grid_size)
            adjacent_positions = [
                (row - 1) * self.grid_size + col,  # Up
                (row + 1) * self.grid_size + col,  # Down
                row * self.grid_size + (col - 1),  # Left
                row * self.grid_size + (col + 1)   # Right
            ]
            return all(adj_pos in self.walls for adj_pos in adjacent_positions)

        valid_positions = []
        while len(valid_positions) < count:
            pos = random.randint(0, (self.grid_size * self.grid_size) - 1)
            if pos not in self.walls and pos not in valid_positions and not is_surrounded_by_walls(pos):
                valid_positions.append(pos)
        return valid_positions

    def reset_agents(self):
        self.current_states = self.initial_positions.copy()
        self.paths = [[pos] for pos in self.initial_positions]
        self.iterations = [0] * self.num_agents
        self.goal_reached = [False] * self.num_agents
        self.start_time = time.time()
        self.visited_states = [set() for _ in range(self.num_agents)]  # Reset visited states

    def on_draw(self):
        arcade.start_render()
        if self.scene:
            self.scene.draw()  # Draw the tilemap and walls

        end_row, end_col = divmod(self.goal_state, self.grid_size)
        arcade.draw_rectangle_filled(end_col * self.cell_size + self.cell_size // 2, 
                                     self.height - end_row * self.cell_size - self.cell_size // 2, 
                                     self.cell_size, self.cell_size, arcade.color.GREEN)
        for agent_id in range(self.num_agents):
            for state in self.paths[agent_id]:
                row, col = divmod(state, self.grid_size)
                arcade.draw_rectangle_filled(col * self.cell_size + self.cell_size // 2, 
                                             self.height - row * self.cell_size - self.cell_size // 2, 
                                             self.cell_size, self.cell_size, self.colors[agent_id])
        
        for agent_id in range(self.num_agents):
            current_state = self.paths[agent_id][-1]
            current_row, current_col = divmod(current_state, self.grid_size)
            arcade.draw_rectangle_filled(current_col * self.cell_size + self.cell_size // 2, 
                                         self.height - current_row * self.cell_size - self.cell_size // 2, 
                                         self.cell_size, self.cell_size, self.darker_colors[agent_id])

    def take_action(self, agent_id, action):
        next_state = self.current_states[agent_id] + self.actions[action]
        if next_state in self.walls or next_state < 0 or next_state >= self.n_states:
            print(f"Agent {agent_id} attempted to move into an invalid state: {next_state}")
            return self.current_states[agent_id], -1  # Invalid move, return current state and negative reward
        if next_state in self.visited_states[agent_id]:
            return next_state, -0.5  # Punishment for revisiting a state
        return next_state, 1 if next_state == self.goal_state else -0.01  # Small negative reward for each move

    def update_q_table(self, agent_id, state, action, reward, next_state):
        best_next_action = np.argmax(self.Q_tables[agent_id][next_state])
        td_target = reward + self.discount_factor * self.Q_tables[agent_id][next_state, best_next_action]
        td_error = td_target - self.Q_tables[agent_id][state, action]
        self.Q_tables[agent_id][state, action] += self.learning_rate * td_error

    def choose_action(self, agent_id):
        if np.random.rand() < self.exploration_prob:
            return np.random.randint(0, self.n_actions)  # Explore
        return np.argmax(self.Q_tables[agent_id][self.current_states[agent_id]])  # Exploit

    def on_update(self, delta_time):
        elapsed_time = time.time() - self.start_time
        if elapsed_time > self.max_time:
            self.reset_agents()
            return

        for agent_id in range(self.num_agents):
            if not self.goal_reached[agent_id]:
                if self.current_states[agent_id] != self.goal_state:
                    action = self.choose_action(agent_id)
                    next_state, reward = self.take_action(agent_id, action)
                    self.update_q_table(agent_id, self.current_states[agent_id], action, reward, next_state)

                    if next_state != self.current_states[agent_id]:
                        self.current_states[agent_id] = next_state
                        self.paths[agent_id].append(next_state)
                        self.visited_states[agent_id].add(next_state)  # Mark state as visited
                        self.last_actions[agent_id] = action  # Update last action
                        self.iterations[agent_id] += 1

                    if next_state == self.goal_state:
                        self.goal_reached[agent_id] = True
                        print(f"Agent {agent_id} reached the goal state.")
                else:
                    self.goal_reached[agent_id] = True
            
            if all(self.goal_reached):
                self.reset_agents()

        # Gradually decrease exploration probability
        self.exploration_prob = max(0.1, self.exploration_prob * 0.99)

def main():
    grid_size = 20
    game = Game(grid_size=grid_size, num_agents=1, goal_state=random.randint(0, (grid_size * grid_size) - 1))
    game.setup()  # Call setup to initialize the tilemap and scene
    arcade.run()

if __name__ == "__main__":
    main()