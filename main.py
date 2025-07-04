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
    seleccion_actual = 0
    joystick = get_joystick()

    num_personajes = len(personajes)
    personaje_width = 150
    personaje_height = 200
    spacing = 50
    total_width = num_personajes * personaje_width + (num_personajes - 1) * spacing
    start_x = (ANCHO_PANTALLA - total_width) // 2
    start_y = ALTO_PANTALLA // 2 - personaje_height // 2

    while estado_actual == ESTADO_SELECCION_PERSONAJE:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                global juego_corriendo
                juego_corriendo = False
                return
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    estado_actual = ESTADO_MENU
                    return
                if evento.key == pygame.K_LEFT:
                    seleccion_actual = (seleccion_actual - 1 + num_personajes) % num_personajes
                if evento.key == pygame.K_RIGHT:
                    seleccion_actual = (seleccion_actual + 1) % num_personajes
                if evento.key == pygame.K_RETURN:
                    personaje_elegido = personajes[seleccion_actual]
                    #al iniciar el juego el jugador siempre aparecera en el centro del mapa
                    jugador = Jugador(WORLD_WIDTH // 2, WORLD_HEIGHT // 2,
                                     None,
                                     personaje_elegido["imagen"],
                                     usar_nuevo_sistema=True,
                                     carpeta_movimiento=personaje_elegido["carpeta_movimiento"])
                    estado_actual = ESTADO_JUEGO
                    iniciar_juego()
                    return
            
            if joystick:
                if evento.type == pygame.JOYAXISMOTION:
                    if evento.axis == 0:
                        if evento.value < -joystick_threshold_menu and not joystick_moved_x:
                            seleccion_actual = (seleccion_actual - 1 + num_personajes) % num_personajes
                            joystick_moved_x = True
                        elif evento.value > joystick_threshold_menu and not joystick_moved_x:
                            seleccion_actual = (seleccion_actual + 1) % num_personajes
                            joystick_moved_x = True
                        elif abs(evento.value) < joystick_threshold_menu:
                            joystick_moved_x = False
                elif evento.type == pygame.JOYBUTTONDOWN:
                    if evento.button == 0:
                        personaje_elegido = personajes[seleccion_actual]
                        jugador = Jugador(WORLD_WIDTH // 2, WORLD_HEIGHT // 2,
                                         None,
                                         personaje_elegido["imagen"],
                                         usar_nuevo_sistema=True,
                                         carpeta_movimiento=personaje_elegido["carpeta_movimiento"])
                        estado_actual = ESTADO_JUEGO
                        iniciar_juego()
                        return
                    elif evento.button == 1:
                        estado_actual = ESTADO_MENU
                        return

        dibujar_fondo_estrellado()

        fuente_titulo = pygame.font.Font(None, 60)
        fuente_nombres = pygame.font.Font(None, 36)
        fuente_instrucciones = pygame.font.Font(None, 28)

        texto_titulo = fuente_titulo.render("SELECCIONA TU PERSONAJE", True, BLANCO)
        PANTALLA.blit(texto_titulo, (ANCHO_PANTALLA // 2 - texto_titulo.get_width() // 2, 50))

        for i, personaje in enumerate(personajes):
            x_pos = start_x + i * (personaje_width + spacing)
            y_pos = start_y

            rect = pygame.Rect(x_pos, y_pos, personaje_width, personaje_height)
            color_borde = ROJO if i == seleccion_actual else BLANCO
            pygame.draw.rect(PANTALLA, color_borde, rect, 3)

            if personaje["imagen"]:
                img = pygame.transform.scale(personaje["imagen"], (personaje_width - 20, personaje_height - 60))
                img_rect = img.get_rect(center=(rect.centerx, rect.centery - 15))
                PANTALLA.blit(img, img_rect)
            
            texto_nombre = fuente_nombres.render(personaje["nombre"], True, color_borde)
            texto_nombre_rect = texto_nombre.get_rect(center=(rect.centerx, rect.bottom - 25))
            PANTALLA.blit(texto_nombre, texto_nombre_rect)

        texto_instrucciones_nav = fuente_instrucciones.render("Usa ← y → para navegar, ENTER para seleccionar", True, BLANCO)
        PANTALLA.blit(texto_instrucciones_nav,
                     (ANCHO_PANTALLA // 2 - texto_instrucciones_nav.get_width() // 2, ALTO_PANTALLA - 80))
        
        texto_instrucciones_esc = fuente_instrucciones.render("Presiona ESC para volver al menú principal", True, BLANCO)
        PANTALLA.blit(texto_instrucciones_esc,
                     (ANCHO_PANTALLA // 2 - texto_instrucciones_esc.get_width() // 2, ALTO_PANTALLA - 40))

        pygame.display.flip()
        RELOJ.tick(FPS)

def iniciar_juego():
    global grupo_enemigos, grupo_torretas, grupo_obstaculos_actual, grid_mapa_actual, grupo_balas_enemigo, grupo_balas_jugador
    global grupo_explosiones, grupo_powerups, grupo_indicadores_daño, grupo_indicadores_daño_jugador, camera_offset_x, camera_offset_y
    global posicion_copa_mundo, copa_sprite, copa_encontrada, NIVEL_ACTUAL

    grupo_balas_jugador.empty()
    grupo_balas_enemigo.empty()
    grupo_explosiones.empty()
    grupo_indicadores_daño.empty()
    grupo_indicadores_daño_jugador.empty()
    copa_encontrada = False

    #generamos el mapa al momento de iniciar la partida
    generar_mapa_interactivo()

    if jugador:
        jugador.rect.center = (WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
    

    camera_offset_x = jugador.rect.centerx - ANCHO_PANTALLA // 2
    camera_offset_y = jugador.rect.centery - ALTO_PANTALLA // 2

    camera_offset_x = max(0, min(WORLD_WIDTH - ANCHO_PANTALLA, camera_offset_x))
    camera_offset_y = max(0, min(WORLD_HEIGHT - ALTO_PANTALLA, camera_offset_y))

    #spaunean enemigos a la vista del jugador al momento de iniciar el juego
    spawn_enemies_in_view(jugador.rect, len(grupo_enemigos), len(grupo_torretas))

def escena_juego():
    global estado_actual, juego_corriendo, sonido_mapa_actual, camera_offset_x, camera_offset_y
    global grupo_explosiones, grupo_powerups, grupo_indicadores_daño, grupo_indicadores_daño_jugador, enemigos_eliminados_stats
    global copa_encontrada, copa_sprite, NIVEL_ACTUAL

    if jugador is None:
        estado_actual = ESTADO_SELECCION_PERSONAJE
        return

    if ASSETS['sonido_mapa1'] and not pygame.mixer.Channel(0).get_busy():
        pygame.mixer.Channel(0).set_volume(volumen_global)
        pygame.mixer.Channel(0).play(ASSETS['sonido_mapa1'], -1)

    joystick = get_joystick()

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            juego_corriendo = False
            return
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_ESCAPE:
                estado_actual = ESTADO_PAUSA
                pygame.mixer.Channel(0).pause()
                return
            if evento.key == pygame.K_SPACE:
                bala = jugador.disparar(grupo_enemigos)
                if bala:
                    grupo_balas_jugador.add(bala)
        
        if joystick and evento.type == pygame.JOYBUTTONDOWN:
            if evento.button == 7:
                estado_actual = ESTADO_PAUSA
                pygame.mixer.Channel(0).pause()
                return

    #actualizacion de camara para que siga el jugador mientras se mueve por el mapa
    camera_offset_x = jugador.rect.centerx - ANCHO_PANTALLA // 2
    camera_offset_y = jugador.rect.centery - ALTO_PANTALLA // 2

    #nos aseguramos que la camara no salga de los limites del mapa 
    camera_offset_x = max(0, min(WORLD_WIDTH - ANCHO_PANTALLA, camera_offset_x))
    camera_offset_y = max(0, min(WORLD_HEIGHT - ALTO_PANTALLA, camera_offset_y))

    #actualizamos todos los sprites para evitar bugs dentro del juego
    jugador.update(grupo_obstaculos_actual, grupo_enemigos, camera_offset_x, camera_offset_y)
    
    game_state = {
        'grupo_obstaculos': grupo_obstaculos_actual,
        'grupo_balas_enemigo': grupo_balas_enemigo,
        'grid': grid_mapa_actual,
        'jugador': jugador,
        'grupo_enemigos': grupo_enemigos
    }
    #actualizamos los enemigos para pasarle las coordenadas de la copa que deben defender del jugador
    for enemigo in grupo_enemigos:
        enemigo.update(jugador, game_state, posicion_copa_mundo)
    
    #actualizamos la torreta
    for torreta in grupo_torretas:
        torreta.update(jugador, game_state)

    grupo_balas_jugador.update(camera_offset_x, camera_offset_y)
    grupo_balas_enemigo.update(camera_offset_x, camera_offset_y)
    grupo_powerups.update()
    grupo_explosiones.update()
    grupo_indicadores_daño.update(camera_offset_y)
    grupo_indicadores_daño_jugador.update(camera_offset_y)

    #para mejorar el rendimiento del juego vamos eliminando los enemigos que esten alejados del jugador para
    #asi evitar problemas de rendimiento
    for enemy in list(grupo_enemigos):
        if math.sqrt((enemy.rect.centerx - jugador.rect.centerx)**2 + (enemy.rect.centery - jugador.rect.centery)**2) > ANCHO_PANTALLA * 2:
            enemy.kill()
    for turret in list(grupo_torretas):
        if math.sqrt((turret.rect.centerx - jugador.rect.centerx)**2 + (turret.rect.centery - jugador.rect.centery)**2) > ANCHO_PANTALLA * 2:
            turret.kill()

    #spauneamos mas enemigos segun sean eliminados
    spawn_enemies_in_view(jugador.rect, len(grupo_enemigos), len(grupo_torretas))

    #coliciones
    for bala in grupo_balas_jugador:
        enemigos_golpeados = pygame.sprite.spritecollide(bala, grupo_enemigos, False)
        for enemigo in enemigos_golpeados:
            enemigo.recibir_daño(bala.daño)
            bala.kill()
            if enemigo.vida <= 0:
                jugador.score += 100
                enemigos_eliminados_stats[ENEMY_NAMES_MAP.get(enemigo.tipo_enemigo, "Desconocido")] += 1

                grupo_explosiones.add(Explosion(enemigo.rect.centerx, enemigo.rect.centery))
                if ASSETS['sonido_explocion']:
                    pygame.mixer.Channel(2).set_volume(volumen_global)
                    pygame.mixer.Channel(2).play(ASSETS['sonido_explocion'])
                
                if random.random() < 0.2:
                    powerup_types = ["bonusx2", "estrella", "tnt", "vida"]
                    chosen_powerup_type = random.choice(powerup_types)
                    grupo_powerups.add(PowerUp(enemigo.rect.centerx, enemigo.rect.centery, chosen_powerup_type))
                
                enemigo.kill()
                spawn_enemies_in_view(jugador.rect, len(grupo_enemigos), len(grupo_torretas))

        torretas_golpeadas = pygame.sprite.spritecollide(bala, grupo_torretas, False)
        for torreta in torretas_golpeadas:
            torreta.recibir_daño(bala.daño)
            bala.kill()
            if torreta.vida <= 0:
                jugador.score += 150
                enemigos_eliminados_stats[ENEMY_NAMES_MAP.get(torreta.tipo_enemigo, "Desconocido")] += 1

                grupo_explosiones.add(Explosion(torreta.rect.centerx, torreta.rect.centery))
                if ASSETS['sonido_explocion']:
                    pygame.mixer.Channel(2).set_volume(volumen_global)
                    pygame.mixer.Channel(2).play(ASSETS['sonido_explocion'])
                
                if random.random() < 0.3:
                    powerup_types = ["bonusx2", "estrella", "tnt", "vida"]
                    chosen_powerup_type = random.choice(powerup_types)
                    grupo_powerups.add(PowerUp(torreta.rect.centerx, torreta.rect.centery, chosen_powerup_type))
                
                torreta.kill()
                spawn_enemies_in_view(jugador.rect, len(grupo_enemigos), len(grupo_torretas))

        obstaculos_golpeados = pygame.sprite.spritecollide(bala, grupo_obstaculos_actual, False)
        for obstaculo in obstaculos_golpeados:
            if obstaculo.tipo == "solido":
                bala.kill()
            elif obstaculo.tipo == "destructible":
                obstaculo.recibir_daño(bala.daño)
                bala.kill()
    
    