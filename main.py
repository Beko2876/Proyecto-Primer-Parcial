import pygame
import math
import random
import os
import sys
import json
from scripts.configuracion import *
from scripts.personajes import *
from scripts.enemigos import *
from scripts.astar import a_star

#aqui pondremos las variables para el juego
estado_actual = ESTADO_INTRO
juego_corriendo  = True
jugador = None
num_enemigos_por_zona = 5 #para el juego tendremos 5 enemigos por zona de camara en la pantalla
#esto lo hacemos para poder tener un buen rendimiento en el juego
num_torretas_por_zona = 1
sonido_mapa_actual = None
sonido_derrota_reproduciondose = False
sonido_victoria_reproduciendose = False

#variables para la copa del tesoro que el usuario debe de conseguir la cual los snemigos protegen
posicion_copa_mundo = None
copa_sprite = None
copa_encontrada = None

#variables para el manejo de GAMEPAD dentro del menu de opciones
joystick_menu = None

def get_joystick():
    global joystick_menu
    if joystick_menu is None and pygame.joystick.get_count() > 0:
        joystick_menu = pygame.joystick.Joystick(0)
        joystick_menu.init()
    return joystick_menu

#esta linea contiene unas estadisticas para los enemigos eliminados al final de la partida
enemigos_eliminados_stats = {
    "Nefasto": 0,
    "Inquisidor": 0,
    "Siniestro": 0,
    "Vandal": 0,
    "Torreta": 0
}

#aqui agregaremos los mapas de una manera interactivos

def generar_mapa_interactivo():
    global grid_mapa_actual, grupo_obstaculos_actual, grupo_enemigos, grupo_torretas, grupo_powerups, posicion_copa_mundo, copa_sprite

    grupo_obstaculos_actual.empty()
    grupo_enemigos.empty()
    grupo_torretas.empty()
    grupo_powerups.empty()
    grid_mapa_actual = [[0 for _ in range(GRID_ALTO)] for _ in range(GRID_ANCHO)]

#generamos los obstaculos de una manera dispersa para que no tenga tantos obstaculos dentro de la partida
#esto lo hacemos para mayor rendimiento dentro del juego
    num_obstaculos_totales = (WORLD_WIDTH * WORLD_HEIGHT) // (TILE_SIZE * TILE_SIZE * 150)
    
    for _ in range(num_obstaculos_totales):
        attempts = 0
        while attempts < 100:
            ox = random.randint(0, WORLD_WIDTH - OBSTACLE_SIZE)
            oy = random.randint(0, WORLD_HEIGHT - OBSTACLE_SIZE)
            
            temp_rect = pygame.Rect(ox, oy, OBSTACLE_SIZE, OBSTACLE_SIZE)
            
            collision_found = False
            for existing_obstacle in grupo_obstaculos_actual:
                if temp_rect.colliderect(existing_obstacle.rect.inflate(TILE_SIZE, TILE_SIZE)):
                    collision_found = True
                    break
            
            if not collision_found:
                if random.random() < 0.7: 
                    grupo_obstaculos_actual.add(Obstaculo(ox, oy, OBSTACLE_SIZE, OBSTACLE_SIZE, imagen=ASSETS['obstaculo_arbusto'], tipo="arbusto"))
                else:
                    grupo_obstaculos_actual.add(Obstaculo(ox, oy, OBSTACLE_SIZE, OBSTACLE_SIZE, imagen=ASSETS['piedra'], tipo="solido"))
                break
            attempts += 1

    # actualizacion del grid para el pathfinding
    for obstaculo in grupo_obstaculos_actual:
        if obstaculo.tipo in ["solido", "destructible"]:
            x_grid_start = max(0, obstaculo.rect.x // TILE_SIZE)
            y_grid_start = max(0, obstaculo.rect.y // TILE_SIZE)
            x_grid_end = min(GRID_ANCHO - 1, (obstaculo.rect.right - 1) // TILE_SIZE)
            y_grid_end = min(GRID_ALTO - 1, (obstaculo.rect.bottom - 1) // TILE_SIZE)

            for i in range(x_grid_start, x_grid_end + 1):
                for j in range(y_grid_start, y_grid_end + 1):
                    if 0 <= i < GRID_ANCHO and 0 <= j < GRID_ALTO:
                        grid_mapa_actual[i][j] = 1
                        
                        
      #generamos la copa en un lugar aleatorio y alejada del jugador
    attempts = 0
    player_start_x = WORLD_WIDTH // 2
    player_start_y = WORLD_HEIGHT // 2
    min_distance_from_player = max(ANCHO_PANTALLA, ALTO_PANTALLA) * 1.5
    
    while attempts < 200:
        cx = random.randint(TILE_SIZE, WORLD_WIDTH - TILE_SIZE)
        cy = random.randint(TILE_SIZE, WORLD_HEIGHT - TILE_SIZE)
        
        dist_to_player_start = math.sqrt((cx - player_start_x)**2 + (cy - player_start_y)**2)

        if dist_to_player_start > min_distance_from_player:
            copa_temp_rect = pygame.Rect(cx, cy, TILE_SIZE * 2, TILE_SIZE * 2)
            collision_with_obstacle = False
            for obstaculo in grupo_obstaculos_actual:
                if obstaculo.tipo in ["solido", "destructible"] and copa_temp_rect.colliderect(obstaculo.rect):
                    collision_with_obstacle = True
                    break
            
            if not collision_with_obstacle:
                posicion_copa_mundo = (cx, cy)
                copa_sprite = PowerUp(cx, cy, "copa")
                break
        attempts += 1
    
    if posicion_copa_mundo is None:
        posicion_copa_mundo = (WORLD_WIDTH - TILE_SIZE * 5, WORLD_HEIGHT - TILE_SIZE * 5)
        copa_sprite = PowerUp(posicion_copa_mundo[0], posicion_copa_mundo[1], "copa")

def spawn_enemies_in_view(player_rect, current_enemies_count, current_turrets_count):
    global grupo_enemigos, grupo_torretas
    
    spawn_margin = TILE_SIZE * 5
    
  
    min_x_world = max(0, player_rect.centerx - ANCHO_PANTALLA // 2 - spawn_margin)
    max_x_world = min(WORLD_WIDTH - TILE_SIZE, player_rect.centerx + ANCHO_PANTALLA // 2 + spawn_margin)
    min_y_world = max(0, player_rect.centery - ALTO_PANTALLA // 2 - spawn_margin)
    max_y_world = min(WORLD_HEIGHT - TILE_SIZE, player_rect.centery + ALTO_PANTALLA // 2 + spawn_margin)

   
    target_enemies = num_enemigos_por_zona
    enemies_to_spawn = target_enemies - current_enemies_count

    for _ in range(enemies_to_spawn):
        attempts = 0
        spawn_x, spawn_y = -1, -1
        while attempts < 50:
            
            side = random.choice(['top', 'bottom', 'left', 'right'])
            
            if side == 'top':
                x_pos = random.randint(max(0, player_rect.centerx - ANCHO_PANTALLA // 2), min(WORLD_WIDTH - TILE_SIZE, player_rect.centerx + ANCHO_PANTALLA // 2))
                y_pos = random.randint(max(0, player_rect.centery - ALTO_PANTALLA // 2 - spawn_margin), max(0, player_rect.centery - ALTO_PANTALLA // 2 - TILE_SIZE))
            elif side == 'bottom':
                x_pos = random.randint(max(0, player_rect.centerx - ANCHO_PANTALLA // 2), min(WORLD_WIDTH - TILE_SIZE, player_rect.centerx + ANCHO_PANTALLA // 2))
                y_pos = random.randint(min(WORLD_HEIGHT - TILE_SIZE, player_rect.centery + ALTO_PANTALLA // 2 + TILE_SIZE), min(WORLD_HEIGHT - TILE_SIZE, player_rect.centery + ALTO_PANTALLA // 2 + spawn_margin))
            elif side == 'left':
                x_pos = random.randint(max(0, player_rect.centerx - ANCHO_PANTALLA // 2 - spawn_margin), max(0, player_rect.centerx - ANCHO_PANTALLA // 2 - TILE_SIZE))
                y_pos = random.randint(max(0, player_rect.centery - ALTO_PANTALLA // 2), min(WORLD_HEIGHT - TILE_SIZE, player_rect.centery + ALTO_PANTALLA // 2))
            else: 
                x_pos = random.randint(min(WORLD_WIDTH - TILE_SIZE, player_rect.centerx + ANCHO_PANTALLA // 2 + TILE_SIZE), min(WORLD_WIDTH - TILE_SIZE, player_rect.centerx + ANCHO_PANTALLA // 2 + spawn_margin))
                y_pos = random.randint(max(0, player_rect.centery - ALTO_PANTALLA // 2), min(WORLD_HEIGHT - TILE_SIZE, player_rect.centery + ALTO_PANTALLA // 2))

              #generamos la copa en un lugar aleatorio y alejada del jugador
    attempts = 0
    player_start_x = WORLD_WIDTH // 2
    player_start_y = WORLD_HEIGHT // 2
    min_distance_from_player = max(ANCHO_PANTALLA, ALTO_PANTALLA) * 1.5
    
    while attempts < 200:
        cx = random.randint(TILE_SIZE, WORLD_WIDTH - TILE_SIZE)
        cy = random.randint(TILE_SIZE, WORLD_HEIGHT - TILE_SIZE)
        
        dist_to_player_start = math.sqrt((cx - player_start_x)**2 + (cy - player_start_y)**2)

        if dist_to_player_start > min_distance_from_player:
            copa_temp_rect = pygame.Rect(cx, cy, TILE_SIZE * 2, TILE_SIZE * 2)
            collision_with_obstacle = False
            for obstaculo in grupo_obstaculos_actual:
                if obstaculo.tipo in ["solido", "destructible"] and copa_temp_rect.colliderect(obstaculo.rect):
                    collision_with_obstacle = True
                    break
            
            if not collision_with_obstacle:
                posicion_copa_mundo = (cx, cy)
                copa_sprite = PowerUp(cx, cy, "copa")
                break
        attempts += 1
    
    if posicion_copa_mundo is None:
        posicion_copa_mundo = (WORLD_WIDTH - TILE_SIZE * 5, WORLD_HEIGHT - TILE_SIZE * 5)
        copa_sprite = PowerUp(posicion_copa_mundo[0], posicion_copa_mundo[1], "copa")

def spawn_enemies_in_view(player_rect, current_enemies_count, current_turrets_count):
    global grupo_enemigos, grupo_torretas
    
    spawn_margin = TILE_SIZE * 5
    
  
    min_x_world = max(0, player_rect.centerx - ANCHO_PANTALLA // 2 - spawn_margin)
    max_x_world = min(WORLD_WIDTH - TILE_SIZE, player_rect.centerx + ANCHO_PANTALLA // 2 + spawn_margin)
    min_y_world = max(0, player_rect.centery - ALTO_PANTALLA // 2 - spawn_margin)
    max_y_world = min(WORLD_HEIGHT - TILE_SIZE, player_rect.centery + ALTO_PANTALLA // 2 + spawn_margin)

   
    target_enemies = num_enemigos_por_zona
    enemies_to_spawn = target_enemies - current_enemies_count

    for _ in range(enemies_to_spawn):
        attempts = 0
        spawn_x, spawn_y = -1, -1
        while attempts < 50:
            
            side = random.choice(['top', 'bottom', 'left', 'right'])
            
            if side == 'top':
                x_pos = random.randint(max(0, player_rect.centerx - ANCHO_PANTALLA // 2), min(WORLD_WIDTH - TILE_SIZE, player_rect.centerx + ANCHO_PANTALLA // 2))
                y_pos = random.randint(max(0, player_rect.centery - ALTO_PANTALLA // 2 - spawn_margin), max(0, player_rect.centery - ALTO_PANTALLA // 2 - TILE_SIZE))
            elif side == 'bottom':
                x_pos = random.randint(max(0, player_rect.centerx - ANCHO_PANTALLA // 2), min(WORLD_WIDTH - TILE_SIZE, player_rect.centerx + ANCHO_PANTALLA // 2))
                y_pos = random.randint(min(WORLD_HEIGHT - TILE_SIZE, player_rect.centery + ALTO_PANTALLA // 2 + TILE_SIZE), min(WORLD_HEIGHT - TILE_SIZE, player_rect.centery + ALTO_PANTALLA // 2 + spawn_margin))
            elif side == 'left':
                x_pos = random.randint(max(0, player_rect.centerx - ANCHO_PANTALLA // 2 - spawn_margin), max(0, player_rect.centerx - ANCHO_PANTALLA // 2 - TILE_SIZE))
                y_pos = random.randint(max(0, player_rect.centery - ALTO_PANTALLA // 2), min(WORLD_HEIGHT - TILE_SIZE, player_rect.centery + ALTO_PANTALLA // 2))
            else: 
                x_pos = random.randint(min(WORLD_WIDTH - TILE_SIZE, player_rect.centerx + ANCHO_PANTALLA // 2 + TILE_SIZE), min(WORLD_WIDTH - TILE_SIZE, player_rect.centerx + ANCHO_PANTALLA // 2 + spawn_margin))
                y_pos = random.randint(max(0, player_rect.centery - ALTO_PANTALLA // 2), min(WORLD_HEIGHT - TILE_SIZE, player_rect.centery + ALTO_PANTALLA // 2))
