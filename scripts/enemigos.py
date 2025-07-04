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
                grid_x = int(target_x_pixel // TILE_SIZE)
                grid_y = int(target_y_pixel // TILE_SIZE)

                if (0 <= grid_x < GRID_ANCHO and 0 <= grid_y < GRID_ALTO and
                        grid_mapa_actual[grid_x][grid_y] == 0):
                    self.patrol_points.append((grid_x, grid_y))
                    break
                attempts += 1

        if not self.patrol_points:
            self.patrol_points.append((start_grid_x, start_grid_y))

        self.current_patrol_index = 0
        self.path = []

    def update(self, jugador, game_state, copa_pos=None):
        """Método principal de actualización del enemigo"""
        distancia_al_jugador = math.sqrt(
            (self.rect.centerx - jugador.rect.centerx) ** 2 + (self.rect.centery - jugador.rect.centery) ** 2)
        if distancia_al_jugador > self.rango_vision * 1.5: 
            self.target_player_on_hit = False

        #ejecutar el arbol de comportamiento
        self.behavior_tree.tick(self, jugador, game_state, copa_pos)

        self._animar()
        self._colision_con_otros_enemigos(game_state['grupo_enemigos'])

    def recibir_daño(self, daño):
        """Método para que el enemigo reciba daño"""
        self.vida -= daño
        if self.vida < 0:
            self.vida = 0
        display_damage = min(daño, 15)
        grupo_indicadores_daño.add(IndicadorDano(self.rect.centerx, self.rect.top, display_damage))
        self.target_player_on_hit = True  

    def mover_a_siguiente_paso(self, game_state):
        """Mover el enemigo al siguiente paso en su camino"""
        if self.path:
            target_grid_x, target_grid_y = self.path[0]

            target_pixel_x = target_grid_x * TILE_SIZE + TILE_SIZE // 2
            target_pixel_y = target_grid_y * TILE_SIZE + TILE_SIZE // 2

            dx = target_pixel_x - self.rect.centerx
            dy = target_pixel_y - self.rect.centery

            if abs(dx) < self.velocidad and abs(dy) < self.velocidad:
                self.rect.centerx = target_pixel_x
                self.rect.centery = target_pixel_y
                self.path.pop(0)
                if not self.path:
                    dx, dy = 0, 0
                    self.current_frame = 0
            else:
                dist = math.sqrt(dx ** 2 + dy ** 2)
                if dist > 0:
                    dx = (dx / dist) * self.velocidad
                    dy = (dy / dist) * self.velocidad

                if abs(dx) > abs(dy):
                    self.direction = "right" if dx > 0 else "left"
                elif abs(dy) > 0:
                    self.direction = "down" if dy > 0 else "up"

                self.rect.x += dx
                self.rect.y += dy

                self._colision_obstaculos_enemigo(dx, dy, game_state['grupo_obstaculos'])
        else:
            self.current_frame = 0
            self.ultimo_path_calculado = pygame.time.get_ticks()

    def _colision_obstaculos_enemigo(self, dx, dy, grupo_obstaculos):
        """Manejo de colisiones del enemigo con obstáculos"""
        original_x = self.rect.x
        self.rect.x += dx
        colision_x = False
        for obstaculo in grupo_obstaculos:
            if obstaculo.tipo in ["solido", "destructible"] and self.rect.colliderect(obstaculo.rect):
                if dx > 0:
                    self.rect.right = obstaculo.rect.left
                elif dx < 0:
                    self.rect.left = obstaculo.rect.right
                colision_x = True
                break
        self.rect.x = original_x

        original_y = self.rect.y
        self.rect.y += dy
        colision_y = False
        for obstaculo in grupo_obstaculos:
            if obstaculo.tipo in ["solido", "destructible"] and self.rect.colliderect(obstaculo.rect):
                if dy > 0:
                    self.rect.bottom = obstaculo.rect.top
                elif dy < 0:
                    self.rect.top = obstaculo.rect.bottom
                colision_y = True
                break
        self.rect.y = original_y

        if colision_x:
            self.rect.x += dx
            self.path = []
        if colision_y:
            self.rect.y += dy
            self.path = []

    def _colision_con_otros_enemigos(self, grupo_enemigos):
        #manejo de coliciones entre enemigos
        for otro_enemigo in grupo_enemigos:
            if otro_enemigo != self and self.rect.colliderect(otro_enemigo.rect):
            
                if self.rect.centerx < otro_enemigo.rect.centerx:
                    self.rect.x -= 1
                else:
                    self.rect.x += 1
                if self.rect.centery < otro_enemigo.rect.centery:
                    self.rect.y -= 1
                else:
                    self.rect.y += 1

    def _animar(self):
        """Animar el sprite del enemigo"""
        ahora = pygame.time.get_ticks()
        if ahora - self.ultima_actualizacion_frame > self.velocidad_animacion:
            self.ultima_actualizacion_frame = ahora
            if self.direction in self.animation_frames and self.animation_frames[self.direction]:
                self.current_frame = (self.current_frame + 1) % len(self.animation_frames[self.direction])
                self.image = self.animation_frames[self.direction][self.current_frame]

    def draw_health_bar(self, screen, offset_x, offset_y):
        """Dibujar la barra de vida del enemigo"""
        bar_width = self.rect.width
        bar_height = 5
        bar_x = self.rect.x - offset_x
        bar_y = self.rect.y - offset_y - 10

        pygame.draw.rect(screen, ROJO, (bar_x, bar_y, bar_width, bar_height))
        current_health_width = (self.vida / self.max_vida) * bar_width
        pygame.draw.rect(screen, VERDE, (bar_x, bar_y, current_health_width, bar_height))

class Torreta(pygame.sprite.Sprite):
    """Clase para las torretas enemigas"""
    def __init__(self, x, y, vida=75, rango_vision=TURRET_DETECTION_RANGE):
        super().__init__()
        self.sprite_sheet = ASSETS['torreta_sprite_sheet']
        self.num_columnas = 8
        self.num_filas = 1
        self.frames = self._cargar_frames_torreta()
        self.current_frame = 0
        self.image = self.frames[self.current_frame]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vida = vida
        self.max_vida = vida
        self.rango_vision = rango_vision
        self.ultimo_disparo = pygame.time.get_ticks()
        self.tiempo_entre_disparos = TURRET_SHOOT_COOLDOWN
        self.tipo_enemigo = "enemigo5"

    def _cargar_frames_torreta(self):
        """Cargar los frames de animación de la torreta"""
        frames_list = []
        if self.sprite_sheet:
            ancho_sheet = self.sprite_sheet.get_width()
            alto_sheet = self.sprite_sheet.get_height()
            ancho_frame = ancho_sheet // self.num_columnas
            alto_frame = alto_sheet // self.num_filas
            
            for col_index in range(self.num_columnas):
                x_pos = col_index * ancho_frame
                frame = self.sprite_sheet.subsurface((x_pos, 0, ancho_frame, alto_frame))
                frame = pygame.transform.scale(frame, (SCALED_TILE_SIZE, SCALED_TILE_SIZE))
                frames_list.append(frame)
        else:
            for _ in range(self.num_columnas):
                frame = pygame.Surface((SCALED_TILE_SIZE, SCALED_TILE_SIZE), pygame.SRCALPHA)
                frames_list.append(frame)
        return frames_list

    def update(self, jugador, game_state):
        """Actualizar la torreta"""
        if jugador is None:
            return

        distancia_al_jugador = math.sqrt(
            (self.rect.centerx - jugador.rect.centerx) ** 2 + (self.rect.centery - jugador.rect.centery) ** 2)
        ahora = pygame.time.get_ticks()

        if distancia_al_jugador < self.rango_vision:
            #calculamos el angulo hacia el jugador (el angulo se mide en grados)
            dx = jugador.rect.centerx - self.rect.centerx
            dy = jugador.rect.centery - self.rect.centery
            angle = math.degrees(math.atan2(-dy, dx)) 

            angle = (angle + 360 + 22.5) % 360  
            self.current_frame = int(angle // 45)
            self.image = self.frames[self.current_frame]

            if ahora - self.ultimo_disparo > self.tiempo_entre_disparos:
                self.ultimo_disparo = ahora
                direccion_disparo = (dx / distancia_al_jugador, dy / distancia_al_jugador)
                from .personajes import Bala 
                bala = Bala(self.rect.centerx, self.rect.centery, direccion_disparo, es_jugador=False)
                game_state['grupo_balas_enemigo'].add(bala)

    def recibir_daño(self, daño):
        """Método para que la torreta reciba daño"""
        self.vida -= daño
        if self.vida < 0:
            self.vida = 0
        display_damage = min(daño, 15)
        grupo_indicadores_daño.add(IndicadorDano(self.rect.centerx, self.rect.top, display_damage))

    def draw_health_bar(self, screen, offset_x, offset_y):
        """Dibujar la barra de vida de la torreta"""
        bar_width = self.rect.width
        bar_height = 5
        bar_x = self.rect.x - offset_x
        bar_y = self.rect.y - offset_y - 10

        pygame.draw.rect(screen, ROJO, (bar_x, bar_y, bar_width, bar_height))
        current_health_width = (self.vida / self.max_vida) * bar_width
        pygame.draw.rect(screen, VERDE, (bar_x, bar_y, current_health_width, bar_height))