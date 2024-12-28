import random
from OpenGL.GL import *
import numpy as np
import math
from projectile import EnemyProjectile

class EnemyPart:
    def __init__(self, relative_pos, size, health, color, name, material_type="metal"):
        self.relative_pos = list(relative_pos)  # Position relative to enemy center
        self.size = size
        self.max_health = health
        self.health = health
        self.color = list(color)
        self.name = name
        self.alive = True
        self.material_type = material_type
        
        # Define faces for hit detection (normal vectors pointing outward)
        self.faces = [
            {"normal": [0, 0, 1], "vertices": []},   # Front
            {"normal": [0, 0, -1], "vertices": []},  # Back
            {"normal": [0, 1, 0], "vertices": []},   # Top
            {"normal": [0, -1, 0], "vertices": []},  # Bottom
            {"normal": [1, 0, 0], "vertices": []},   # Right
            {"normal": [-1, 0, 0], "vertices": []}   # Left
        ]
        self._calculate_face_vertices()
        
        # Damage resistance properties
        self.armor_rating = {
            "core": 1.2,
            "shield_generator": 0.8,
            "weapon_left": 0.9,
            "weapon_right": 0.9,
            "engine": 0.7
        }.get(name, 1.0)

    def _calculate_face_vertices(self):
        """Calculate vertices for each face based on size"""
        s = self.size / 2
        
        # Front face vertices (clockwise order)
        self.faces[0]["vertices"] = [
            [-s, -s, s], [s, -s, s],
            [s, s, s], [-s, s, s]
        ]
        
        # Back face vertices
        self.faces[1]["vertices"] = [
            [-s, -s, -s], [-s, s, -s],
            [s, s, -s], [s, -s, -s]
        ]
        
        # Top face vertices
        self.faces[2]["vertices"] = [
            [-s, s, -s], [-s, s, s],
            [s, s, s], [s, s, -s]
        ]
        
        # Bottom face vertices
        self.faces[3]["vertices"] = [
            [-s, -s, -s], [s, -s, -s],
            [s, -s, s], [-s, -s, s]
        ]
        
        # Right face vertices
        self.faces[4]["vertices"] = [
            [s, -s, -s], [s, s, -s],
            [s, s, s], [s, -s, s]
        ]
        
        # Left face vertices
        self.faces[5]["vertices"] = [
            [-s, -s, -s], [-s, -s, s],
            [-s, s, s], [-s, s, -s]
        ]

    def get_world_vertices(self, enemy_pos):
        """Get vertices in world space"""
        world_vertices = []
        for face in self.faces:
            face_verts = []
            for vertex in face["vertices"]:
                world_vert = [
                    enemy_pos[0] + self.relative_pos[0] + vertex[0],
                    enemy_pos[1] + self.relative_pos[1] + vertex[1],
                    enemy_pos[2] + self.relative_pos[2] + vertex[2]
                ]
                face_verts.append(world_vert)
            world_vertices.append(face_verts)
        return world_vertices

    def check_collision(self, projectile, enemy_pos):
        """Check if projectile hits this part and calculate impact"""
        if not self.alive:
            return False, None
            
        # Simple sphere-box collision first for performance
        part_pos = [
            enemy_pos[0] + self.relative_pos[0],
            enemy_pos[1] + self.relative_pos[1],
            enemy_pos[2] + self.relative_pos[2]
        ]
        
        dx = part_pos[0] - projectile.pos[0]
        dy = part_pos[1] - projectile.pos[1]
        dz = part_pos[2] - projectile.pos[2]
        distance = np.sqrt(dx*dx + dy*dy + dz*dz)
        
        if distance > (self.size + projectile.radius):
            return False, None
            
        # If we're here, we need to do detailed collision detection
        # Find the closest face and its normal
        closest_face = None
        closest_dist = float('inf')
        hit_point = None
        
        for face_idx, face in enumerate(self.faces):
            # Transform face normal to world space (simplified - assumes no rotation)
            world_normal = face["normal"]
            
            # Get face vertices in world space
            world_vertices = []
            for vertex in face["vertices"]:
                world_vertices.append([
                    part_pos[0] + vertex[0],
                    part_pos[1] + vertex[1],
                    part_pos[2] + vertex[2]
                ])
            
            # Calculate distance from projectile to face plane
            face_point = world_vertices[0]  # Any vertex will do for plane calculation
            
            # Vector from face to projectile
            to_projectile = [
                projectile.pos[0] - face_point[0],
                projectile.pos[1] - face_point[1],
                projectile.pos[2] - face_point[2]
            ]
            
            # Distance to plane
            dist = sum(a*b for a, b in zip(to_projectile, world_normal))
            
            if abs(dist) < closest_dist and abs(dist) <= projectile.radius:
                # Calculate hit point on plane
                potential_hit = [
                    projectile.pos[0] - dist * world_normal[0],
                    projectile.pos[1] - dist * world_normal[1],
                    projectile.pos[2] - dist * world_normal[2]
                ]
                
                # Check if hit point is inside face bounds
                if self._point_in_face(potential_hit, world_vertices, face_idx):
                    closest_dist = abs(dist)
                    closest_face = face
                    hit_point = potential_hit
        
        if closest_face is not None:
            return True, {
                "hit_point": hit_point,
                "normal": closest_face["normal"],
                "material": self.material_type
            }
            
        return False, None

    def _point_in_face(self, point, vertices, face_idx):
        """Check if a point lies within a face's boundaries"""
        # Different checks based on face orientation
        if face_idx in [0, 1]:  # Front/Back faces (check X and Y)
            x, y = 0, 1
        elif face_idx in [2, 3]:  # Top/Bottom faces (check X and Z)
            x, y = 0, 2
        else:  # Left/Right faces (check Y and Z)
            x, y = 1, 2
            
        # Get 2D coordinates of point and vertices for the relevant plane
        point_2d = [point[x], point[y]]
        vertices_2d = [[v[x], v[y]] for v in vertices]
        
        # Check if point is inside the 2D polygon
        return self._point_in_polygon_2d(point_2d, vertices_2d)
        
    def _point_in_polygon_2d(self, point, vertices):
        """Check if a 2D point is inside a polygon using ray casting"""
        x, y = point
        inside = False
        
        j = len(vertices) - 1
        for i in range(len(vertices)):
            if ((vertices[i][1] > y) != (vertices[j][1] > y) and
                x < (vertices[j][0] - vertices[i][0]) * (y - vertices[i][1]) /
                    (vertices[j][1] - vertices[i][1]) + vertices[i][0]):
                inside = not inside
            j = i
            
        return inside

    def take_damage(self, impact_data):
        """Handle physics-based damage"""
        if not self.alive:
            return False
            
        # Apply armor rating to incoming damage
        damage = impact_data["damage"] / self.armor_rating
        
        # Additional effects based on penetration
        if impact_data["penetration"] > 0.8:
            damage *= 1.5  # Critical hit for high penetration
            
        # Apply damage
        self.health -= damage
        
        # Update color based on damage
        damage_factor = max(0, self.health / self.max_health)
        self.color = [c * damage_factor for c in self.color]
        
        # Check if destroyed
        if self.health <= 0:
            self.alive = False
            return True
            
        return False

    def draw(self, enemy_pos):
        if not self.alive:
            return

        pos = [
            enemy_pos[0] + self.relative_pos[0],
            enemy_pos[1] + self.relative_pos[1],
            enemy_pos[2] + self.relative_pos[2]
        ]

        glPushMatrix()
        glTranslatef(*pos)
        
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

class Enemy:
    def __init__(self, pos):
        self.pos = list(pos)
        self.speed = 3.0
        self.last_shot_time = 0
        self.shot_cooldown = 2.0
        self.projectiles = []
        self.target_pos = None
        self.movement_timer = 0
        self.movement_interval = 3.0
        
        # Initialize enemy parts with specific materials
        self.parts = [
            EnemyPart([0, 0, 0], 1.0, 100, [1, 0, 0], "core", "core"),  # Core (red)
            EnemyPart([0, 0.8, 0], 0.6, 50, [0, 1, 0], "shield_generator", "shield"),  # Shield generator (green)
            EnemyPart([0.6, 0, 0], 0.4, 30, [1, 1, 0], "weapon_right", "metal"),  # Right weapon (yellow)
            EnemyPart([-0.6, 0, 0], 0.4, 30, [1, 1, 0], "weapon_left", "metal"),  # Left weapon (yellow)
            EnemyPart([0, 0, 0.6], 0.5, 40, [0, 0, 1], "engine", "engine"),  # Engine (blue)
        ]
        
        self.alive = True

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
            return False, None

        # Check each part for hits
        for part in self.parts:
            hit, hit_data = part.check_collision(projectile, self.pos)
            if hit:
                # Calculate impact physics
                impact_data = projectile.calculate_impact(
                    hit_data["hit_point"],
                    hit_data["normal"],
                    hit_data["material"]
                )
                
                # Apply damage to the part
                destroyed = part.take_damage(impact_data)
                
                # If core is destroyed, enemy dies
                if destroyed and part.name == "core":
                    self.alive = False
                
                # Modify behavior based on destroyed parts
                if destroyed:
                    if part.name == "shield_generator":
                        # Make all remaining parts more vulnerable
                        for p in self.parts:
                            if p.alive:
                                p.armor_rating *= 0.7
                    elif part.name in ["weapon_left", "weapon_right"]:
                        # Increase shot cooldown as weapons are destroyed
                        self.shot_cooldown *= 1.5
                    elif part.name == "engine":
                        # Reduce speed when engine is destroyed
                        self.speed *= 0.5
                
                return True, impact_data["impact_point"]
        
        return False, None

    def draw(self):
        if not self.alive:
            return
            
        # Draw all alive parts
        for part in self.parts:
            part.draw(self.pos)

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
                        # Calculate impact damage for player
                        impact_data = projectile.calculate_impact(
                            player.pos,  # Hit point (player center)
                            [0, 1, 0],   # Default normal (up)
                            "player"     # Player material type
                        )
                        player.take_damage(impact_data["damage"])
            
            # Check if player projectiles hit enemy
            for projectile in player.projectiles:
                hit, pos = enemy.check_hit(projectile)  # Get both hit status and position
                if hit:
                    projectile.alive = False
                    hit_pos = pos  # Use the actual hit position for particles

        return hit_pos

    def draw(self):
        for enemy in self.enemies:
            if enemy.alive:
                enemy.draw()
                enemy.draw_projectiles()

    def cleanup(self):
        # Remove dead enemies after some time
        self.enemies = [e for e in self.enemies if e.alive] 