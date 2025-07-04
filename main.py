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