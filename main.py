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
    
    #coliciones de balas enemigas contra el jugador
    for bala_enemigo in grupo_balas_enemigo:
        if pygame.sprite.collide_rect(bala_enemigo, jugador):
            jugador.recibir_daño(bala_enemigo.daño)
            bala_enemigo.kill()

    for enemigo in grupo_enemigos:
        if enemigo.rect.colliderect(jugador.rect):
            ahora = pygame.time.get_ticks()
            if ahora - enemigo.ultimo_ataque_cuerpo_a_cuerpo > enemigo.tiempo_entre_ataques_cuerpo_a_cuerpo:
                enemigo.ultimo_ataque_cuerpo_a_cuerpo = ahora
                jugador.recibir_daño(ENEMY_MELEE_DAMAGE)

    powerups_recolectados = pygame.sprite.spritecollide(jugador, grupo_powerups, True)
    for powerup in powerups_recolectados:
        if ASSETS['sonido_powerup']:
            pygame.mixer.Channel(3).set_volume(volumen_global)
            pygame.mixer.Channel(3).play(ASSETS['sonido_powerup'])

        if powerup.tipo == "bonusx2":
            jugador.activar_bonus_x2()
        elif powerup.tipo == "estrella":
            jugador.activar_invulnerabilidad()
        elif powerup.tipo == "tnt":
            for enemy in list(grupo_enemigos):
                grupo_explosiones.add(Explosion(enemy.rect.centerx, enemy.rect.centery))
                if ASSETS['sonido_explocion']:
                    pygame.mixer.Channel(2).set_volume(volumen_global)
                    pygame.mixer.Channel(2).play(ASSETS['sonido_explocion'])
                
                enemigos_eliminados_stats[ENEMY_NAMES_MAP.get(enemy.tipo_enemigo, "Desconocido")] += 1

                enemy.kill()
                jugador.score += 100
                spawn_enemies_in_view(jugador.rect, len(grupo_enemigos), len(grupo_torretas))
            for turret in list(grupo_torretas):
                grupo_explosiones.add(Explosion(turret.rect.centerx, turret.rect.centery))
                if ASSETS['sonido_explocion']:
                    pygame.mixer.Channel(2).set_volume(volumen_global)
                    pygame.mixer.Channel(2).play(ASSETS['sonido_explocion'])
                
                enemigos_eliminados_stats[ENEMY_NAMES_MAP.get(turret.tipo_enemigo, "Desconocido")] += 1

                turret.kill()
                jugador.score += 150
                spawn_enemies_in_view(jugador.rect, len(grupo_enemigos), len(grupo_torretas))

        elif powerup.tipo == "vida":
            jugador.aumentar_corazon()
    
    #colicion entre la copa y el jugador
    if copa_sprite and jugador.rect.colliderect(copa_sprite.rect):
        copa_encontrada = True
        if ASSETS['sonido_victoria']:
            pygame.mixer.Channel(1).set_volume(volumen_global)
            pygame.mixer.Channel(1).play(ASSETS['sonido_victoria'])
        pygame.mixer.Channel(0).stop()
        
        if NIVEL_ACTUAL < MAX_NIVELES:
            NIVEL_ACTUAL += 1
            resetear_juego_para_siguiente_nivel()
            iniciar_juego()
        else:
            estado_actual = ESTADO_ESTADISTICAS_FINALES

    if jugador.corazones <= 0:
        pygame.mixer.Channel(0).stop()
        
        global sonido_derrota_reproduciendose
        if ASSETS['sonido_perdiste'] and not sonido_derrota_reproduciendose:
            pygame.mixer.Channel(1).set_volume(volumen_global)
            pygame.mixer.Channel(1).play(ASSETS['sonido_perdiste'])
            sonido_derrota_reproduciendose = True
            
            pygame.time.wait(int(ASSETS['sonido_perdiste'].get_length() * 1000))
            sonido_derrota_reproduciendose = False

        estado_actual = ESTADO_DERROTA

    PANTALLA.fill(VERDE_PASTO)


    visible_rect = pygame.Rect(camera_offset_x, camera_offset_y, ANCHO_PANTALLA, ALTO_PANTALLA)

    for sprite in grupo_obstaculos_actual:
        if visible_rect.colliderect(sprite.rect):
            PANTALLA.blit(sprite.image, (sprite.rect.x - camera_offset_x, sprite.rect.y - camera_offset_y))
    
    for sprite in grupo_enemigos:
        if visible_rect.colliderect(sprite.rect):
            PANTALLA.blit(sprite.image, (sprite.rect.x - camera_offset_x, sprite.rect.y - camera_offset_y))
            sprite.draw_health_bar(PANTALLA, camera_offset_x, camera_offset_y)

    for sprite in grupo_torretas:
        if visible_rect.colliderect(sprite.rect):
            PANTALLA.blit(sprite.image, (sprite.rect.x - camera_offset_x, sprite.rect.y - camera_offset_y))
            sprite.draw_health_bar(PANTALLA, camera_offset_x, camera_offset_y)

    for sprite in grupo_balas_jugador:
        if visible_rect.colliderect(sprite.rect):
            PANTALLA.blit(sprite.image, (sprite.rect.x - camera_offset_x, sprite.rect.y - camera_offset_y))
    
    for sprite in grupo_balas_enemigo:
        if visible_rect.colliderect(sprite.rect):
            PANTALLA.blit(sprite.image, (sprite.rect.x - camera_offset_x, sprite.rect.y - camera_offset_y))

    for sprite in grupo_powerups:
        if visible_rect.colliderect(sprite.rect):
            PANTALLA.blit(sprite.image, (sprite.rect.x - camera_offset_x, sprite.rect.y - camera_offset_y))

    for sprite in grupo_explosiones:
        if visible_rect.colliderect(sprite.rect):
            PANTALLA.blit(sprite.image, (sprite.rect.x - camera_offset_x, sprite.rect.y - camera_offset_y))

    for sprite in grupo_indicadores_daño:
        PANTALLA.blit(sprite.image, (sprite.rect.x - camera_offset_x, sprite.rect.y))
    
    for sprite in grupo_indicadores_daño_jugador:
        PANTALLA.blit(sprite.image, (sprite.rect.x - camera_offset_x, sprite.rect.y))

    #dibujamos la copa
    if copa_sprite and visible_rect.colliderect(copa_sprite.rect):
        PANTALLA.blit(copa_sprite.image, (copa_sprite.rect.x - camera_offset_x, copa_sprite.rect.y - camera_offset_y))

    #dibujamos el jugador en el centro del mapa relativo a la camara
    PANTALLA.blit(jugador.image, (jugador.rect.x - camera_offset_x, jugador.rect.y - camera_offset_y))

    jugador.draw_aim_assist(PANTALLA)

    # dibujamos el UI
    corazon_img = pygame.transform.scale(ASSETS['powerup_vida'], (30, 30))
    for i in range(jugador.corazones):
        PANTALLA.blit(corazon_img, (10 + i * 35, 10))
    
    if jugador.corazones > 0:
        barra_ancho = 30
        barra_alto = 5
        vida_porcentaje = jugador.vida_actual_corazon / jugador.vida_por_corazon
        pygame.draw.rect(PANTALLA, ROJO, (10, 45, barra_ancho, barra_alto))
        pygame.draw.rect(PANTALLA, VERDE, (10, 45, barra_ancho * vida_porcentaje, barra_alto))

    fuente_ui = pygame.font.Font(None, 30)
    texto_enemigos_restantes = fuente_ui.render(f"Enemigos en pantalla: {len(grupo_enemigos) + len(grupo_torretas)}", True, BLANCO)
    PANTALLA.blit(texto_enemigos_restantes, (ANCHO_PANTALLA - texto_enemigos_restantes.get_width() - 10, 10))
    texto_score = fuente_ui.render(f"Score: {jugador.score}", True, BLANCO)
    PANTALLA.blit(texto_score, (ANCHO_PANTALLA - texto_score.get_width() - 10, 40))
    texto_nivel = fuente_ui.render(f"Nivel: {NIVEL_ACTUAL}/{MAX_NIVELES}", True, BLANCO)
    PANTALLA.blit(texto_nivel, (ANCHO_PANTALLA - texto_nivel.get_width() - 10, 70))

    if jugador.invulnerable_powerup_activo:
        fuente_powerup = pygame.font.Font(None, 24)
        tiempo_restante = max(0, (jugador.duracion_invulnerabilidad_powerup - (pygame.time.get_ticks() - jugador.tiempo_inicio_invulnerabilidad_powerup)) // 1000)
        texto_invulnerable = fuente_powerup.render(f"Inmune: {tiempo_restante}s", True, AZUL)
        PANTALLA.blit(texto_invulnerable, (10, ALTO_PANTALLA - 30))
    
    if jugador.bonus_x2_activo:
        fuente_powerup = pygame.font.Font(None, 24)
        tiempo_restante = max(0, (jugador.duracion_bonus_x2 - (pygame.time.get_ticks() - jugador.tiempo_inicio_bonus_x2)) // 1000)
        texto_bonusx2 = fuente_powerup.render(f"Bonus x2: {tiempo_restante}s", True, AMARILLO)
        PANTALLA.blit(texto_bonusx2, (10, ALTO_PANTALLA - 60))

    # Dibujar el minimapa
    dibujar_minimapa(PANTALLA, jugador.rect, camera_offset_x, camera_offset_y)

    pygame.display.flip()
    RELOJ.tick(FPS)

def escena_pausa():
    global estado_actual, juego_corriendo, joystick_moved_y

    opciones = ["Continuar", "Volver al Menú", "Salir del Juego"]
    seleccion_actual = 0

    joystick = get_joystick()

    while estado_actual == ESTADO_PAUSA:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                juego_corriendo = False
                return
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    estado_actual = ESTADO_JUEGO
                    pygame.mixer.Channel(0).unpause()
                    return
                if evento.key == pygame.K_DOWN:
                    seleccion_actual = (seleccion_actual + 1) % len(opciones)
                if evento.key == pygame.K_UP:
                    seleccion_actual = (seleccion_actual - 1 + len(opciones)) % len(opciones)
                if evento.key == pygame.K_RETURN:
                    if seleccion_actual == 0:
                        estado_actual = ESTADO_JUEGO
                        pygame.mixer.Channel(0).unpause()
                        return
                    elif seleccion_actual == 1:
                        resetear_juego()
                        estado_actual = ESTADO_MENU
                        return
                    elif seleccion_actual == 2:
                        juego_corriendo = False
                        return
            
            if joystick:
                if evento.type == pygame.JOYAXISMOTION:
                    if evento.axis == 1:
                        if evento.value > joystick_threshold_menu and not joystick_moved_y:
                            seleccion_actual = (seleccion_actual + 1) % len(opciones)
                            joystick_moved_y = True
                        elif evento.value < -joystick_threshold_menu and not joystick_moved_y:
                            seleccion_actual = (seleccion_actual - 1 + len(opciones)) % len(opciones)
                            joystick_moved_y = True
                        elif abs(evento.value) < joystick_threshold_menu:
                            joystick_moved_y = False
                elif evento.type == pygame.JOYBUTTONDOWN:
                    if evento.button == 0 or evento.button == 7:
                        if seleccion_actual == 0:
                            estado_actual = ESTADO_JUEGO
                            pygame.mixer.Channel(0).unpause()
                            return
                        elif seleccion_actual == 1:
                            resetear_juego()
                            estado_actual = ESTADO_MENU
                            return
                        elif seleccion_actual == 2:
                            juego_corriendo = False
                            return
                    elif evento.button == 1:
                        estado_actual = ESTADO_JUEGO
                        pygame.mixer.Channel(0).unpause()
                        return
        superficie_transparente = pygame.Surface((ANCHO_PANTALLA, ALTO_PANTALLA), pygame.SRCALPHA)
        superficie_transparente.fill((0, 0, 0, 128))
        PANTALLA.blit(superficie_transparente, (0, 0))

        fuente_titulo = pygame.font.Font(None, 74)
        fuente_opciones = pygame.font.Font(None, 50)

        texto_titulo = fuente_titulo.render("PAUSA", True, BLANCO)
        PANTALLA.blit(texto_titulo, (ANCHO_PANTALLA // 2 - texto_titulo.get_width() // 2, 150))

        for i, opcion in enumerate(opciones):
            color = ROJO if i == seleccion_actual else BLANCO
            texto_opcion = fuente_opciones.render(opcion, True, color)
            PANTALLA.blit(texto_opcion, (ANCHO_PANTALLA // 2 - texto_opcion.get_width() // 2, 250 + i * 60))

        pygame.display.flip()
        RELOJ.tick(FPS)

def escena_fin_juego():
    global estado_actual, juego_corriendo, sonido_victoria_reproduciendose

    if ASSETS['sonido_victoria'] and not sonido_victoria_reproduciendose:
        pygame.mixer.Channel(1).set_volume(volumen_global)
        pygame.mixer.Channel(1).play(ASSETS['sonido_victoria'])
        sonido_victoria_reproduciendose = True
        
        pygame.time.wait(int(ASSETS['sonido_victoria'].get_length() * 1000))
        sonido_victoria_reproduciendose = False

    if NIVEL_ACTUAL <= MAX_NIVELES:
        pass
    else:
        estado_actual = ESTADO_ESTADISTICAS_FINALES

def escena_derrota():
    global estado_actual, juego_corriendo, jugador, sonido_derrota_reproduciendose, joystick_moved_y

    if ASSETS['sonido_menu'] and not pygame.mixer.Channel(0).get_busy():
        pygame.mixer.Channel(0).set_volume(volumen_global)
        pygame.mixer.Channel(0).play(ASSETS['sonido_menu'], -1)

    opciones = ["Reintentar", "Volver al Menú", "Salir del Juego"]
    seleccion_actual = 0

    joystick = get_joystick()

    while estado_actual == ESTADO_DERROTA:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                juego_corriendo = False
                return
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_DOWN:
                    seleccion_actual = (seleccion_actual + 1) % len(opciones)
                if evento.key == pygame.K_UP:
                    seleccion_actual = (seleccion_actual - 1 + len(opciones)) % len(opciones)
                if evento.key == pygame.K_RETURN:
                    if seleccion_actual == 0:
                        resetear_juego()
                        estado_actual = ESTADO_JUEGO
                        iniciar_juego()
                        return
                    elif seleccion_actual == 1:
                        resetear_juego()
                        estado_actual = ESTADO_MENU
                        return
                    elif seleccion_actual == 2:
                        juego_corriendo = False
                        return
            
            if joystick:
                if evento.type == pygame.JOYAXISMOTION:
                    if evento.axis == 1:
                        if evento.value > joystick_threshold_menu and not joystick_moved_y:
                            seleccion_actual = (seleccion_actual + 1) % len(opciones)
                            joystick_moved_y = True
                        elif evento.value < -joystick_threshold_menu and not joystick_moved_y:
                            seleccion_actual = (seleccion_actual - 1 + len(opciones)) % len(opciones)
                            joystick_moved_y = True
                        elif abs(evento.value) < joystick_threshold_menu:
                            joystick_moved_y = False
                elif evento.type == pygame.JOYBUTTONDOWN:
                    if evento.button == 0:
                        if seleccion_actual == 0:
                            resetear_juego()
                            estado_actual = ESTADO_JUEGO
                            iniciar_juego()
                            return
                        elif seleccion_actual == 1:
                            resetear_juego()
                            estado_actual = ESTADO_MENU
                            return
                        elif seleccion_actual == 2:
                            juego_corriendo = False
                            return
                    elif evento.button == 1:
                        resetear_juego()
                        estado_actual = ESTADO_MENU
                        return

        dibujar_fondo_estrellado()

        fuente_titulo = pygame.font.Font(None, 74)
        fuente_opciones = pygame.font.Font(None, 50)

        texto_derrota = fuente_titulo.render("HAS SIDO DERROTADO", True, ROJO)
        PANTALLA.blit(texto_derrota, (ANCHO_PANTALLA // 2 - texto_derrota.get_width() // 2, 150))

        for i, opcion in enumerate(opciones):
            color = ROJO if i == seleccion_actual else BLANCO
            texto_opcion = fuente_opciones.render(opcion, True, color)
            PANTALLA.blit(texto_opcion, (ANCHO_PANTALLA // 2 - texto_opcion.get_width() // 2, 300 + i * 60))

        pygame.display.flip()
        RELOJ.tick(FPS)

def escena_estadisticas_finales():
    global estado_actual, juego_corriendo, enemigos_eliminados_stats

    font_title = pygame.font.Font(None, 60)
    font_text = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 28)

    total_enemigos_eliminados = sum(enemigos_eliminados_stats.values())

    joystick = get_joystick()

    while estado_actual == ESTADO_ESTADISTICAS_FINALES:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                juego_corriendo = False
                return
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE or evento.key == pygame.K_RETURN:
                    resetear_juego()
                    estado_actual = ESTADO_MENU
                    return
            
            if joystick and evento.type == pygame.JOYBUTTONDOWN:
                if evento.button == 1:
                    resetear_juego()
                    estado_actual = ESTADO_MENU
                    return

        dibujar_fondo_estrellado()

        text_title = font_title.render("¡JUEGO COMPLETADO!", True, VERDE)
        PANTALLA.blit(text_title, (ANCHO_PANTALLA // 2 - text_title.get_width() // 2, 50))

        text_total = font_text.render(f"Total de enemigos eliminados: {total_enemigos_eliminados}", True, VERDE)
        PANTALLA.blit(text_total, (ANCHO_PANTALLA // 2 - text_total.get_width() // 2, 120))

        y_offset = 180
        
        for i, (enemy_name, count) in enumerate(enemigos_eliminados_stats.items()):
            enemy_stats_text = font_text.render(f"{enemy_name}: {count}", True, BLANCO)
            PANTALLA.blit(enemy_stats_text, (ANCHO_PANTALLA // 2 - enemy_stats_text.get_width() // 2, y_offset + i * 40))

        text_return = font_small.render("Presiona ESC o ENTER para volver al menú", True, BLANCO)
        PANTALLA.blit(text_return, (ANCHO_PANTALLA // 2 - text_return.get_width() // 2, ALTO_PANTALLA - 50))

        pygame.display.flip()
        RELOJ.tick(FPS)

def resetear_juego():
    global jugador, grupo_enemigos, grupo_torretas, grupo_balas_jugador, grupo_balas_enemigo, grupo_obstaculos_actual
    global sonido_derrota_reproduciendose, grupo_explosiones, grupo_powerups, grupo_indicadores_daño, grupo_indicadores_daño_jugador, enemigos_eliminados_stats
    global joystick_moved_x, joystick_moved_y, camera_offset_x, camera_offset_y, posicion_copa_mundo, copa_sprite, copa_encontrada, NIVEL_ACTUAL

    jugador = None
    grupo_enemigos.empty()
    grupo_torretas.empty()
    grupo_balas_jugador.empty()
    grupo_balas_enemigo.empty()
    grupo_obstaculos_actual.empty()
    grupo_explosiones.empty()
    grupo_powerups.empty()
    grupo_indicadores_daño.empty()
    grupo_indicadores_daño_jugador.empty()
    
    camera_offset_x = 0
    camera_offset_y = 0

    posicion_copa_mundo = None
    copa_sprite = None
    copa_encontrada = False

    NIVEL_ACTUAL = 1

    pygame.mixer.Channel(0).stop()
    sonido_derrota_reproduciendose = False
    for key in enemigos_eliminados_stats:
        enemigos_eliminados_stats[key] = 0
    
    joystick_moved_x = False
    joystick_moved_y = False

def resetear_juego_para_siguiente_nivel():
    global grupo_enemigos, grupo_torretas, grupo_balas_jugador, grupo_balas_enemigo, grupo_obstaculos_actual
    global grupo_explosiones, grupo_powerups, grupo_indicadores_daño, grupo_indicadores_daño_jugador
    global posicion_copa_mundo, copa_sprite, copa_encontrada

    grupo_enemigos.empty()
    grupo_torretas.empty()
    grupo_balas_jugador.empty()
    grupo_balas_enemigo.empty()
    grupo_obstaculos_actual.empty()
    grupo_explosiones.empty()
    grupo_powerups.empty()
    grupo_indicadores_daño.empty()
    grupo_indicadores_daño_jugador.empty()
    
    posicion_copa_mundo = None
    copa_sprite = None
    copa_encontrada = False

    pygame.mixer.Channel(0).stop()

#bucle principal para todos los estados posibles dentro del juego
while juego_corriendo:
    if estado_actual == ESTADO_INTRO:
        escena_intro()
    elif estado_actual == ESTADO_MENU:
        escena_menu()
    elif estado_actual == ESTADO_SELECCION_PERSONAJE:
        escena_seleccion_personaje()
    elif estado_actual == ESTADO_JUEGO:
        escena_juego()
    elif estado_actual == ESTADO_PAUSA:
        escena_pausa()
    elif estado_actual == ESTADO_FIN_JUEGO:
        escena_fin_juego()
    elif estado_actual == ESTADO_DERROTA:
        escena_derrota()
    elif estado_actual == ESTADO_CONFIGURACION:
        escena_configuracion()
    elif estado_actual == ESTADO_ESTADISTICAS_FINALES:
        escena_estadisticas_finales()

pygame.quit()