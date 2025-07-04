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

    def update(self):
        """Método de actualización del obstáculo"""
        pass

    def recibir_daño(self, daño):
        """Método para que el obstáculo reciba daño"""
        if self.tipo == "destructible":
            self.vida -= daño
            if self.vida <= 0:
                self.kill()
                #actualizacion del grid para cuando se destruya un obstaculo
                
                x_grid_start = self.rect.x // TILE_SIZE
                y_grid_start = self.rect.y // TILE_SIZE
                x_grid_end = (self.rect.right - 1) // TILE_SIZE
                y_grid_end = (self.rect.bottom - 1) // TILE_SIZE

                for i in range(x_grid_start, x_grid_end + 1):
                    for j in range(y_grid_start, y_grid_end + 1):
                        if 0 <= i < GRID_ANCHO and 0 <= j < GRID_ALTO:
                            grid_mapa_actual[i][j] = 0

class Jugador(pygame.sprite.Sprite):
    """Clase principal del jugador"""
    def __init__(self, x, y, sprite_sheet_movimiento, personaje_elegido_img, usar_nuevo_sistema=False, carpeta_movimiento=""):
        super().__init__()
        self.personaje_elegido_img = personaje_elegido_img
        self.usar_nuevo_sistema = usar_nuevo_sistema

        if self.usar_nuevo_sistema:
            carpeta_personaje = os.path.join(CARPETA_MOVIMIENTO, carpeta_movimiento)
            self.sprites_direccion = {
                "up": cargar_imagen(carpeta_personaje, "arriba.png"),
                "down": cargar_imagen(carpeta_personaje, "abajo.png"),
                "left": cargar_imagen(carpeta_personaje, "izquierda.png"),
                "right": cargar_imagen(carpeta_personaje, "derecha.png")
            }
            self.animation_frames = self.cargar_frames_separados()
        else:
            self.sprite_sheet = sprite_sheet_movimiento
            self.num_columnas = 4
            self.num_filas = 4
            self.directions_order = ["down", "left", "right", "up"]
            self.animation_frames = self.cargar_frames_por_direccion(self.sprite_sheet, self.num_columnas, self.num_filas)

        self.direction = "down"
        self.current_frame = 0
        self.image = self.animation_frames.get(self.direction, [pygame.Surface((SCALED_TILE_SIZE, SCALED_TILE_SIZE), pygame.SRCALPHA)])[
            self.current_frame]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.velocidad = VELOCIDAD_GENERAL
        
        #utilizamos una imagen de un corazon para simular la vida del jugador
        self.max_corazones = 5
        self.corazones = self.max_corazones
        self.vida_por_corazon = 100
        self.vida_actual_corazon = self.vida_por_corazon
        
    
        self.ultima_actualizacion_frame = pygame.time.get_ticks()
        self.velocidad_animacion = 100

        self.ultima_colision_tiempo = 0
        self.es_invulnerable = False
        self.direccion_disparo = (1, 0)
        self.ultimo_disparo = 0
        self.tiempo_entre_disparos = 300
        self.target_enemy_pos = None

        #powerups
        self.invulnerable_powerup_activo = False
        self.tiempo_inicio_invulnerabilidad_powerup = 0
        self.duracion_invulnerabilidad_powerup = 5000

        self.bonus_x2_activo = False
        self.tiempo_inicio_bonus_x2 = 0
        self.duracion_bonus_x2 = 5000

        #nombre y puntuacion
        self.score = 0
        self.nombre = "Jugador"

        #configuracion de gamepad
        self.joystick = None
        self.joystick_threshold = 0.2
        self.joystick_shoot_threshold = 0.5

    def cargar_frames_separados(self):
        """Cargar frames de animación desde archivos separados"""
        frames_dict = {"up": [], "down": [], "left": [], "right": []}
        for direccion, sprite_sheet in self.sprites_direccion.items():
            if sprite_sheet:
                ancho_sheet = sprite_sheet.get_width()
                alto_sheet = sprite_sheet.get_height()
                ancho_frame = ancho_sheet // 4
                alto_frame = alto_sheet
                for i in range(4):
                    x_pos = i * ancho_frame
                    if x_pos + ancho_frame <= ancho_sheet:
                        frame = sprite_sheet.subsurface((x_pos, 0, ancho_frame, alto_frame))
                        frame = pygame.transform.scale(frame, (SCALED_TILE_SIZE, SCALED_TILE_SIZE))
