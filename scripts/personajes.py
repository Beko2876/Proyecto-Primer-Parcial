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
                        frames_dict[direccion].append(frame)
                    else:
                        frame_default = pygame.Surface((SCALED_TILE_SIZE, SCALED_TILE_SIZE), pygame.SRCALPHA)
                        frames_dict[direccion].append(frame_default)
            else:
                for i in range(4):
                    frame_default = pygame.Surface((SCALED_TILE_SIZE, SCALED_TILE_SIZE), pygame.SRCALPHA)
                    frames_dict[direccion].append(frame_default)
        return frames_dict

    def cargar_frames_por_direccion(self, sprite_sheet, num_columnas, num_filas):
        """Cargar frames de animación desde un sprite sheet"""
        frames_dict = {direction: [] for direction in self.directions_order}
        if sprite_sheet:
            ancho_sheet = sprite_sheet.get_width()
            alto_sheet = sprite_sheet.get_height()
            if num_columnas == 0 or num_filas == 0:
                return {direction: [pygame.Surface((SCALED_TILE_SIZE, SCALED_TILE_SIZE), pygame.SRCALPHA)] for direction in
                        self.directions_order}
            ancho_frame_original = ancho_sheet // num_columnas
            alto_frame_original = alto_sheet // num_filas
            
            for row_index, direction_name in enumerate(self.directions_order):
                y_pos = row_index * alto_frame_original
                for col_index in range(num_columnas):
                    x_pos = col_index * ancho_frame_original
                    if x_pos + ancho_frame_original <= ancho_sheet and y_pos + alto_frame_original <= alto_sheet:
                        frame = sprite_sheet.subsurface((x_pos, y_pos, ancho_frame_original, alto_frame_original))
                        frame = pygame.transform.scale(frame, (SCALED_TILE_SIZE, SCALED_TILE_SIZE))
                        frames_dict[direction_name].append(frame)
                    else:
                        frames_dict[direction_name].append(
                            pygame.Surface((SCALED_TILE_SIZE, SCALED_TILE_SIZE), pygame.SRCALPHA))
            return frames_dict
        default_surface = pygame.Surface((SCALED_TILE_SIZE, SCALED_TILE_SIZE), pygame.SRCALPHA)
        return {direction: [default_surface] for direction in self.directions_order}

    def update(self, grupo_obstaculos, grupo_enemigos_param, offset_x, offset_y):
        """Método principal de actualización del jugador"""
        dx, dy = 0, 0
        keys = pygame.key.get_pressed()
        ahora = pygame.time.get_ticks()
        moving = False

        #aparte del gamepad tambien usaremos el teclado para que una mejor jugabilidad en el juego en caso de que el jugador no desee jugar con un
        #gamepad
        if keys[pygame.K_LEFT] and keys[pygame.K_UP]:
            dx = -self.velocidad
            dy = -self.velocidad
            self.direccion_disparo = (-1, -1)
            self.direction = "up"
            moving = True
        elif keys[pygame.K_LEFT] and keys[pygame.K_DOWN]:
            dx = -self.velocidad
            dy = self.velocidad
            self.direccion_disparo = (-1, 1)
            self.direction = "down"
            moving = True
        elif keys[pygame.K_RIGHT] and keys[pygame.K_UP]:
            dx = self.velocidad
            dy = -self.velocidad
            self.direccion_disparo = (1, -1)
            self.direction = "up"
            moving = True
        elif keys[pygame.K_RIGHT] and keys[pygame.K_DOWN]:
            dx = self.velocidad
            dy = self.velocidad
            self.direccion_disparo = (1, 1)
            self.direction = "down"
            moving = True
        elif keys[pygame.K_LEFT]:
            dx = -self.velocidad
            self.direccion_disparo = (-1, 0)
            self.direction = "left"
            moving = True
        elif keys[pygame.K_RIGHT]:
            dx = self.velocidad
            self.direccion_disparo = (1, 0)
            self.direction = "right"
            moving = True
        elif keys[pygame.K_UP]:
            dy = -self.velocidad
            self.direccion_disparo = (0, -1)
            self.direction = "up"
            moving = True
        elif keys[pygame.K_DOWN]:
            dy = self.velocidad
            self.direccion_disparo = (0, 1)
            self.direction = "down"
            moving = True

        #manejo de gamepad
        if pygame.joystick.get_count() > 0:
            if self.joystick is None:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()

            axis_x = self.joystick.get_axis(0)
            axis_y = self.joystick.get_axis(1)
            
            trigger_right = self.joystick.get_axis(5)

            if abs(axis_x) > self.joystick_threshold or abs(axis_y) > self.joystick_threshold:
                dx = axis_x * self.velocidad
                dy = axis_y * self.velocidad
                moving = True

                if abs(axis_x) > abs(axis_y):
                    self.direction = "right" if axis_x > 0 else "left"
                else:
                    self.direction = "down" if axis_y > 0 else "up"
                
                mag = math.sqrt(axis_x**2 + axis_y**2)
                if mag > 0:
                    self.direccion_disparo = (axis_x / mag, axis_y / mag)
                else:
                    self.direccion_disparo = (0, 0)

            if trigger_right > self.joystick_shoot_threshold:
                bala = self.disparar(grupo_enemigos_param)
                if bala:
                    grupo_balas_jugador.add(bala)

        if self.direccion_disparo[0] != 0 or self.direccion_disparo[1] != 0:
            mag = (self.direccion_disparo[0] ** 2 + self.direccion_disparo[1] ** 2) ** 0.5
            if mag > 0:
                self.direccion_disparo = (self.direccion_disparo[0] / mag, self.direccion_disparo[1] / mag)

        self.rect.x += dx
        self.rect.y += dy

        #coliciones contra obstaculos
        self.colision_obstaculos(dx, 0, grupo_obstaculos)
        self.colision_obstaculos(0, dy, grupo_obstaculos)

        #coliciones entre jugador y enemigos
        for enemy in grupo_enemigos_param:
            if enemy != self and self.rect.colliderect(enemy.rect):
                if self.rect.centerx < enemy.rect.centerx:
                    self.rect.x -= 1
                else:
                    self.rect.x += 1
                if self.rect.centery < enemy.rect.centery:
                    self.rect.y -= 1
                else:
                    self.rect.y += 1

        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(WORLD_WIDTH, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(WORLD_HEIGHT, self.rect.bottom)

        if self.es_invulnerable:
            if ahora - self.ultima_colision_tiempo > PLAYER_INVULNERABILITY_DURATION:
                self.es_invulnerable = False
        
        if self.invulnerable_powerup_activo:
            if ahora - self.tiempo_inicio_invulnerabilidad_powerup > self.duracion_invulnerabilidad_powerup:
                self.invulnerable_powerup_activo = False

        if self.bonus_x2_activo:
            if ahora - self.tiempo_inicio_bonus_x2 > self.duracion_bonus_x2:
                self.bonus_x2_activo = False

        if moving:
            if ahora - self.ultima_actualizacion_frame > self.velocidad_animacion:
                self.ultima_actualizacion_frame = ahora
                if self.direction in self.animation_frames and self.animation_frames[self.direction]:
                    self.current_frame = (self.current_frame + 1) % len(self.animation_frames[self.direction])
                    self.image = self.animation_frames[self.direction][self.current_frame]
        else:
            self.current_frame = 0
            if self.direction in self.animation_frames and self.animation_frames[self.direction]:
                self.image = self.animation_frames[self.direction][self.current_frame]

        #calculamos la distancia del enemigo mas cercano para usar una pequeña asistencia de aim
        self.target_enemy_pos = None
        closest_enemy_dist_sq = AIM_ASSIST_RANGE ** 2

        all_enemies = list(grupo_enemigos) + list(grupo_torretas)
        for enemy in all_enemies:
            dist_x = enemy.rect.centerx - self.rect.centerx
            dist_y = enemy.rect.centery - self.rect.centery
            dist_sq = dist_x ** 2 + dist_y ** 2

            if dist_sq < closest_enemy_dist_sq:
                closest_enemy_dist_sq = dist_sq
                self.target_enemy_pos = enemy.rect.center

    def recibir_daño(self, daño):
        """Método para que el jugador reciba daño"""
        if self.invulnerable_powerup_activo:
            return
        if self.es_invulnerable:
            return

        self.vida_actual_corazon -= daño
        if self.vida_actual_corazon <= 0:
            self.corazones -= 1
            if self.corazones > 0:
                self.vida_actual_corazon = self.vida_por_corazon
            else:
                self.vida_actual_corazon = 0
        
        #creamos un indicador de daño para el jugador estilo free fire
        grupo_indicadores_daño_jugador.add(IndicadorDanoJugador(self.rect.centerx, self.rect.top, daño))

        self.es_invulnerable = True
        self.ultima_colision_tiempo = pygame.time.get_ticks()

    def colision_obstaculos(self, dx, dy, grupo_obstaculos):
        """Manejo de colisiones con obstáculos"""
        for obstaculo in grupo_obstaculos:
            if obstaculo.tipo in ["solido", "destructible"] and self.rect.colliderect(obstaculo.rect):
                if dx > 0:
                    self.rect.right = obstaculo.rect.left
                if dx < 0:
                    self.rect.left = obstaculo.rect.right
                if dy > 0:
                    self.rect.bottom = obstaculo.rect.top
                if dy < 0:
                    self.rect.top = obstaculo.rect.bottom
            elif obstaculo.tipo == "peligro" and self.rect.colliderect(obstaculo.rect):
                self.recibir_daño(OBSTACLE_DAMAGE)

    def disparar(self, grupo_enemigos_param):
        """Método para que el jugador dispare"""
        ahora = pygame.time.get_ticks()
        if ahora - self.ultimo_disparo > self.tiempo_entre_disparos:
            self.ultimo_disparo = ahora

            self.target_enemy_pos = None
            closest_enemy_dist_sq = AIM_ASSIST_RANGE ** 2

            all_enemies = list(grupo_enemigos_param) + list(grupo_torretas)
            for enemy in all_enemies:
                dist_x = enemy.rect.centerx - self.rect.centerx
                dist_y = enemy.rect.centery - self.rect.centery
                dist_sq = dist_x ** 2 + dist_y ** 2

                if dist_sq < closest_enemy_dist_sq:
                    closest_enemy_dist_sq = dist_sq
                    self.target_enemy_pos = enemy.rect.center

            direccion_final_disparo = self.direccion_disparo 

            if self.target_enemy_pos:
                target_dx = self.target_enemy_pos[0] - self.rect.centerx
                target_dy = self.target_enemy_pos[1] - self.rect.centery
                mag = math.sqrt(target_dx ** 2 + target_dy ** 2)
                if mag > 0:
                    direccion_final_disparo = (target_dx / mag, target_dy / mag)

            damage_to_deal = random.randint(BULLET_DAMAGE_MIN, BULLET_DAMAGE_MAX)
            damage_to_deal = damage_to_deal * 2 if self.bonus_x2_activo else damage_to_deal
            return Bala(self.rect.centerx, self.rect.centery, direccion_final_disparo, es_jugador=True, daño=damage_to_deal)
        return None

    def draw_aim_assist(self, screen):
        pass

    def activar_invulnerabilidad(self):
        """Activar el power-up de invulnerabilidad"""
        self.invulnerable_powerup_activo = True
        self.tiempo_inicio_invulnerabilidad_powerup = pygame.time.get_ticks()

    def activar_bonus_x2(self):
        """Activar el power-up de daño doble"""
        self.bonus_x2_activo = True
        self.tiempo_inicio_bonus_x2 = pygame.time.get_ticks()

    def aumentar_corazon(self):
        """Aumentar un corazón de vida"""
        if self.corazones < self.max_corazones:
            self.corazones += 1
            self.vida_actual_corazon = self.vida_por_corazon

class Bala(pygame.sprite.Sprite):
    """Clase para las balas del juego"""
    def __init__(self, x, y, direccion, es_jugador=True, daño=None):
        super().__init__()
        self.original_image = pygame.Surface((10, 5), pygame.SRCALPHA)
        self.original_image.fill(ROJO if es_jugador else AMARILLO)
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))

        self.speed = BULLET_SPEED if es_jugador else ENEMY_BULLET_SPEED
        self.dx = direccion[0] * self.speed
        self.dy = direccion[1] * self.speed

        self.daño = daño if daño is not None else (random.randint(BULLET_DAMAGE_MIN, BULLET_DAMAGE_MAX) if es_jugador else ENEMY_BULLET_DAMAGE)
        self.distancia_recorrida = 0
        self.alcance_maximo = 400
        self.es_jugador = es_jugador

        #rotamos la pantalla segun la direccion del jugador
        if self.dx == 0 and self.dy == 0:
            angle = 0
        else:
            angle = math.degrees(math.atan2(-self.dy, self.dx))
        self.image = pygame.transform.rotate(self.original_image, angle)
        self.rect = self.image.get_rect(center=self.rect.center)

    def update(self, offset_x, offset_y):
        """Actualizar la posición de la bala"""
        self.rect.x += self.dx
        self.rect.y += self.dy
        self.distancia_recorrida += math.sqrt(self.dx ** 2 + self.dy ** 2)

        #eliminamos las balas del jugador que se salen de los limines establecidos
        if (self.rect.left > WORLD_WIDTH or self.rect.right < 0 or
                self.rect.top > WORLD_HEIGHT or self.rect.bottom < 0 or
                self.distancia_recorrida > self.alcance_maximo):
            self.kill()


        #coliciones contra obstaculos
        self.colision_obstaculos(dx, 0, grupo_obstaculos)
        self.colision_obstaculos(0, dy, grupo_obstaculos)

        #coliciones entre jugador y enemigos
        for enemy in grupo_enemigos_param:
            if enemy != self and self.rect.colliderect(enemy.rect):
                if self.rect.centerx < enemy.rect.centerx:
                    self.rect.x -= 1
                else:
                    self.rect.x += 1
                if self.rect.centery < enemy.rect.centery:
                    self.rect.y -= 1
                else:
                    self.rect.y += 1

        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(WORLD_WIDTH, self.rect.right)
        self.rect.top = max(0, self.rect.top)
        self.rect.bottom = min(WORLD_HEIGHT, self.rect.bottom)

        if self.es_invulnerable:
            if ahora - self.ultima_colision_tiempo > PLAYER_INVULNERABILITY_DURATION:
                self.es_invulnerable = False
        
        if self.invulnerable_powerup_activo:
            if ahora - self.tiempo_inicio_invulnerabilidad_powerup > self.duracion_invulnerabilidad_powerup:
                self.invulnerable_powerup_activo = False

        if self.bonus_x2_activo:
            if ahora - self.tiempo_inicio_bonus_x2 > self.duracion_bonus_x2:
                self.bonus_x2_activo = False

        if moving:
            if ahora - self.ultima_actualizacion_frame > self.velocidad_animacion:
                self.ultima_actualizacion_frame = ahora
                if self.direction in self.animation_frames and self.animation_frames[self.direction]:
                    self.current_frame = (self.current_frame + 1) % len(self.animation_frames[self.direction])
                    self.image = self.animation_frames[self.direction][self.current_frame]
        else:
            self.current_frame = 0
            if self.direction in self.animation_frames and self.animation_frames[self.direction]:
                self.image = self.animation_frames[self.direction][self.current_frame]

        #calculamos la distancia del enemigo mas cercano para usar una pequeña asistencia de aim
        self.target_enemy_pos = None
        closest_enemy_dist_sq = AIM_ASSIST_RANGE ** 2

        all_enemies = list(grupo_enemigos) + list(grupo_torretas)
        for enemy in all_enemies:
            dist_x = enemy.rect.centerx - self.rect.centerx
            dist_y = enemy.rect.centery - self.rect.centery
            dist_sq = dist_x ** 2 + dist_y ** 2

            if dist_sq < closest_enemy_dist_sq:
                closest_enemy_dist_sq = dist_sq
                self.target_enemy_pos = enemy.rect.center

    def recibir_daño(self, daño):
        """Método para que el jugador reciba daño"""
        if self.invulnerable_powerup_activo:
            return
        if self.es_invulnerable:
            return

        self.vida_actual_corazon -= daño
        if self.vida_actual_corazon <= 0:
            self.corazones -= 1
            if self.corazones > 0:
                self.vida_actual_corazon = self.vida_por_corazon
            else:
                self.vida_actual_corazon = 0
        
        #creamos un indicador de daño para el jugador estilo free fire
        grupo_indicadores_daño_jugador.add(IndicadorDanoJugador(self.rect.centerx, self.rect.top, daño))

        self.es_invulnerable = True
        self.ultima_colision_tiempo = pygame.time.get_ticks()

    def colision_obstaculos(self, dx, dy, grupo_obstaculos):
        """Manejo de colisiones con obstáculos"""
        for obstaculo in grupo_obstaculos:
            if obstaculo.tipo in ["solido", "destructible"] and self.rect.colliderect(obstaculo.rect):
                if dx > 0:
                    self.rect.right = obstaculo.rect.left
                if dx < 0:
                    self.rect.left = obstaculo.rect.right
                if dy > 0:
                    self.rect.bottom = obstaculo.rect.top
                if dy < 0:
                    self.rect.top = obstaculo.rect.bottom
            elif obstaculo.tipo == "peligro" and self.rect.colliderect(obstaculo.rect):
                self.recibir_daño(OBSTACLE_DAMAGE)

    def disparar(self, grupo_enemigos_param):
        """Método para que el jugador dispare"""
        ahora = pygame.time.get_ticks()
        if ahora - self.ultimo_disparo > self.tiempo_entre_disparos:
            self.ultimo_disparo = ahora

            self.target_enemy_pos = None
            closest_enemy_dist_sq = AIM_ASSIST_RANGE ** 2

            all_enemies = list(grupo_enemigos_param) + list(grupo_torretas)
            for enemy in all_enemies:
                dist_x = enemy.rect.centerx - self.rect.centerx
                dist_y = enemy.rect.centery - self.rect.centery
                dist_sq = dist_x ** 2 + dist_y ** 2

                if dist_sq < closest_enemy_dist_sq:
                    closest_enemy_dist_sq = dist_sq
                    self.target_enemy_pos = enemy.rect.center

            direccion_final_disparo = self.direccion_disparo 

            if self.target_enemy_pos:
                target_dx = self.target_enemy_pos[0] - self.rect.centerx
                target_dy = self.target_enemy_pos[1] - self.rect.centery
                mag = math.sqrt(target_dx ** 2 + target_dy ** 2)
                if mag > 0:
                    direccion_final_disparo = (target_dx / mag, target_dy / mag)

            damage_to_deal = random.randint(BULLET_DAMAGE_MIN, BULLET_DAMAGE_MAX)
            damage_to_deal = damage_to_deal * 2 if self.bonus_x2_activo else damage_to_deal
            return Bala(self.rect.centerx, self.rect.centery, direccion_final_disparo, es_jugador=True, daño=damage_to_deal)
        return None

    def draw_aim_assist(self, screen):
        pass

    def activar_invulnerabilidad(self):
        """Activar el power-up de invulnerabilidad"""
        self.invulnerable_powerup_activo = True
        self.tiempo_inicio_invulnerabilidad_powerup = pygame.time.get_ticks()

    def activar_bonus_x2(self):
        """Activar el power-up de daño doble"""
        self.bonus_x2_activo = True
        self.tiempo_inicio_bonus_x2 = pygame.time.get_ticks()

    def aumentar_corazon(self):
        """Aumentar un corazón de vida"""
        if self.corazones < self.max_corazones:
            self.corazones += 1
            self.vida_actual_corazon = self.vida_por_corazon

class Bala(pygame.sprite.Sprite):
    """Clase para las balas del juego"""
    def __init__(self, x, y, direccion, es_jugador=True, daño=None):
        super().__init__()
        self.original_image = pygame.Surface((10, 5), pygame.SRCALPHA)
        self.original_image.fill(ROJO if es_jugador else AMARILLO)
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(x, y))

        self.speed = BULLET_SPEED if es_jugador else ENEMY_BULLET_SPEED
        self.dx = direccion[0] * self.speed
        self.dy = direccion[1] * self.speed

        self.daño = daño if daño is not None else (random.randint(BULLET_DAMAGE_MIN, BULLET_DAMAGE_MAX) if es_jugador else ENEMY_BULLET_DAMAGE)
        self.distancia_recorrida = 0
        self.alcance_maximo = 400
        self.es_jugador = es_jugador

        #rotamos la pantalla segun la direccion del jugador
        if self.dx == 0 and self.dy == 0:
            angle = 0
        else:
            angle = math.degrees(math.atan2(-self.dy, self.dx))
        self.image = pygame.transform.rotate(self.original_image, angle)
        self.rect = self.image.get_rect(center=self.rect.center)

    def update(self, offset_x, offset_y):
        """Actualizar la posición de la bala"""
        self.rect.x += self.dx
        self.rect.y += self.dy
        self.distancia_recorrida += math.sqrt(self.dx ** 2 + self.dy ** 2)

        #eliminamos las balas del jugador que se salen de los limines establecidos
        if (self.rect.left > WORLD_WIDTH or self.rect.right < 0 or
                self.rect.top > WORLD_HEIGHT or self.rect.bottom < 0 or
                self.distancia_recorrida > self.alcance_maximo):
            self.kill()

