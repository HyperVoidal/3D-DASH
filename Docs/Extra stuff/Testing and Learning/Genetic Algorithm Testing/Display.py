import arcade

S_WIDTH = 800
S_HEIGHT = 600
S_TITLE = "Escape the Maze"

class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.window.set_mouse_visible(False)
        arcade.set_background_color(arcade.csscolor.FIREBRICK)
        
    def setup(self):
        pass

    def on_draw(self):
        self.clear()

class MainMenu(arcade.View):
    
    def on_show_view(self):
        arcade.set_background_color(arcade.csscolor.FIREBRICK)
    
    def on_draw(self):
        self.clear()
        
        arcade.set_background_color(arcade.csscolor.FIREBRICK)
        arcade.draw_text(
            "Escape the Maze",
            S_WIDTH/2, S_HEIGHT/2 + 75,
            arcade.color.BLACK,
            font_size=50,
            font_name="Impact",
            anchor_x="center"
        )
        arcade.draw_text(
            "click to start",
            S_WIDTH/2, S_HEIGHT/6,
            arcade.color.DARK_GRAY,
            italic=True,
            font_size=20,
            font_name="Arial",
            anchor_x="center"
        )
    
    def on_mouse_press(self, _x, _y, _button, _modifiers):
        game_view = GameView()
        self.window.show_view(game_view)
        game_view.setup()
    
def main():
    window = arcade.Window(S_WIDTH, S_HEIGHT, S_TITLE)
    start_view = MainMenu()
    window.show_view(start_view)
    arcade.run()

if __name__ == "__main__":
    main()
        
    