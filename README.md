# Detección de documentos casi duplicados

Proyecto de Análisis de Grandes Volúmenes de Datos. Compara firmas MinHash y
SuperMinHash, con una extensión a FracMinHash y LSH, para detectar documentos
casi duplicados. El corpus seleccionado es 20 Newsgroups.

## Estado actual

- Carga de las versiones `bydate` y `original` de 20 Newsgroups.
- Perfil de datos y detección descriptiva de copias exactas.
- Normalización mínima, tokenización y generación de shingles de palabras.
- Pruebas unitarias para la carga, normalización y shingles.
- El baseline exacto, MinHash, SuperMinHash, FracMinHash y LSH están pendientes.

## Requisitos

Python 3.10 o posterior. El cargador y los scripts actuales usan solo la
biblioteca estándar; no hace falta instalar paquetes de Python.

## Ejecutar

Desde la raíz del repositorio:

```bash
# Descargar y resumir ambas versiones (o usar archivos ya guardados en data/raw)
python3 src/loader.py --version both

# Perfil descriptivo de ambas versiones
python3 src/profile_data.py

# Aplicar la limpieza actual y medir shingles de cinco palabras
python3 src/profile_shingling.py --k 5

# Ejecutar las pruebas
python3 -m unittest discover -s tests -v
```

Los cargadores descargan automáticamente los archivos desde las fuentes
indicadas en el código. Los archivos originales se guardan en `data/raw/` y no
se incluyen en Git; así se evita duplicar en el repositorio los mensajes del
corpus.

Los perfiles generados se guardan en `data/profiles/`.

## Limpieza y shingles actuales

- Normalización Unicode NFKC, conversión a minúsculas y unificación de espacios.
- Eliminación heurística de cabeceras de correo reconocibles y de la firma
  posterior a una línea `--`.
- Se conserva el contenido citado; no se eliminan palabras comunes ni se aplica
  stemming.
- Los tokens son secuencias Unicode alfanuméricas; los números se conservan.
- Cada shingle es una ventana deslizante de cinco palabras y los shingles de un
  documento se almacenan como un conjunto.

Esta política es inicial y puede cambiarse antes de fijar los experimentos.

## Material del proyecto y del paper

- `presentacion/`: propuesta del proyecto en Beamer y PDF.
- `presentacion_superminhash/`: presentación del paper, PDF con notas, ejemplo
  detallado del algoritmo, figuras y fuentes LaTeX.
- `SuperMinHash2017.pdf`: paper recomendado por la profesora.
- `ProyectoSemestral_2026.pdf`: instrucciones del proyecto.
- `propuesta.txt`: propuesta aprobada.

Las presentaciones Beamer pueden recompilarse con `make` dentro de sus
respectivas carpetas, teniendo instalados los paquetes LaTeX requeridos.
