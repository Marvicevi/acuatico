# Club Acuático Valdivia - Sistema de Progreso de Nadadores 🏊‍♂️

**Plataforma Web (PWA)** desarrollada nativamente en Python (Streamlit) e integrada con una base de datos relacional (Supabase/PostgreSQL) para la gestión deportiva integral de atletas, consolidando asistencia, análisis de tiempos y proyección de marcas minimas mediante gráficas de radar (Spider Charts).

---

## 👥 Sistema de Perfiles y Roles (Permisos)

La aplicación utiliza un esquema de acceso cerrado por seguridad:
* **No hay registro público.** Nadie puede crear su propia cuenta desde el exterior.
* Todas las contraseñas están almacenadas en base de datos. Cada usuario puede modificar su propia contraseña en cualquier momento usando el menú "⚙️ Mi Cuenta".

Existen **4 niveles de acceso** con interfaces condicionales:

### 1. 👑 Master (Super Administrador)
Tiene control absoluto y global del club y la aplicación.
* **Acceso exclusivo** a la pestaña **"🛡️ Admin Usuarios"**, desde la cual puede *crear* cuentas para el resto del equipo (Entrenadores, Directiva, Nadadores).
* Puede asignar explícitamente a qué "Grupos" tiene acceso y autoridad cada entrenador al momento de crear sus cuentas.
* Visualiza todos los perfiles, todos los tableros analíticos y puede ingresar tiempos o asistencias para cualquier miembro.

### 2. 📋 Entrenador
Su visión está acotada estrictamente a los **Grupos Asignados** bajo su tutela.
* **📊 Dashboard:** Análisis tabular y gráfico individual de los alumnos de su grupo.
* **🗓️ Asistencia:** Interfaz de tabla ágil para tomar lista diaria por grupo.
* **👥 Perfiles:** Interfaz gráfica para registrar nuevos nadadores, editar su categoría o cambiar su género (Menú desplegable estricto de Supabase).
* **⏱️ Registrar Tiempos:** Inserción guiada o por carga masiva usando archivos Excel/CSV de las competencias.
* **⚙️ Configurar Marcas:** Control sobre las métricas deportivas (tiempos mínimos) de la temporada para que los atletas se comparen.

### 3. 👁️ Directiva (Presidente / Directorio)
Perfil diseñado puramente para supervisión a gran escala y soporte administrativo.
* **Supervisión Global:** Tienen acceso al **📊 Dashboard Global**, pudiendo ver resúmenes generales de *todo el club* (todos los grupos del Master y Entrenadores). Esta vista inicialmente es de Solo Lectura.
* **Colaboradores Operativos:** Para apoyar la labor técnica, la Directiva cuenta con permisos para ayudar a subir planillas masivas de **⏱️ Registrar Tiempos** y ayudar a **⚙️ Configurar Marcas Mínimas** base.
* Tienen bloqueada la toma de 🗓️ Asistencia y la creación biográfica de 👥 Perfiles, salvaguardando ese registro para los técnicos.

### 4. 🏊‍♂️ Nadador (Próximamente disponible en UI total)
Perfil de lectura personal.
* Visualización hermética: El nadador solamente puede ver sus propios registros, sus asistencias y cómo rinden sus últimos tiempos (Spider Chart) en relación a su categoría y categorías de competidores superiores.
* Bloqueo a la información o registros de sus compañeros.

---

## 🚀 Despliegue en la Nube (Deployment Instructions)

### 1. Configuración de Base de Datos (Supabase)
1. Créate una cuenta en [Supabase](https://supabase.com/).
2. Crea un nuevo proyecto.
3. Ve a la sección **SQL Editor**. Abre el archivo local `schema_supabase.sql` que se encuentra en esta carpeta, cópialo entero y ejecútalo (Run).
   * Este script generará automáticamente las tablas (`usuarios`, `nadadores`, `tiempos`, `asistencias`, `marcas_minimas`), los Tipos Desplegables ENUM (`tipo_rol`, `tipo_sexo`), y **creará tu primer usuario administrador** (`master@club.cl`).
4. Ve a *Settings > API* y copia dos cosas: El **URL** del proyecto y el **`anon` public API Key**.

### 2. Configuración del Servidor y UI (Streamlit Cloud)
1. Sube todo el contenido de esta carpeta (este repositorio) a [GitHub](https://github.com).
2. Ingresa a [Streamlit Community Cloud](https://share.streamlit.io/) e inicia sesión con tu cuenta de GitHub.
3. Selecciona **New App** y despliega a partir del repositorio recién subido. Usa siempre la ruta primaria: `app.py`.
4. **Vínculo Seguro (Secrets):**
   * Antes de presionar el último botón *Deploy*, ve a la sección inferior de **Advanced Settings...**.
   * Pega allí las llaves de Supabase usando el siguiente formato exacto (TOML):
   ```toml
   [supabase]
   SUPABASE_URL = "https://tu-url.supabase.co"
   SUPABASE_KEY = "tu-llave-anonima-publica"
   ```
5. Guarda (Save) y Ejecuta (Deploy).

*Listo! El sistema está vivo, enlazado, configurado y asegurado para todos tus dispositivos.*

---

## 📱 Uso en Dispositivos Móviles (App)

La aplicación está diseñada para ser completamente responsiva, por lo que **funciona perfectamente tanto en Android como en iPhone (iOS)**. No necesitas publicarla en la App Store ni en Google Play Store.

Para que los usuarios la tengan en su celular como si fuera una aplicación nativa (con su ícono propio y sin barra de direcciones web), deben seguir estos simples pasos:

### Para usuarios de iPhone (iOS):
1. Abre el navegador **Safari**.
2. Ingresa al enlace (URL) de la aplicación.
3. Toca el ícono de **Compartir** (el cuadrado con una flecha apuntando hacia arriba, en la parte inferior de la pantalla).
4. Desplázate hacia abajo y selecciona **"Agregar a inicio"** (Add to Home Screen).
5. Toca en **"Agregar"** en la esquina superior derecha.
6. ¡Listo! Verás el ícono de la app en la pantalla de inicio de tu iPhone.

### Para usuarios de Android:
1. Abre el navegador **Google Chrome**.
2. Ingresa al enlace (URL) de la aplicación.
3. Toca el ícono de **Menú** (los tres puntos verticales en la esquina superior derecha).
4. Selecciona **"Agregar a la pantalla principal"** (Add to Home screen) o "Instalar aplicación".
5. Toca en **"Agregar"** o "Instalar" para confirmar.
6. ¡Listo! La aplicación aparecerá junto al resto de las apps en tu teléfono.
