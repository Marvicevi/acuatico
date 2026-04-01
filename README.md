# Sistema de Progreso: Club Acuático Valdivia 🏊‍♂️

Bienvenido al repositorio del Sistema de Progreso de Nadadores. Esta aplicación web permite a entrenadores, directiva, master y nadadores realizar un seguimiento detallado y basado en datos del rendimiento en los distintos estilos de natación a lo largo del tiempo.

## Arquitectura y Distribución (PWA)

Esta aplicación está construida sobre **Python** y **Streamlit** y se conecta a una base de datos relacional gratuita en **Supabase** (PostgreSQL).

**Estrategia de Distribución:** No es necesario pagar licencias de App Store (Apple) ni Google Play. Al ser desplegada en *Streamlit Community Cloud*, la aplicación funciona como una **PWA (Progressive Web App)** nativa y responsiva.
1. Los usuarios acceden a través de un simple enlace URL (ej: *miapp.streamlit.app*).
2. En sus teléfonos móviles (Safari o Chrome), seleccionan "Agregar a la Pantalla de Inicio".
3. Al instante, tendrán el ícono del club en la pantalla de sus celulares, abriéndose como una aplicación nativa, a pantalla completa y libre de distracciones.

## Roles del Sistema (Simulación OAuth)
El proyecto incluye un flujo de validación basado en correos electrónicos.
- **Master**: Valida a los usuarios nuevos que se registren simulando el inicio con su cuenta de Google.
- **Entrenador**: Visualiza el resumen de sus grupos (ej. *Elite* o *Juvenil*), evalúa distancias contra marcas mínimas, y toma la asistencia con un solo clic.
- **Directiva**: Posee visión global (Solo lectura) sobre todo el desempeño del club.
- **Nadador**: Puede visualizar únicamente su propio progreso.

## Configuración de Base de Datos (Supabase)
Esta aplicación utiliza Supabase (PostgreSQL) para alojar todos los datos. Sigue estos pasos para configurarlo:

1. Ingresa a [supabase.com](https://supabase.com/).
2. Crea un **New Project**. En la pantalla de creación:
   - **Enable Data API**: **DEJA MARCADA** esta opción (es la que nos permite conectar la aplicación Streamlit directo a la base de datos).
   - **Enable automatic RLS**: **DESMARCA** esta opción. Para esta etapa de prototipo, el sistema validará los accesos y los roles internamente. Si lo dejas activado, Supabase bloqueará las lecturas (Row Level Security) y no podrás ver ninguna marca ni asistencia en tu aplicación.
3. Ve a la pestaña **SQL Editor** en el panel izquierdo de Supabase. Abre un *New Query*, pega todo el código del archivo local `schema_supabase.sql` y ejecútalo (Run). Esto construirá todas tus tablas automáticamente.
4. Para finalizar, ve al menú **Project Settings** (el engranaje) -> **API** y copia los dos valores clave: tu `Project URL` y tu `Project API Key (anon-public)`.

## Requisitos y Configuración Local

1. Prepara tu entorno virtual (si no lo tienes activo):
    ```bash
    source .venv/bin/activate
    ```
2. Instala las dependencias:
    ```bash
    pip install -r requirements.txt
    ```
3. Crea un archivo llamado `.streamlit/secrets.toml` y pega tu URL y Llave recién creadas:
    ```toml
    [supabase]
    SUPABASE_URL = "https://TU_URL.supabase.co"
    SUPABASE_KEY = "TU_LLAVE_ANONIMA"
    ```
4. Lanza la aplicación localmente de prueba:
    ```bash
    streamlit run app.py
    ```

## Despliegue en la Nube
Para lanzar esta app al público de manera gratuita:
1. Sube este directorio a un repositorio **público** en **GitHub**.
2. Ingresa a `share.streamlit.io` y vincula tu cuenta de GitHub.
3. Despliega la aplicación apuntando hacia el archivo principal `app.py`.
4. En el panel de control de Streamlit, ve a  `Settings` > `Secrets` y pega el mismo contenido de tu archivo `.streamlit/secrets.toml` local.
