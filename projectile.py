from OpenGL.GL import *
import numpy as np
import math

class Projectile:
    def __init__(self, pos, direction, speed, damage_profile=None):
        self.pos = list(pos)
        # Normalize direction
        length = np.sqrt(sum(x*x for x in direction))
        self.velocity = [d * speed / length for d in direction]
        self.alive = True
        self.radius = 0.2
        
        # Default damage profile if none provided
        self.damage_profile = damage_profile or {
            "impact": 20,  # Base impact damage
            "penetration": 0.5,  # How well it penetrates armor (0-1)
            "splash": 0,  # Splash damage radius
            "energy_transfer": 0.8,  # How much energy is transferred to the target (0-1)
        }
        
        # Physics properties
        self.mass = 0.1  # kg
        self.energy = 0.5 * self.mass * (speed ** 2)  # Kinetic energy
        
    def update(self, dt):
        self.pos[0] += self.velocity[0] * dt
        self.pos[1] += self.velocity[1] * dt
        self.pos[2] += self.velocity[2] * dt
        
    def calculate_impact(self, hit_point, surface_normal, target_material):
        """Calculate impact effects based on physics"""
        # Calculate angle of impact
        impact_angle = self._calculate_impact_angle(surface_normal)
        
        # Calculate energy transfer based on angle and material
        energy_transfer = self._calculate_energy_transfer(impact_angle, target_material)
        
        # Calculate penetration
        penetration = self._calculate_penetration(energy_transfer, target_material)
        
        # Calculate final damage
        damage = self._calculate_damage(energy_transfer, penetration)
        
        return {
            "damage": damage,
            "penetration": penetration,
            "energy_transfer": energy_transfer,
            "impact_point": hit_point,
            "impact_angle": impact_angle
        }
    
    def _calculate_impact_angle(self, surface_normal):
        """Calculate angle between projectile velocity and surface normal"""
        v_norm = np.array(self.velocity) / np.linalg.norm(self.velocity)
        n_norm = np.array(surface_normal) / np.linalg.norm(surface_normal)
        cos_angle = np.dot(v_norm, n_norm)
        return math.acos(max(-1, min(1, cos_angle)))  # Clamp to prevent floating point errors
        
    def _calculate_energy_transfer(self, impact_angle, target_material):
        """Calculate how much energy is transferred to the target"""
        # Angle factor: More energy transfer at perpendicular impacts
        angle_factor = abs(math.cos(impact_angle))
        
        # Material factor: Different materials absorb energy differently
        material_factors = {
            "metal": 0.7,
            "shield": 0.9,
            "core": 0.8,
            "engine": 0.6
        }
        material_factor = material_factors.get(target_material, 0.7)
        
        return self.energy * angle_factor * material_factor * self.damage_profile["energy_transfer"]
        
    def _calculate_penetration(self, energy_transfer, target_material):
        """Calculate penetration depth based on energy and material"""
        material_resistance = {
            "metal": 0.7,
            "shield": 0.3,
            "core": 0.5,
            "engine": 0.8
        }
        resistance = material_resistance.get(target_material, 0.7)
        
        return (energy_transfer * self.damage_profile["penetration"]) / resistance
        
    def _calculate_damage(self, energy_transfer, penetration):
        """Calculate final damage based on energy transfer and penetration"""
        base_damage = self.damage_profile["impact"]
        energy_factor = energy_transfer / self.energy  # Normalize to 0-1
        penetration_factor = min(1, penetration)  # Cap at 1
        
        return base_damage * energy_factor * (1 + penetration_factor)
    
    def draw(self):
        glPushMatrix()
        glTranslatef(*self.pos)
        glColor3f(1, 1, 0)  # Default color - should be overridden by subclasses
        glPointSize(5.0)
        glBegin(GL_POINTS)
        glVertex3f(0, 0, 0)
        glEnd()
        glPopMatrix()

class PlayerProjectile(Projectile):
    def __init__(self, pos, direction, speed=30.0):
        damage_profile = {
            "impact": 25,
            "penetration": 0.7,
            "splash": 0,
            "energy_transfer": 0.9
        }
        super().__init__(pos, direction, speed, damage_profile)
        
    def draw(self):
        glPushMatrix()
        glTranslatef(*self.pos)
        glColor3f(1, 1, 0)  # Yellow for player projectiles
        glPointSize(5.0)
        glBegin(GL_POINTS)
        glVertex3f(0, 0, 0)
        glEnd()
        glPopMatrix()

class EnemyProjectile(Projectile):
    def __init__(self, pos, direction, speed=20.0):
        damage_profile = {
            "impact": 15,
            "penetration": 0.4,
            "splash": 0.5,
            "energy_transfer": 0.6
        }
        super().__init__(pos, direction, speed, damage_profile)
        
    def draw(self):
        glPushMatrix()
        glTranslatef(*self.pos)
        glColor3f(1, 0, 0)  # Red for enemy projectiles
        glPointSize(5.0)
        glBegin(GL_POINTS)
        glVertex3f(0, 0, 0)
        glEnd()
        glPopMatrix() 