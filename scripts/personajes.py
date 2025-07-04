#FELIX ANTONIO MERCEDES MERCEDES
#21-EISN-2-047
import pygame
import math
import random
import os
from .configuracion import *

class Obstaculo(pygame.sprite.Sprite):
    """Clase para los obstáculos del juego"""
    def __init__(self, x, y, ancho, alto, color=None, tipo="solido", imagen=None, vida=None):
        super().__init__()
        self.tipo = tipo

        if tipo == "destructible":
            self.vida = vida if vida is not None else 50
        else:
            self.vida = -1

        self.original_image = None
        self.gira = False

        if imagen:
            self.original_image = pygame.transform.scale(imagen, (ancho, alto))
            self.image = self.original_image
        elif color:
            self.image = pygame.Surface((ancho, alto))
            self.image.fill(color)
            self.original_image = self.image.copy()
        else:
            if self.tipo == "solido":
                if ASSETS.get('piedra'):
                    self.original_image = pygame.transform.scale(ASSETS['piedra'], (ancho, alto))
                    self.image = self.original_image
                else:
                    self.image = pygame.Surface((ancho, alto))
                    self.image.fill(CYAN)
                    self.original_image = self.image.copy()
            elif self.tipo == "destructible" or self.tipo == "peligro":
                self.image = pygame.Surface((ancho, alto), pygame.SRCALPHA)
                self.original_image = self.image.copy()
            else:
                self.image = pygame.Surface((ancho, alto), pygame.SRCALPHA)
                self.original_image = self.image.copy()

        self.angulo = 0
        self.velocidad_rotacion = 5
        self.rect = self.image.get_rect(topleft=(x, y))

