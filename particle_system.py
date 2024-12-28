import random
import time
from OpenGL.GL import *
import numpy as np

class Particle:
    def __init__(self, pos, velocity, lifetime, color, size=2.0):
        self.pos = list(pos)
        self.velocity = list(velocity)
        self.lifetime = lifetime
        self.birth_time = time.time()
        self.color = color
        self.size = size
        self.gravity = -9.8

    def update(self, dt):
        self.pos[0] += self.velocity[0] * dt
        self.pos[1] += self.velocity[1] * dt + 0.5 * self.gravity * dt * dt
        self.pos[2] += self.velocity[2] * dt
        self.velocity[1] += self.gravity * dt

    def is_alive(self):
        return time.time() - self.birth_time < self.lifetime

    def draw(self):
        glPushMatrix()
        glTranslatef(*self.pos)
        glColor4f(*self.color)
        glPointSize(self.size)
        glBegin(GL_POINTS)
        glVertex3f(0, 0, 0)
        glEnd()
        glPopMatrix()

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit_explosion(self, pos, count=20):
        for _ in range(count):
            speed = random.uniform(5, 10)
            direction = [
                random.uniform(-1, 1),
                random.uniform(-1, 1),
                random.uniform(-1, 1)
            ]
            # Normalize direction
            length = np.sqrt(sum(x*x for x in direction))
            velocity = [d * speed / length for d in direction]
            
            color = (1, random.uniform(0, 0.5), 0, 1)  # Red-orange explosion
            self.particles.append(Particle(pos, velocity, random.uniform(0.3, 0.7), color, 3.0))

    def emit_hit(self, pos, count=10):
        for _ in range(count):
            velocity = [
                random.uniform(-3, 3),
                random.uniform(2, 5),
                random.uniform(-3, 3)
            ]
            color = (1, 1, 0, 1)  # Yellow spark
            self.particles.append(Particle(pos, velocity, random.uniform(0.2, 0.4), color, 2.0))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.is_alive()]
        for particle in self.particles:
            particle.update(dt)

    def draw(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for particle in self.particles:
            particle.draw()
        glDisable(GL_BLEND) 