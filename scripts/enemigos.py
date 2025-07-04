#FELIX ANTONIO MERCEDES MERCEDES
#21-EISN-2-047
import pygame
import math
import random
import os
from .configuracion import *
from .arboldecomportamiento import *
from .personajes import IndicadorDano

class Enemigo(pygame.sprite.Sprite):
    """Clase para los enemigos del juego"""
    def __init__(self, x, y, carpeta_enemigo_movimiento, vida=50, rango_vision=ENEMY_DETECTION_RANGE):
        super().__init__()
        self.carpeta_enemigo = carpeta_enemigo_movimiento
        self.num_columnas = 4
        self.num_filas = 1
        
        self.directions_order = ["up", "down", "left", "right"]
        self.direction_filenames = {
            "up": "arriba.png",
            "down": "abajo.png",
            "left": "izquierda.png",
            "right": "derecha.png"
        }
        
        self.animation_frames = self._cargar_frames_enemigo()
        
        self.direction = "down"
        self.current_frame = 0
        self.image = self.animation_frames.get(self.direction, [pygame.Surface((SCALED_TILE_SIZE, SCALED_TILE_SIZE), pygame.SRCALPHA)])[
            self.current_frame % len(self.animation_frames.get(self.direction, [pygame.Surface((SCALED_TILE_SIZE, SCALED_TILE_SIZE), pygame.SRCALPHA)]))]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.velocidad = VELOCIDAD_GENERAL
        self.vida = vida
        self.max_vida = vida
        self.rango_vision = rango_vision
        self.path = []
        self.ultimo_path_calculado = pygame.time.get_ticks()
        self.intervalo_calculo_path = 500
        self.ultimo_ataque_cuerpo_a_cuerpo = pygame.time.get_ticks()
        self.tiempo_entre_ataques_cuerpo_a_cuerpo = ENEMY_MELEE_COOLDOWN

        self.ultima_actualizacion_frame = pygame.time.get_ticks()
        self.velocidad_animacion = 150

        #creamos una variables para el patrullaje de los enemigos
        self.patrol_points = []
        self.current_patrol_index = 0
        self.last_patrol_point_reached_time = 0
        self.patrol_wait_time = 1500
        self.target_player_on_hit = False

        self.generar_patrol_points(x, y)
        
        self.tipo_enemigo = os.path.basename(carpeta_enemigo_movimiento)

        #configuracion para el arbol de comportamiento de los enemigos
        self.behavior_tree = self._build_behavior_tree()

    def _build_behavior_tree(self):
        """Construir el árbol de comportamiento del enemigo"""
        root = Selector("Enemy Behavior")
        #ya que el objetivo del jugador es tomar la copa los enemigos tienen como prioridad defender la copa
        defend_branch = Sequence("Defend Branch")
        defend_branch.add_child(EnemigoRecibioDano("Condition: Received Damage"))
        defend_branch.add_child(PerseguirYAtacar("Action: Pursue and Attack (Defend)"))
        root.add_child(defend_branch)

        #atacar (prioridad media)
        attack_branch = Sequence("Attack Branch")
        attack_branch.add_child(JugadorEnRangoVision("Condition: Player in Range"))
        attack_branch.add_child(PerseguirYAtacar("Action: Pursue and Attack"))
        root.add_child(attack_branch)

        patrol_branch = Sequence("Patrol Branch")
        patrol_branch.add_child(JugadorFueraRangoVision("Condition: Player Out of Range"))
        
        patrol_selector = Selector("Patrol Selector")
        patrol_selector.add_child(PatrullarAlrededorCopa("Action: Patrol Around Trophy"))
        patrol_selector.add_child(Patrullar("Action: General Patrol"))
        
        patrol_branch.add_child(patrol_selector)
        root.add_child(patrol_branch)

        return root

    def _cargar_frames_enemigo(self):
        """Cargar los frames de animación del enemigo"""
        frames_dict = {direction: [] for direction in self.directions_order}
        for direction_name in self.directions_order:
            filename = self.direction_filenames[direction_name]
            ruta_completa_imagen = os.path.join(CARPETA_MOVIMIENTO_ENEMIGOS, self.carpeta_enemigo, filename)
            try:
                sprite_sheet_individual = pygame.image.load(ruta_completa_imagen).convert_alpha()
                ancho_sheet = sprite_sheet_individual.get_width()
                alto_sheet = sprite_sheet_individual.get_height()
                
                ancho_frame = ancho_sheet // self.num_columnas
                alto_frame = alto_sheet // self.num_filas
                
                for col_index in range(self.num_columnas):
                    x_pos = col_index * ancho_frame
                    frame = sprite_sheet_individual.subsurface((x_pos, 0, ancho_frame, alto_frame))
                    frame = pygame.transform.scale(frame, (SCALED_TILE_SIZE, SCALED_TILE_SIZE))
                    frames_dict[direction_name].append(frame)
            except pygame.error as e:
                for _ in range(self.num_columnas):
                    frame = pygame.Surface((SCALED_TILE_SIZE, SCALED_TILE_SIZE), pygame.SRCALPHA)
                    frames_dict[direction_name].append(frame)
        return frames_dict

    def generar_patrol_points(self, start_x, start_y, num_points=3, patrol_radius=200):
        """Generar puntos de patrullaje aleatorios"""
        self.patrol_points = []
        start_grid_x = start_x // TILE_SIZE
        start_grid_y = start_y // TILE_SIZE

        start_grid_x = max(0, min(GRID_ANCHO - 1, start_grid_x))
        start_grid_y = max(0, min(GRID_ALTO - 1, start_grid_y))

        self.patrol_points.append((start_grid_x, start_grid_y))

        for _ in range(num_points - 1):
            attempts = 0
            while attempts < 20:
                angle = random.uniform(0, 2 * math.pi)
                radius = random.uniform(0, patrol_radius)
                target_x_pixel = start_x + radius * math.cos(angle)
                target_y_pixel = start_y + radius * math.sin(angle)
