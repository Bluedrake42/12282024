import math
from OpenGL.GL import *
import pygame
from pygame.locals import *
import numpy as np
import configparser
import time
from text_renderer import TextRenderer
from projectile import PlayerProjectile

class Player:
    def __init__(self):
        # Load settings
        config = configparser.ConfigParser()
        config.read('settings.cfg')
        
        self.pos = [0, 0, 0]
        self.rot = [0, 0]  # pitch, yaw
        self.speed = 5.0  # Units per second
        self.mouse_sensitivity = float(config.get('Controls', 'mouse_sensitivity', fallback='0.2'))
        self.projectiles = []
        self.last_shot_time = 0
        self.shot_cooldown = 0.2  # Seconds between shots
        self.max_health = int(config.get('Player', 'max_health', fallback='100'))
        self.health = self.max_health
        self.is_dead = False
        self.death_time = None
        self.respawn_delay = int(config.get('Player', 'respawn_delay', fallback='10'))
        
        # Combat properties
        self.armor_rating = 1.0
        self.material_type = "player"  # Special material type for player
        
        # Zoom settings
        self.is_zoomed = False
        self.was_right_clicked = False  # Track previous right click state
        self.normal_fov = 90.0  # Explicit float values
        self.zoom_fov = 30.0    # Explicit float values
        self.current_fov = self.normal_fov
        self.fov_transition_speed = 8.0  # Speed of FOV change
        self.zoom_sensitivity_multiplier = 0.4  # Reduce sensitivity when zoomed
        
        # Initialize text renderer
        self.text_renderer = TextRenderer()

    def die(self):
        if not self.is_dead:
            self.is_dead = True
            self.health = 0
            self.death_time = time.time()
            print("Player died!")  # Debug print
        
    def respawn(self):
        self.health = self.max_health
        self.pos = [0, 0, 0]
        self.rot = [0, 0]
        self.projectiles.clear()
        self.is_dead = False
        self.death_time = None

    def set_mouse_sensitivity(self, sensitivity):
        self.mouse_sensitivity = max(0.01, min(1.0, sensitivity))
        # Save to config
        config = configparser.ConfigParser()
        config.read('settings.cfg')
        config['Controls']['mouse_sensitivity'] = str(sensitivity)
        with open('settings.cfg', 'w') as configfile:
            config.write(configfile)

    def draw_crosshair(self, screen_width, screen_height):
        # Switch to 2D orthographic projection for crosshair
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, screen_width, screen_height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Draw crosshair
        size = 10
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        glLineWidth(2.0)
        glColor3f(1, 1, 1)  # White crosshair
        glBegin(GL_LINES)
        # Horizontal line
        glVertex2f(center_x - size, center_y)
        glVertex2f(center_x + size, center_y)
        # Vertical line
        glVertex2f(center_x, center_y - size)
        glVertex2f(center_x, center_y + size)
        glEnd()

        # Restore 3D projection
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def create_text_texture(self, text, font_size, color):
        font = pygame.font.Font(None, font_size)
        text_surface = font.render(text, True, color)
        text_data = pygame.image.tostring(text_surface, 'RGBA', True)
        
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_surface.get_width(), text_surface.get_height(),
                    0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        return texture, text_surface.get_width(), text_surface.get_height()

    def draw_text_quad(self, texture, x, y, width, height):
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x, y)
        glTexCoord2f(1, 0); glVertex2f(x + width, y)
        glTexCoord2f(1, 1); glVertex2f(x + width, y + height)
        glTexCoord2f(0, 1); glVertex2f(x, y + height)
        glEnd()
        glDisable(GL_TEXTURE_2D)

    def draw_death_screen(self, screen_width, screen_height, time_remaining):
        if not self.is_dead or self.death_time is None:
            return

        # Switch to 2D orthographic projection
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, screen_width, screen_height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Draw black overlay
        glColor4f(0, 0, 0, 0.8)
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(screen_width, 0)
        glVertex2f(screen_width, screen_height)
        glVertex2f(0, screen_height)
        glEnd()

        # Calculate vertical spacing
        center_y = screen_height // 2
        spacing = 80  # Vertical space between text elements

        # Draw "YOU HAVE DIED" text centered
        self.text_renderer.draw_text_centered("YOU HAVE DIED",
                                            screen_width // 2,
                                            center_y - spacing,
                                            140,
                                            color=(1, 0, 0, 1))
        
        # Draw "respawning in" text centered
        self.text_renderer.draw_text_centered("respawning in",
                                            screen_width // 2,
                                            center_y,
                                            72)
        
        # Draw countdown centered
        self.text_renderer.draw_text_centered(str(max(0, int(time_remaining))),
                                            screen_width // 2,
                                            center_y + spacing,
                                            96)

        # Restore matrices
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()
        
        glDisable(GL_BLEND)

    def take_damage(self, damage):
        if self.is_dead:
            return False
            
        # Apply armor rating to incoming damage
        final_damage = round(damage / self.armor_rating, 1)  # Round to 1 decimal place
        self.health = round(max(0, self.health - final_damage), 1)  # Round health to 1 decimal place
        
        if self.health <= 0:
            self.die()
            return True
        return False

    def check_projectile_hit(self, projectile_pos, projectile_radius):
        if self.is_dead:
            return False
            
        # Simple sphere collision
        dx = self.pos[0] - projectile_pos[0]
        dy = self.pos[1] - projectile_pos[1]
        dz = self.pos[2] - projectile_pos[2]
        distance = np.sqrt(dx*dx + dy*dy + dz*dz)
        
        # Player hit radius of 1.0
        return distance < (1.0 + projectile_radius)

    def get_view_direction(self):
        pitch = math.radians(self.rot[0])
        yaw = math.radians(self.rot[1])
        
        # Calculate direction vector (inverted the signs for correct direction)
        dx = -math.sin(yaw) * math.cos(pitch)
        dy = math.sin(pitch)  # Inverted pitch for correct up/down
        dz = -math.cos(yaw) * math.cos(pitch)
        
        return [dx, dy, dz]

    def shoot(self, current_time):
        if current_time - self.last_shot_time < self.shot_cooldown:
            return None

        self.last_shot_time = current_time
        direction = self.get_view_direction()
        
        # Create projectile slightly in front of player
        spawn_pos = [
            self.pos[0] + direction[0],
            self.pos[1] + direction[1],
            self.pos[2] + direction[2]
        ]
        
        return PlayerProjectile(spawn_pos, direction)

    def update(self, dt, current_time):
        if self.is_dead:
            if self.death_time is not None:
                time_since_death = current_time - self.death_time
                if time_since_death >= self.respawn_delay:
                    self.respawn()
            return

        # Handle zoom toggle with state tracking
        mouse_buttons = pygame.mouse.get_pressed()
        is_right_clicked = mouse_buttons[2]  # Current right click state
        
        if is_right_clicked and not self.was_right_clicked:  # Only toggle on button press
            self.is_zoomed = not self.is_zoomed
            # Snap FOV to target value to ensure consistency
            self.current_fov = self.zoom_fov if self.is_zoomed else self.normal_fov
            
        self.was_right_clicked = is_right_clicked  # Update previous state

        # Update FOV smoothly
        target_fov = self.zoom_fov if self.is_zoomed else self.normal_fov
        fov_diff = target_fov - self.current_fov
        if abs(fov_diff) > 0.01:  # Small threshold for floating point comparison
            self.current_fov += fov_diff * dt * self.fov_transition_speed
            # Clamp FOV to target values to prevent overshooting
            if self.is_zoomed:
                self.current_fov = max(self.current_fov, self.zoom_fov)
            else:
                self.current_fov = min(self.current_fov, self.normal_fov)

        # Adjust mouse sensitivity based on zoom
        current_sensitivity = self.mouse_sensitivity * (self.zoom_sensitivity_multiplier if self.is_zoomed else 1.0)

        # Mouse look
        mouse_dx, mouse_dy = pygame.mouse.get_rel()
        self.rot[0] += -mouse_dy * current_sensitivity
        self.rot[1] += -mouse_dx * current_sensitivity
        
        # Clamp pitch to prevent over-rotation
        self.rot[0] = max(-90, min(90, self.rot[0]))

        # Movement
        keys = pygame.key.get_pressed()
        move_x = keys[K_d] - keys[K_a]
        move_z = keys[K_s] - keys[K_w]

        # Calculate forward and right vectors
        yaw = math.radians(self.rot[1])
        forward_x = math.sin(yaw)
        forward_z = math.cos(yaw)
        right_x = math.cos(yaw)
        right_z = -math.sin(yaw)

        # Apply movement with delta time
        self.pos[0] += (forward_x * move_z + right_x * move_x) * self.speed * dt
        self.pos[2] += (forward_z * move_z + right_z * move_x) * self.speed * dt

        # Handle shooting
        if not self.is_dead and mouse_buttons[0]:  # Left mouse button
            new_projectile = self.shoot(current_time)
            if new_projectile:
                self.projectiles.append(new_projectile)

        # Update projectiles
        for projectile in self.projectiles:
            projectile.update(dt)

        # Remove projectiles that are too far away
        self.projectiles = [p for p in self.projectiles if p.alive and 
                          abs(p.pos[0] - self.pos[0]) < 100 and 
                          abs(p.pos[2] - self.pos[2]) < 100]

    def apply_transform(self):
        glRotatef(-self.rot[0], 1, 0, 0)
        glRotatef(-self.rot[1], 0, 1, 0)
        glTranslatef(-self.pos[0], -self.pos[1], -self.pos[2])

    def draw_projectiles(self):
        for projectile in self.projectiles:
            projectile.draw() 

    def draw_health_bar(self, screen_width, screen_height):
        # Switch to 2D orthographic projection
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, screen_width, screen_height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Health bar settings
        bar_width = 200
        bar_height = 20
        x = 10
        y = 10
        border = 2
        health_percentage = self.health / self.max_health

        # Draw border (black)
        glColor3f(0, 0, 0)
        glBegin(GL_QUADS)
        glVertex2f(x - border, y - border)
        glVertex2f(x + bar_width + border, y - border)
        glVertex2f(x + bar_width + border, y + bar_height + border)
        glVertex2f(x - border, y + bar_height + border)
        glEnd()

        # Draw background (dark gray)
        glColor3f(0.2, 0.2, 0.2)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + bar_width, y)
        glVertex2f(x + bar_width, y + bar_height)
        glVertex2f(x, y + bar_height)
        glEnd()

        # Draw health bar with color gradient
        if health_percentage > 0:
            # Color changes from green to yellow to red
            if health_percentage > 0.5:
                r = 2.0 * (1 - health_percentage)  # 0.5 -> 1: 1 -> 0
                g = 1.0
            else:
                r = 1.0
                g = 2.0 * health_percentage  # 0 -> 0.5: 0 -> 1
            glColor3f(r, g, 0)
            
            bar_fill_width = bar_width * health_percentage
            glBegin(GL_QUADS)
            glVertex2f(x, y)
            glVertex2f(x + bar_fill_width, y)
            glVertex2f(x + bar_fill_width, y + bar_height)
            glVertex2f(x, y + bar_height)
            glEnd()

        # Draw text
        percentage_text = f"{int(health_percentage * 100)}%"
        fraction_text = f"{round(self.health, 1)}/{self.max_health}"  # Round displayed health to 1 decimal
        
        # Draw percentage text (centered in health bar)
        self.text_renderer.draw_text_centered_rect(percentage_text, 
                                                 x, y, bar_width, bar_height, 24)
        
        # Draw fraction text (to the right of health bar)
        fraction_width, fraction_height = self.text_renderer.get_text_dimensions(fraction_text, 24)
        self.text_renderer.draw_text(fraction_text, 
                                   x + bar_width + 10,
                                   y + (bar_height - fraction_height) // 2, 24)

        # Restore 3D projection
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def cleanup(self):
        """Clean up resources"""
        self.text_renderer.cleanup() 

    def get_current_fov(self):
        """Get the current FOV value for rendering"""
        return self.current_fov 