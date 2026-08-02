# 🕹️ ScoreBridge Arcade Sync

Sistema de automatización para capturar puntuaciones altas (.hi) de emuladores en RetroArch (como FinalBurn Neo), procesarlas mediante un script de Python y sincronizarlas automáticamente con **iScored**, integrado de forma fluida con frontends como **Attract-Mode Plus**.

Tras seleccionar un juego en Attract Mode Plus (AM+) y ser lanzado en RetroArch, al terminar la partida, ScoreBridge buscará tus iniciales en el fichero .hi de tus puntuaciones, y sólo subirá si es mayor a la que tengas previamente en iSocred, por lo que sólo guarda una única puntuación (la más alta LoL)

---

## 📋 Prerrequisitos en Windows

Antes de configurar el proyecto, asegúrate de tener instalado en tu sistema:
1. **Python** (versión 3.x recomendada). Asegúrate de marcar la casilla *"Add Python to PATH"* durante la instalación.
2. **RetroArch** configurado con los cores necesarios (ej. `fbneo_libretro.dll`).
3. **Attract-Mode Plus** como frontend de juegos.

---

## ⚙️ Instalación y Configuración Paso a Paso

### 1. Clonar o descargar el repositorio
Coloca la carpeta del proyecto en la ruta de tu elección (por ejemplo, `C:\AttractModePlus\ScoreBridge\`).

### 2. Instalar Python
Instalar desde https://www.python.org/downloads/ 

### 3. Instalar dependencias de Python
Abre una terminal (CMD o PowerShell) en la carpeta del proyecto e instala la librería necesaria para las peticiones web:

pip install requests

### 4. Revisar el fichero config_example.json
Modificar los siguientes valores y guardar el fichero como config.json:

default_initials --> poner tus iniciales por defecto. 

hi_folder --> ruta a la carpeta donde RetroArch almacena los archios .hi

gameroom --> nombre de tu gameroom en iSocred

games --> conforme juegues a nuevos juegos desde RetroArch, se irán agregando de manera automática a este apartado en el propio fichero, pero dejará vacío 'iscored_id' para que lo pongas tú a mano, según tu cuenta de iScored

### 5. Revisar el fichero loader_example.bat
En la configuración del emulador de AM+, debes hacer que el ejecutable apunte al loader.bat, algo de este estilo:

executable           C:\AttractModePlus\ScoreBridge\loader.bat
args                 "[romfilename]"
rompath              C:\AttractModePlus\collections\Arcade\roms\
workpath             C:\RetroArch\
romext               .zip
system               Arcade
artwork    snap      collections\Arcade\snap
artwork    wheel     collections\Arcade\logo
artwork    marquee   collections\Arcade\marquee

En mi caso, por un lado tengo una carpeta con Retroarch, y por otro una carpeta con AM+, y dentro del mismo tengo ScoreBridge