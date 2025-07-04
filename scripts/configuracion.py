#FELIX ANTONIO MERCEDES MERCEDES
#21-EISN-2-047
import pygame
import os
import random

pygame.init()
pygame.mixer.init()
pygame.joystick.init() 

#constantes del juego
ANCHO_PANTALLA = 800
ALTO_PANTALLA = 600
FPS = 60
TILE_SIZE = 32
SPRITE_SCALE_FACTOR = 1.5
SCALED_TILE_SIZE = int(TILE_SIZE * SPRITE_SCALE_FACTOR)
OBSTACLE_SIZE = TILE_SIZE #todos los obstaculos tendran el mismo tamaño

#colores del que usaremos
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
ROJO = (255, 0, 0)
VERDE = (0, 255, 0)
AZUL = (0, 0, 255)
GRIS_OSCURO = (50, 50, 50)
MARRON = (139, 69, 19)
VERDE_OSCURO = (0, 100, 0)
NARANJA = (255, 165, 0)
AMARILLO = (255, 255, 0)
CYAN = (0, 255, 255)
VERDE_PASTO = (34, 139, 34)  #color que simula un pasto dentro de la partida

#configuracion de la pantalla
PANTALLA = pygame.display.set_mode((ANCHO_PANTALLA, ALTO_PANTALLA))
pygame.display.set_caption("THE CHAOS ENGINE CLONE")
RELOJ = pygame.time.Clock()

#rutas de los activos (assest)
CARPETA_RAIZ_JUEGO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_ACTIVOS = os.path.join(CARPETA_RAIZ_JUEGO, "assets")

CARPETA_SONIDOS = os.path.join(CARPETA_ACTIVOS, "sonidos")
CARPETA_MENU = os.path.join(CARPETA_ACTIVOS, "menu")
CARPETA_ENEMIGOS = os.path.join(CARPETA_ACTIVOS, "enemigos")
CARPETA_MOVIMIENTOS = os.path.join(CARPETA_ACTIVOS, "movimientos")
CARPETA_MERCENARIOS = os.path.join(CARPETA_ACTIVOS, "mercenarios")
CARPETA_POWERUPS = os.path.join(CARPETA_ACTIVOS, "powerups")
CARPETA_INTRO = os.path.join(CARPETA_ACTIVOS, "intro")
CARPETA_OBSTACULOS = os.path.join(CARPETA_ACTIVOS, "obstaculos")
CARPETA_EXPLOCION = os.path.join(CARPETA_ACTIVOS, "explocion")
CARPETA_PREMIO = os.path.join(CARPETA_ACTIVOS, "premio")

CARPETA_MOVIMIENTO = os.path.join(CARPETA_ACTIVOS, "movimientoplayer1")
CARPETA_MOVIMIENTO_ENEMIGOS = os.path.join(CARPETA_ACTIVOS, "movimientoenemigo")

#carga de imagenes y sonidos
ASSETS = {}

def cargar_imagen(ruta, nombre, scale_to_tile=False):
    """Función para cargar imágenes desde archivos"""
    ruta_completa = os.path.join(ruta, nombre)
    try:
        imagen = pygame.image.load(ruta_completa).convert_alpha()
        if scale_to_tile:
            imagen = pygame.transform.scale(imagen, (SCALED_TILE_SIZE, SCALED_TILE_SIZE))
        return imagen
    except pygame.error as e:
        print(f"Error cargando imagen {nombre} de {ruta_completa}: {e}")
        return None

def cargar_sonido(ruta, nombre):
    """Función para cargar sonidos desde archivos"""
    ruta_completa = os.path.join(ruta, nombre)
    try:
        sonido = pygame.mixer.Sound(ruta_completa)
        return sonido
    except pygame.error as e:
        print(f"Error cargando sonido {nombre} de {ruta_completa}: {e}")
        return None

def cargar_todos_los_assets():
    """Función para cargar todos los assets del juego"""

    ASSETS['sonido_intro'] = cargar_sonido(CARPETA_SONIDOS, "intro.wav")
    ASSETS['sonido_menu'] = cargar_sonido(CARPETA_SONIDOS, "menu.wav")
    ASSETS['sonido_mapa1'] = cargar_sonido(CARPETA_SONIDOS, "mapa1.wav")
    ASSETS['sonido_perdiste'] = cargar_sonido(CARPETA_SONIDOS, "perdiste.wav")
    ASSETS['sonido_powerup'] = cargar_sonido(CARPETA_SONIDOS, "powerup.wav")
    ASSETS['sonido_explocion'] = cargar_sonido(CARPETA_SONIDOS, "explocion.wav")
    ASSETS['sonido_victoria'] = cargar_sonido(CARPETA_SONIDOS, "victoria.wav")

    ASSETS['el_bandido'] = cargar_imagen(CARPETA_MERCENARIOS, "El bandido.png")
    ASSETS['el_caballero'] = cargar_imagen(CARPETA_MERCENARIOS, "El caballero.png")
    ASSETS['el_maton'] = cargar_imagen(CARPETA_MERCENARIOS, "El Maton.png")
    ASSETS['el_mercenario'] = cargar_imagen(CARPETA_MERCENARIOS, "El mercenario.png")

    ASSETS['obstaculo_arbusto'] = cargar_imagen(CARPETA_OBSTACULOS, "arbusto.png")
    ASSETS['piedra'] = cargar_imagen(CARPETA_OBSTACULOS, "piedra.png")

    ASSETS['explocion_sprite_sheet'] = cargar_imagen(CARPETA_EXPLOCION, "explocion.png")

    ASSETS['powerup_bonusx2'] = cargar_imagen(CARPETA_POWERUPS, "bonusx2.png")
    ASSETS['powerup_estrella'] = cargar_imagen(CARPETA_POWERUPS, "estrella.png")
    ASSETS['powerup_tnt'] = cargar_imagen(CARPETA_POWERUPS, "tnt.png")
    ASSETS['powerup_vida'] = cargar_imagen(CARPETA_POWERUPS, "vida.png")

    ASSETS['intro1'] = cargar_imagen(CARPETA_INTRO, "intro1.png")
    ASSETS['intro2'] = cargar_imagen(CARPETA_INTRO, "intro2.png")

    ASSETS['copa'] = cargar_imagen(CARPETA_PREMIO, "copa.png")

    ASSETS['torreta_sprite_sheet'] = cargar_imagen(os.path.join(CARPETA_MOVIMIENTO_ENEMIGOS, "enemigo5"), "torreta.png")

volumen_global = 0.5
pygame.mixer.music.set_volume(volumen_global)

estrellas = []
for _ in range(200):
    x = random.randint(0, ANCHO_PANTALLA)
    y = random.randint(0, ALTO_PANTALLA)
    tamano = random.randint(1, 3)
    estrellas.append((x, y, tamano))

def dibujar_fondo_estrellado():
    """Función para dibujar un fondo estrellado"""
    PANTALLA.fill(NEGRO)
    for x, y, tamano in estrellas:
        pygame.draw.circle(PANTALLA, BLANCO, (x, y), tamano)

VELOCIDAD_GENERAL = 3
PLAYER_COLLISION_DAMAGE = 10
PLAYER_INVULNERABILITY_DURATION = 1000
BULLET_SPEED = 8
BULLET_DAMAGE_MIN = 15
BULLET_DAMAGE_MAX = 25
ENEMY_BULLET_SPEED = 7
ENEMY_BULLET_DAMAGE = 15
ENEMY_SHOOT_COOLDOWN = 1000
ENEMY_DETECTION_RANGE = 200
AIM_ASSIST_RANGE = 250
OBSTACLE_DAMAGE = 5
ENEMY_MELEE_DAMAGE = 20
ENEMY_MELEE_COOLDOWN = 750
TURRET_SHOOT_COOLDOWN = 1000
TURRET_DETECTION_RANGE = 300

#grid para el A*
WORLD_WIDTH = 4000  
WORLD_HEIGHT = 4000 
GRID_ANCHO = WORLD_WIDTH // TILE_SIZE
GRID_ALTO = WORLD_HEIGHT // TILE_SIZE
grid_mapa_actual = [[0 for _ in range(GRID_ALTO)] for _ in range(GRID_ANCHO)]

ESTADO_INTRO = 0
ESTADO_MENU = 1
ESTADO_SELECCION_PERSONAJE = 2
ESTADO_JUEGO = 3
ESTADO_PAUSA = 4
ESTADO_FIN_JUEGO = 5 
ESTADO_DERROTA = 6
ESTADO_CONFIGURACION = 7
ESTADO_ESTADISTICAS_FINALES = 8  

ENEMY_NAMES_MAP = {
    "enemigo1": "Nefasto",
    "enemigo2": "Inquisidor", 
    "enemigo3": "Siniestro",
    "enemigo4": "Vandal",
    "enemigo5": "Torreta"
}

NIVEL_ACTUAL = 1
MAX_NIVELES = 3

joystick_threshold_menu = 0.5
joystick_moved_y = False
joystick_moved_x = False

grupo_explosiones = pygame.sprite.Group()
grupo_powerups = pygame.sprite.Group()
grupo_indicadores_daño = pygame.sprite.Group()  
grupo_indicadores_daño_jugador = pygame.sprite.Group() 
grupo_enemigos = pygame.sprite.Group()
grupo_torretas = pygame.sprite.Group()
grupo_balas_jugador = pygame.sprite.Group()
grupo_balas_enemigo = pygame.sprite.Group()
grupo_obstaculos_actual = pygame.sprite.Group()

cargar_todos_los_assets()