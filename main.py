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
    
