-- BORRADO PREVIO PARA EVITAR ERRORES (CASCADE borra las tablas que dependen de ellos)
DROP TABLE IF EXISTS asistencias, tiempos, nadadores, marcas_minimas, usuarios, incidencias_clase, tests, resultados_test, datos_fisicos, tiempos_entrenamiento CASCADE;
DROP TYPE IF EXISTS tipo_rol, tipo_sexo, tipo_estilo, tipo_categoria CASCADE;

-- ==========================================
-- SCRIPT DE INICIALIZACIÓN V2: SUPABASE (Con Menús Desplegables)
-- ==========================================

-- 0. CREACIÓN DE LISTAS DESPLEGABLES ESTRICTAS (ENUMs)
CREATE TYPE tipo_rol AS ENUM ('Nadador', 'Entrenador', 'Directiva', 'Master', 'Pendiente');
CREATE TYPE tipo_sexo AS ENUM ('Masculino', 'Femenino', 'Ambos');

-- 0.1 CREACIÓN DE LISTA DE ESTILOS (ENUM)
CREATE TYPE tipo_estilo AS ENUM (
    '50 Libre', '100 Libre', '200 Libre', '400 Libre', '800 Libre', '1500 Libre',
    '50 Espalda', '100 Espalda', '200 Espalda',
    '50 Pecho', '100 Pecho', '200 Pecho',
    '50 Mariposa', '100 Mariposa', '200 Mariposa',
    '100 IM', '200 IM', '400 IM'
);

-- Nuevas Categorías solicitadas
CREATE TYPE tipo_categoria AS ENUM (
    'Infantil A', 'Infantil B1', 'Infantil B2', 
    'Juvenil A1', 'Juvenil A2', 'Juvenil B', 'Mayores'
);

-- 1. Tabla de Usuarios (Autenticación y Roles)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    clave VARCHAR(255) NOT NULL, 
    rol tipo_rol DEFAULT 'Pendiente', 
    validado BOOLEAN DEFAULT false,
    grupos_asignados TEXT[] DEFAULT '{}' 
);

-- 2. Tabla de Nadadores
CREATE TABLE nadadores (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    grupo VARCHAR(50), 
    categoria tipo_categoria NOT NULL,
    sexo tipo_sexo DEFAULT 'Masculino'
);

-- 3. Tabla de Tiempos
CREATE TABLE tiempos (
    id SERIAL PRIMARY KEY,
    id_nadador INTEGER REFERENCES nadadores(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    lugar VARCHAR(150),
    estilo tipo_estilo NOT NULL, -- Cambiado de VARCHAR a tipo_estilo
    -- 'tiempo_formateado' guarda el texto "01:23,45" para mostrar en la app
    tiempo_formateado VARCHAR(15) NOT NULL, 
    -- 'segundos_totales' es lo que Supabase usa para ordenar de menor a mayor (el más rápido)
    segundos_totales FLOAT NOT NULL,
    tipo_piscina VARCHAR(30)
);

-- 4. Tabla de Asistencias
CREATE TABLE asistencias (
    id SERIAL PRIMARY KEY,
    id_nadador INTEGER REFERENCES nadadores(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    estado VARCHAR(20) DEFAULT 'Ausente', 
    UNIQUE(id_nadador, fecha) 
);

-- ==========================================
-- 5. DATOS INICIALES (Usuario Master)
-- ==========================================
INSERT INTO usuarios (nombre, email, clave, rol, validado) 
VALUES ('Administrador Master', 'master@club.cl', 'admin123', 'Master', true);

-- 6. Tabla de Marcas Mínimas (Objetivos separados por Sexo)
CREATE TABLE marcas_minimas (
    id SERIAL PRIMARY KEY,
    categoria VARCHAR(50) NOT NULL,
    estilo tipo_estilo NOT NULL, -- Cambiado de VARCHAR a tipo_estilo
    sexo tipo_sexo NOT NULL DEFAULT 'Masculino',
    tiempo_objetivo VARCHAR(15), -- Formato MM:SS,MS
    segundos_objetivo FLOAT NOT NULL,
    UNIQUE(categoria, estilo, sexo)
);

-- ==========================================
-- 7. NUEVAS TABLAS (V3)
-- ==========================================

-- 7a. Incidencias de Clase
CREATE TABLE incidencias_clase (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    grupo VARCHAR(50),
    tipo VARCHAR(50) NOT NULL,  -- 'Nadador Individual' | 'Clase Completa' | 'Test Federación'
    id_nadador INTEGER REFERENCES nadadores(id) ON DELETE SET NULL,
    descripcion TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 7b. Tests de Rendimiento
CREATE TABLE tests (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    fecha DATE NOT NULL,
    grupo VARCHAR(50),
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 7c. Resultados de Tests
CREATE TABLE resultados_test (
    id SERIAL PRIMARY KEY,
    id_test INTEGER REFERENCES tests(id) ON DELETE CASCADE,
    id_nadador INTEGER REFERENCES nadadores(id) ON DELETE CASCADE,
    resultado TEXT NOT NULL,
    observaciones TEXT
);

-- 7d. Datos Fisiológicos
CREATE TABLE datos_fisicos (
    id SERIAL PRIMARY KEY,
    id_nadador INTEGER REFERENCES nadadores(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    estatura_cm FLOAT,        -- talla de pie (cm)
    peso_kg FLOAT,            -- peso corporal (kg)
    envergadura_cm FLOAT,     -- distancia punta-punta con brazos extendidos (cm)
    talla_sentado_cm FLOAT,   -- longitud de tronco sentado (cm)
    porc_grasa FLOAT,         -- % de grasa corporal estimado
    observaciones TEXT
);

-- 7e. Tiempos de Entrenamiento
CREATE TABLE tiempos_entrenamiento (
    id SERIAL PRIMARY KEY,
    id_nadador INTEGER REFERENCES nadadores(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    prueba VARCHAR(100) NOT NULL,
    tiempo_formateado VARCHAR(15),
    segundos_totales FLOAT,
    serie INTEGER DEFAULT 1,
    tipo_piscina VARCHAR(30),
    observaciones TEXT
);
