import random
from OpenGL.GL import *
import numpy as np
import math

class EnemyProjectile:
    def __init__(self, pos, direction, speed=20.0):
        self.pos = list(pos)
        length = np.sqrt(sum(x*x for x in direction))
        self.velocity = [d * speed / length for d in direction]
        self.alive = True
        self.radius = 0.2
        self.damage = 10

    def update(self, dt):
        self.pos[0] += self.velocity[0] * dt
        self.pos[1] += self.velocity[1] * dt
        self.pos[2] += self.velocity[2] * dt

    def draw(self):
        glPushMatrix()
        glTranslatef(*self.pos)
        glColor3f(1, 0, 0)  # Red projectile
        glPointSize(5.0)
        glBegin(GL_POINTS)
        glVertex3f(0, 0, 0)
        glEnd()
        glPopMatrix()

class Enemy:
    def __init__(self, pos):
        self.pos = list(pos)
        self.size = 1.0
        self.alive = True
        self.color = (1, 0, 0)  # Red enemy
        self.hit_radius = 1.0
        self.speed = 3.0  # Units per second
        self.last_shot_time = 0
        self.shot_cooldown = 2.0  # Seconds between shots
        self.projectiles = []
        self.target_pos = None
        self.movement_timer = 0
        self.movement_interval = 3.0  # Time between position updates

    def update_movement(self, dt, player_pos):
        self.movement_timer += dt
        
        # Update target position periodically
        if self.movement_timer >= self.movement_interval:
            self.movement_timer = 0
            # Set new target position randomly around player
            angle = random.uniform(0, 2 * np.pi)
            distance = random.uniform(8, 15)
            self.target_pos = [
                player_pos[0] + distance * np.cos(angle),
                0,  # Keep at ground level
                player_pos[2] + distance * np.sin(angle)
            ]

        # Move towards target position if we have one
        if self.target_pos:
            dx = self.target_pos[0] - self.pos[0]
            dz = self.target_pos[2] - self.pos[2]
            distance = math.sqrt(dx*dx + dz*dz)
            
            if distance > 0.1:  # Only move if we're not very close
                # Normalize direction and apply speed
                self.pos[0] += (dx / distance) * self.speed * dt
                self.pos[2] += (dz / distance) * self.speed * dt

    def shoot_at_player(self, current_time, player_pos):
        if current_time - self.last_shot_time < self.shot_cooldown:
            return None

        self.last_shot_time = current_time
        
        # Calculate direction to player
        dx = player_pos[0] - self.pos[0]
        dy = player_pos[1] - self.pos[1]
        dz = player_pos[2] - self.pos[2]
        
        # Add some randomness to make it less accurate
        dx += random.uniform(-1, 1)
        dy += random.uniform(-1, 1)
        dz += random.uniform(-1, 1)
        
        direction = [dx, dy, dz]
        return EnemyProjectile(self.pos.copy(), direction)

    def update_projectiles(self, dt):
        for projectile in self.projectiles:
            projectile.update(dt)
        # Remove projectiles that are too far
        self.projectiles = [p for p in self.projectiles if p.alive and 
                          abs(p.pos[0] - self.pos[0]) < 50 and 
                          abs(p.pos[2] - self.pos[2]) < 50]

    def draw_projectiles(self):
        for projectile in self.projectiles:
            projectile.draw()

    def check_hit(self, projectile):
        if not self.alive:
            return False
            
        # Simple sphere collision
        dx = self.pos[0] - projectile.pos[0]
        dy = self.pos[1] - projectile.pos[1]
        dz = self.pos[2] - projectile.pos[2]
        distance = np.sqrt(dx*dx + dy*dy + dz*dz)
        
        return distance < (self.hit_radius + projectile.radius)

    def draw(self):
        if not self.alive:
            return
            
        glPushMatrix()
        glTranslatef(*self.pos)
        
        # Draw enemy cube
        glColor3f(*self.color)
        glBegin(GL_QUADS)
        s = self.size / 2
        
        # Front face
        glVertex3f(-s, -s, s)
        glVertex3f(s, -s, s)
        glVertex3f(s, s, s)
        glVertex3f(-s, s, s)
        
        # Back face
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, s, -s)
        glVertex3f(s, s, -s)
        glVertex3f(s, -s, -s)
        
        # Top face
        glVertex3f(-s, s, -s)
        glVertex3f(-s, s, s)
        glVertex3f(s, s, s)
        glVertex3f(s, s, -s)
        
        # Bottom face
        glVertex3f(-s, -s, -s)
        glVertex3f(s, -s, -s)
        glVertex3f(s, -s, s)
        glVertex3f(-s, -s, s)
        
        # Right face
        glVertex3f(s, -s, -s)
        glVertex3f(s, s, -s)
        glVertex3f(s, s, s)
        glVertex3f(s, -s, s)
        
        # Left face
        glVertex3f(-s, -s, -s)
        glVertex3f(-s, -s, s)
        glVertex3f(-s, s, s)
        glVertex3f(-s, s, -s)
        
        glEnd()
        glPopMatrix()

class EnemyManager:
    def __init__(self):
        self.enemies = []
        self.spawn_timer = 0
        self.spawn_interval = 3.0  # Seconds between spawns
        self.max_enemies = 5

    def spawn_enemy(self):
        if len(self.enemies) >= self.max_enemies:
            return

        # Spawn in random position around player
        angle = random.uniform(0, 2 * np.pi)
        distance = random.uniform(10, 20)
        x = distance * np.cos(angle)
        z = distance * np.sin(angle)
        y = 0  # Spawn at ground level

        self.enemies.append(Enemy([x, y, z]))

    def update(self, dt, current_time, player):
        # Spawn new enemies
        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0
            self.spawn_enemy()

        hit_pos = None
        # Update enemies and check for hits
        for enemy in self.enemies:
            if not enemy.alive:
                continue

            # Update enemy movement
            enemy.update_movement(dt, player.pos)
            
            # Update enemy shooting
            new_projectile = enemy.shoot_at_player(current_time, player.pos)
            if new_projectile:
                enemy.projectiles.append(new_projectile)
            
            # Update enemy projectiles
            enemy.update_projectiles(dt)
            
            # Check if enemy projectiles hit player
            for projectile in enemy.projectiles:
                if projectile.alive:
                    if player.check_projectile_hit(projectile.pos, projectile.radius):
                        projectile.alive = False
                        player.take_damage(projectile.damage)
            
            # Check if player projectiles hit enemy
            for projectile in player.projectiles:
                if enemy.check_hit(projectile):
                    enemy.alive = False
                    projectile.alive = False
                    hit_pos = enemy.pos
                    break

        return hit_pos

    def draw(self):
        for enemy in self.enemies:
            if enemy.alive:
                enemy.draw()
                enemy.draw_projectiles()

    def cleanup(self):
        # Remove dead enemies after some time
        self.enemies = [e for e in self.enemies if e.alive] 