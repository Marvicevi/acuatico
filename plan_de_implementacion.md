# Plan de Implementación: Sistema de Progreso de Nadadores

Este documento contiene el plan paso a paso para transformar el prototipo actual a una aplicación completamente funcional, responsiva, gratuita y escalable, según los requerimientos.

## 1. Arquitectura y Herramientas (Gratuitas y Escalables)
*   **Frontend / Backend**: Mantendremos **Streamlit** por ahora, desplegado en **Streamlit Community Cloud**. Es 100% gratuito, se conecta directamente a GitHub y es razonablemente responsivo para móviles. Si a futuro se requiere un frontend más personalizado o complejo, se podría migrar fácilmente a Next.js (React) gracias a que la base de datos estará separada.
*   **Base de Datos**: **Supabase** (basado en PostgreSQL). Ofrece un generoso plan gratuito "Forever Free", incorpora sistema de login, almacenamiento y una base de datos relacional impecable para manejar atletas, tiempos y asistencias. Además, al ser PostgreSQL estándar, el día que desees escalar, puedes migrar tu base de datos a cualquier otro proveedor (AWS, Google Cloud) sin modificar tu estructura.
*   **Despliegue (Flujo)**: Usaremos **GitHub** como repositorio de código. Al momento de conectar con Streamlit Cloud, cualquier actualización que hagamos al código se desplegará en la aplicación en línea casi al instante.

## 2. Ajuste a la Gráfica de Progreso
*   **Problema actual**: La gráfica hace parecer que tener mayores "puntos" es mejor, pero en natación el menor tiempo es lo deseado.
*   **Solución a Implementar**: Modificaremos la matemática de la gráfica (ya sea invirtiendo la escala del radar en Plotly (`autorange="reversed"`) o calculando un porcentaje de "Mejora respecto a la marca mínima", de manera que el límite exterior sea la meta y los tiempos se representen intuitivamente para visualizar qué tan lejos o cerca se está del objetivo real).

## 3. Créditos de Desarrollador
*   Inyectaremos un componente fijo (`st.markdown` en el footer) que dirá **"Desarrollado por Marco Cedeño"** usando un estilo amigable, moderno y proporcionado, enlazando directamente al LinkedIn (www.linkedin.com/in/marcocede).

## 4. Importar/Exportar Datos (Modelos Excel/CSV)
*   Agregaremos botones para descargar una plantilla vacía de `Excel/CSV` con el encabezado y estructura correctos.
*   Incluiremos un componente para cargar `(file uploader)` múltiples marcas a la vez. El sistema validará que el archivo cargado no contenga errores, e insertará todas las marcas subidas de los nadadores en la base de datos de manera masiva.

## 5. Control de Asistencia Mejorado
*   **Fecha**: El entrenador seleccionará una sola fecha desde un `st.date_input`.
*   **Botonera**: Para cada nadador listado para un grupo en particular ese día, sustituiremos la caja de verificación múltiple por una vista tabular, o botones directos de estado único **"Presente" / "Ausente"**, el cual guardará la información relacionada con la fecha unificada y cada ID individual.

---

## ▶ Carga de Trabajo / Pasos de Acción
1. **Configuración de Base de Datos**: Crear nuestro esquema de base de datos en Supabase (Tablas de *Usuarios, Nadadores, Tiempos, Asistencias*).
2. **Refactorización de `app.py`**: Conectar la aplicación a Supabase para dejar de usar la data 'de mentira' cargada actualmente (usando `st.secrets`).
3. **Módulo Tiempos (Excel/CSV)**: Implementar la carga y descarga masiva de plantillas en la app para registros de tiempo.
4. **Módulo Asistencia**: Remodelar la UI para la toma de asistencia.
5. **Ajuste del Gráfico**: Configurar la gráfica de Plotly correctamente para tiempos.
6. **Módulo Footer/Créditos**: Incorporar los créditos de desarrollador.
7. **Despliegue a la Nube**: Subir todo a GitHub y enlazar con Streamlit Cloud.
