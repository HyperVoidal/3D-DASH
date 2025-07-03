import numpy as np
import random
import matplotlib.pyplot as plt
import os
import arcade
#rather than outputting a variety of images, try to use arcade to output movements.

# Define the environment
grid_size = 6  # Size of the grid world
n_states = grid_size * grid_size  # Number of states in the grid world
n_actions = 4  # Number of possible actions (up, down, left, right)

# Initialize Q-table with zeros
Q_table = np.zeros((n_states, n_actions))

# Define parameters
learning_rate = 0.8
discount_factor = 0.95
exploration_prob = 0.2
epochs = 1000

actions = {
    0: -grid_size,  # Up
    1: grid_size,  # Down
    2: -1,  # Left
    3: 1  # Right
}

# Create the directory if it doesn't exist
os.makedirs("Progression_paths", exist_ok=True)

def save_path(epoch, path, goal_state, iteration=None):
    grid = np.zeros((grid_size, grid_size))
    for state in path:
        row, col = divmod(state, grid_size)
        grid[row, col] = 1

    # Mark the starting point in green and the ending point in red
    start_row, start_col = divmod(path[0], grid_size)
    end_row, end_col = divmod(goal_state, grid_size)
    grid[start_row, start_col] = 0.5  # Green
    grid[end_row, end_col] = 0.75  # Red

    plt.figure(figsize=(6, 6))
    plt.imshow(grid, cmap='Blues', interpolation='nearest')
    plt.scatter(start_col, start_row, color='green', s=100, label='Start')
    plt.scatter(end_col, end_row, color='red', s=100, label='End')
    plt.title(f'Path taken by Q-learning at epoch {epoch}')
    plt.xlabel('Columns')
    plt.ylabel('Rows')
    plt.xticks(np.arange(grid_size))
    plt.yticks(np.arange(grid_size))
    plt.grid(True)
    plt.legend()
    if iteration is not None:
        plt.savefig(f'Progression_paths/Q_learning_path_epoch_{epoch}_iter_{epoch}.png')  # Save the path visualization as a PNG file
    else:
        plt.savefig(f'Progression_paths/Q_learning_path_epoch_{epoch}.png')  # Save the path visualization as a PNG file
    plt.close()

# Q-learning algorithm
goal_state = random.randint(0, n_states - 1)  # Randomly select the goal state
print(f"Goal state: {goal_state}")
for epoch in range(epochs):
    current_state = 0
    print(f"Epoch {epoch} started")

    iteration = 0
    while current_state != goal_state:
        print(f"Current state: {current_state}")
        # Choose action with epsilon-greedy strategy
        if np.random.rand() < exploration_prob:
            action = np.random.randint(0, n_actions)  # Explore
        else:
            action = np.argmax(Q_table[current_state])  # Exploit
        print(f"Action chosen: {action}")

        # Simulate the environment (move to the next state)
        next_state = current_state + actions[action]
        print(f"Next state before boundary check: {next_state}")

        # Ensure the next state is within grid boundaries
        row, col = divmod(current_state, grid_size)
        if action == 0 and row == 0:  # Up
            next_state = current_state
        elif action == 1 and row == grid_size - 1:  # Down
            next_state = current_state
        elif action == 2 and col == 0:  # Left
            next_state = current_state
        elif action == 3 and col == grid_size - 1:  # Right
            next_state = current_state
        print(f"Next state after boundary check: {next_state}")

        # Define a simple reward function (1 if the goal state is reached, 0 otherwise)
        reward = 1 if next_state == goal_state else 0
        print(f"Reward: {reward}")

        # Update Q-value using the Q-learning update rule
        Q_table[current_state, action] += learning_rate * \
            (reward + discount_factor *
             np.max(Q_table[next_state]) - Q_table[current_state, action])
        print(f"Updated Q-table at state {current_state}, action {action}: {Q_table[current_state, action]}")

        current_state = next_state  # Move to the next state
        print(f"Moved to next state: {current_state}")

        # Save the path visualization for the first 100 iterations
        if iteration < 100:
            path = [current_state]
            save_path(epoch, path, goal_state, iteration)
        iteration += 1

    print(f"Epoch {epoch} ended")

    # Print Q-table at certain intervals for debugging
    if epoch % 100 == 0:
        print(f"Q-table at epoch {epoch}:")
        print(np.round(Q_table, 2))

        # Simulate a run using the learned Q-table and record the path
        current_state = 0  # Start from the initial state
        path = [current_state]

        while current_state != goal_state:
            action = np.argmax(Q_table[current_state])  # Choose the best action
            next_state = current_state + actions[action]

            # Ensure the next state is within grid boundaries
            row, col = divmod(current_state, grid_size)
            if action == 0 and row == 0:  # Up
                next_state = current_state
            elif action == 1 and row == grid_size - 1:  # Down
                next_state = current_state
            elif action == 2 and col == 0:  # Left
                next_state = current_state
            elif action == 3 and col == grid_size - 1:  # Right
                next_state = current_state

            path.append(next_state)
            current_state = next_state

        # Save the path visualization
        save_path(epoch, path, goal_state)

# After training, the Q-table represents the learned Q-values
print("Learned Q-table:")
print(np.round(Q_table, 2))

# Simulate a run using the learned Q-table and record the path
current_state = 0  # Start from the initial state
path = [current_state]

while current_state != goal_state:
    action = np.argmax(Q_table[current_state])  # Choose the best action
    next_state = current_state + actions[action]

    # Ensure the next state is within grid boundaries
    row, col = divmod(current_state, grid_size)
    if action == 0 and row == 0:  # Up
        next_state = current_state
    elif action == 1 and row == grid_size - 1:  # Down
        next_state = current_state
    elif action == 2 and col == 0:  # Left
        next_state = current_state
    elif action == 3 and col == grid_size - 1:  # Right
        next_state = current_state

    path.append(next_state)
    current_state = next_state

# Visualize the path on the grid
grid = np.zeros((grid_size, grid_size))
for state in path:
    row, col = divmod(state, grid_size)
    grid[row, col] = 1

# Mark the starting point in green and the ending point in red
start_row, start_col = divmod(path[0], grid_size)
end_row, end_col = divmod(path[-1], grid_size)
grid[start_row, start_col] = 0.5  # Green
grid[end_row, end_col] = 0.75  # Red

plt.figure(figsize=(6, 6))
plt.imshow(grid, cmap='Blues', interpolation='nearest')
plt.scatter(start_col, start_row, color='green', s=100, label='Start')
plt.scatter(end_col, end_row, color='red', s=100, label='End')
plt.title('Path taken by Q-learning')
plt.xlabel('Columns')
plt.ylabel('Rows')
plt.xticks(np.arange(grid_size))
plt.yticks(np.arange(grid_size))
plt.grid(True)
plt.legend()
plt.savefig('Q_learning_path.png')  # Save the path visualization as a PNG file
plt.show()