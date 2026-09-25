# Inteligencia en Red - Grupo 13

## Estructura

- `bots/botGrupo13_v0/` - bot inicial de la E0
- `bots/botGrupo13_v1/` - el que mandamos como v0 al torneo (sale así en el dataset)
- `E0...pdf`, `E1...pdf` - enunciados

El dataset (`dataset_v0.csv`, 280 MB) no está subido porque pasa del límite de GitHub. Se descarga de AulaGlobal y se pone en `dataset_v0 (1)/`.

## Reparto E1

**Persona A - Búsqueda + evaluación (apartado 1)**
- 1.1 comprobar a mano el coste de 3 celdas y la zona más peligrosa
- 1.2 formulación del problema (estado, estado inicial, acciones, objetivo, coste)
- 1.3 coste uniforme: tabla, camino, coste y nodos expandidos
- 1.4 A* con heurística (Manhattan): tabla, camino, coste y nodos expandidos
- 1.5 comparación + coste de ir recto por la fila 0
- evaluación v0 vs v1 (batallas y resultados)
- Memoria: secciones 1, 2, 3, 4, 5 y 9

**Persona B - Reglas + bot v1 (apartado 2)**
- 2.1 hechos que usa el bot y valor de N para "visto"
- 2.3 tabla de reglas (6-12) con umbrales justificados
- 2.4 resolución de conflictos, disparar vs retirarse y completitud
- 2.6 programar el v1 con el esqueleto del enunciado + zip
- Memoria: secciones 6, 7 y 8 + montaje final

**Los dos**
- sección 10 (uso de IA), cada uno lo suyo
- la regla de retirada se cuadra con lo que salga de la búsqueda
- el bot v1 hay que hacerlo nuevo, el de la carpeta `botGrupo13_v1` no sigue el esqueleto
