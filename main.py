import sys
import subprocess
import time
import configparser
import os

def check_and_install_dependencies():
    print("Starting dependency check...")
    required = {
        'pygame': '2.5.2',
        'PyOpenGL': '3.1.7',
        'numpy': '1.26.2'
    }
    
    def install(package, version):
        print(f"Installing {package} {version}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", f"{package}=={version}"], 
                                stderr=subprocess.STDOUT)
            print(f"Successfully installed {package} {version}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {package}. Error: {e.output if hasattr(e, 'output') else str(e)}")
            sys.exit(1)

    for package, version in required.items():
        try:
            __import__(package)
            print(f"Found {package}")
        except ImportError as e:
            print(f"ImportError for {package}: {str(e)}")
            install(package, version)

print("Starting program...")
try:
    check_and_install_dependencies()
except Exception as e:
    print(f"Unexpected error during dependency check: {str(e)}")
    sys.exit(1)

print("Dependencies checked, importing modules...")
try:
    import pygame
    from pygame.locals import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
    import math
    import numpy as np
    from particle_system import ParticleSystem
    from player import Player
    from enemy import EnemyManager
    print("All modules imported successfully")
except ImportError as e:
    print(f"Failed to import required modules: {str(e)}")
    sys.exit(1)

print("Initializing Pygame and OpenGL...")
try:
    pygame.init()
    
    # Load settings
    config = configparser.ConfigParser()
    config.read('settings.cfg')
    
    # Get display settings
    screen_width = int(config.get('Game', 'screen_width', fallback='800'))
    screen_height = int(config.get('Game', 'screen_height', fallback='600'))
    window_mode = config.get('Game', 'window_mode', fallback='windowed').lower()
    vsync = config.getboolean('Game', 'vsync', fallback=True)
    
    # Set display flags
    flags = DOUBLEBUF | OPENGL
    if window_mode == 'fullscreen':
        flags |= FULLSCREEN
    elif window_mode == 'borderless':
        flags |= NOFRAME
    
    # Get the current display info
    display_info = pygame.display.Info()
    current_width = display_info.current_w
    current_height = display_info.current_h
    
    print(f"Monitor resolution: {current_width}x{current_height}")
    print(f"Requested resolution: {screen_width}x{screen_height}")
    print(f"Window mode: {window_mode}")
    
    # Create the window
    if window_mode == 'borderless':
        # For borderless, use the full screen resolution
        pygame.display.set_mode((current_width, current_height), flags)
    else:
        # For windowed or fullscreen, use the configured resolution
        pygame.display.set_mode((screen_width, screen_height), flags)
    
    # Set window position for windowed mode
    if window_mode == 'windowed':
        # Center the window
        os.environ['SDL_VIDEO_CENTERED'] = '1'
    
    pygame.display.set_caption("FPS Game")
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    
    if vsync:
        pygame.display.gl_set_attribute(pygame.GL_SWAP_CONTROL, 1)
    
    # Update display tuple for aspect ratio calculation
    display = pygame.display.get_surface().get_size()
    print(f"Final window size: {display[0]}x{display[1]}")
    
except Exception as e:
    print(f"Failed to initialize Pygame/OpenGL: {str(e)}")
    pygame.quit()
    sys.exit(1)

# Camera settings
fov = 90
aspect_ratio = display[0] / display[1]
near_clip = 0.1
far_clip = 100.0

def draw_floor():
    glBegin(GL_QUADS)
    glColor3f(0.5, 0.5, 0.5)
    size = 50  # Increased floor size
    glVertex3f(-size, -2, -size)
    glVertex3f(size, -2, -size)
    glVertex3f(size, -2, size)
    glVertex3f(-size, -2, size)
    glEnd()

class GameState:
    def __init__(self):
        # Load settings
        config = configparser.ConfigParser()
        config.read('settings.cfg')
        
        self.screen_width = int(config.get('Game', 'screen_width', fallback='800'))
        self.screen_height = int(config.get('Game', 'screen_height', fallback='600'))
        
        self.player = Player()
        self.particle_system = ParticleSystem()
        self.enemy_manager = EnemyManager()
        self.last_time = time.time()
        self.frame_count = 0
        self.last_fps_update = time.time()
        self.fps = 0
        self.font = pygame.font.Font(None, 36)

    def reset_game(self):
        self.player.respawn()
        self.enemy_manager = EnemyManager()
        self.particle_system = ParticleSystem()

    def update(self):
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time

        # Update FPS counter
        self.frame_count += 1
        if current_time - self.last_fps_update >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_fps_update = current_time

        # Update game objects
        self.player.update(dt, current_time)
        
        if not self.player.is_dead:
            # Update enemies and check for hits
            hit_pos = self.enemy_manager.update(dt, current_time, self.player)
            if hit_pos:
                self.particle_system.emit_explosion(hit_pos)
        
        self.particle_system.update(dt)
        self.enemy_manager.cleanup()

    def draw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluPerspective(self.player.get_current_fov(), aspect_ratio, near_clip, far_clip)
        
        self.player.apply_transform()
        
        # Enable depth testing
        glEnable(GL_DEPTH_TEST)
        
        # Draw 3D scene
        draw_floor()
        self.enemy_manager.draw()
        self.player.draw_projectiles()
        self.particle_system.draw()
        
        # Draw 2D overlays
        glDisable(GL_DEPTH_TEST)
        
        if not self.player.is_dead:
            # Draw crosshair
            self.player.draw_crosshair(self.screen_width, self.screen_height)
            
            # Draw UI elements
            pygame.display.get_surface().fill((0, 0, 0, 0))
            
            # FPS counter (top right)
            fps_text = self.font.render(f"FPS: {self.fps}", True, (255, 255, 255))
            pygame.display.get_surface().blit(fps_text, 
                (self.screen_width - fps_text.get_width() - 10, 10))
            
            # Health bar
            self.player.draw_health_bar(self.screen_width, self.screen_height)
        else:
            # Draw death screen with countdown
            time_remaining = self.player.respawn_delay - (time.time() - self.player.death_time)
            self.player.draw_death_screen(self.screen_width, self.screen_height, time_remaining)

def main():
    game_state = GameState()
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                # Adjust mouse sensitivity
                elif event.key == pygame.K_COMMA:  # < key
                    sensitivity = game_state.player.mouse_sensitivity - 0.05
                    game_state.player.set_mouse_sensitivity(sensitivity)
                elif event.key == pygame.K_PERIOD:  # > key
                    sensitivity = game_state.player.mouse_sensitivity + 0.05
                    game_state.player.set_mouse_sensitivity(sensitivity)

        game_state.update()
        game_state.draw()
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main() 