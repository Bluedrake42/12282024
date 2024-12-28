import pygame
from OpenGL.GL import *
import numpy as np

class TextRenderer:
    def __init__(self):
        pygame.font.init()
        self.fonts = {}
        self.textures = {}
        
    def create_font_texture(self, font_size):
        """Create a texture atlas for a given font size"""
        if font_size in self.textures:
            return
            
        font = pygame.font.Font(None, font_size)
        
        # Create surfaces for all necessary characters
        chars = "0123456789%/abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ. "
        char_surfaces = {}
        max_height = 0
        total_width = 0
        
        for char in chars:
            surface = font.render(char, True, (255, 255, 255))
            char_surfaces[char] = surface
            max_height = max(max_height, surface.get_height())
            total_width += surface.get_width()
        
        # Create texture atlas
        atlas_surface = pygame.Surface((total_width, max_height), pygame.SRCALPHA)
        atlas_surface.fill((0, 0, 0, 0))
        
        # Position information for each character
        char_data = {}
        x_offset = 0
        
        for char, surface in char_surfaces.items():
            atlas_surface.blit(surface, (x_offset, 0))
            char_data[char] = {
                'x': x_offset,
                'width': surface.get_width(),
                'height': surface.get_height()
            }
            x_offset += surface.get_width()

        # Flip the surface vertically before creating texture
        atlas_surface = pygame.transform.flip(atlas_surface, False, True)
        
        # Create OpenGL texture
        texture_data = pygame.image.tostring(atlas_surface, 'RGBA', True)
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, atlas_surface.get_width(), atlas_surface.get_height(),
                    0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        self.textures[font_size] = {
            'texture': texture,
            'width': atlas_surface.get_width(),
            'height': atlas_surface.get_height(),
            'char_data': char_data
        }
    
    def draw_text(self, text, x, y, font_size, color=(1, 1, 1, 1)):
        """Draw text at the specified position"""
        if font_size not in self.textures:
            self.create_font_texture(font_size)
            
        atlas_data = self.textures[font_size]
        texture = atlas_data['texture']
        atlas_height = atlas_data['height']
        char_data = atlas_data['char_data']
        
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glColor4f(*color)
        
        current_x = x
        for char in text:
            if char not in char_data:
                current_x += font_size // 3  # Space for unknown characters
                continue
                
            char_info = char_data[char]
            char_width = char_info['width']
            char_height = char_info['height']
            char_x = char_info['x']
            
            # Calculate texture coordinates
            tex_x1 = char_x / atlas_data['width']
            tex_x2 = (char_x + char_width) / atlas_data['width']
            
            # Draw character quad
            glBegin(GL_QUADS)
            glTexCoord2f(tex_x1, 0)
            glVertex2f(current_x, y)
            glTexCoord2f(tex_x2, 0)
            glVertex2f(current_x + char_width, y)
            glTexCoord2f(tex_x2, 1)
            glVertex2f(current_x + char_width, y + char_height)
            glTexCoord2f(tex_x1, 1)
            glVertex2f(current_x, y + char_height)
            glEnd()
            
            current_x += char_width
            
        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        
        return current_x - x  # Return the width of the rendered text
    
    def cleanup(self):
        """Delete all textures"""
        for atlas_data in self.textures.values():
            glDeleteTextures([atlas_data['texture']]) 
    
    def get_text_dimensions(self, text, font_size):
        """Calculate the width and height of text before rendering"""
        if font_size not in self.textures:
            self.create_font_texture(font_size)
            
        atlas_data = self.textures[font_size]
        char_data = atlas_data['char_data']
        
        total_width = 0
        max_height = 0
        
        for char in text:
            if char not in char_data:
                total_width += font_size // 3  # Space for unknown characters
                continue
                
            char_info = char_data[char]
            total_width += char_info['width']
            max_height = max(max_height, char_info['height'])
            
        return total_width, max_height

    def draw_text_centered(self, text, center_x, center_y, font_size, color=(1, 1, 1, 1)):
        """Draw text centered at the specified position"""
        width, height = self.get_text_dimensions(text, font_size)
        x = center_x - width // 2
        y = center_y - height // 2
        return self.draw_text(text, x, y, font_size, color)

    def draw_text_centered_rect(self, text, rect_x, rect_y, rect_width, rect_height, font_size, color=(1, 1, 1, 1)):
        """Draw text centered within a rectangle"""
        text_width, text_height = self.get_text_dimensions(text, font_size)
        x = rect_x + (rect_width - text_width) // 2
        y = rect_y + (rect_height - text_height) // 2
        return self.draw_text(text, x, y, font_size, color) 