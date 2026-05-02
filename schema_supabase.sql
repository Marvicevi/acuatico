-- ==========================================
-- SCRIPT DE INICIALIZACIÓN V2: SUPABASE (Con Menús Desplegables)
-- ==========================================

-- 0. CREACIÓN DE LISTAS DESPLEGABLES ESTRICTAS (ENUMs)
CREATE TYPE tipo_rol AS ENUM ('Nadador', 'Entrenador', 'Directiva', 'Master', 'Pendiente');
CREATE TYPE tipo_sexo AS ENUM ('Masculino', 'Femenino', 'Ambos');

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
    categoria VARCHAR(50),
    sexo tipo_sexo DEFAULT 'Masculino'
);

-- 3. Tabla de Tiempos (Competencias)
CREATE TABLE tiempos (
    id SERIAL PRIMARY KEY,
    id_nadador INTEGER REFERENCES nadadores(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    lugar VARCHAR(150),
    estilo VARCHAR(50) NOT NULL,
    tiempo_formateado VARCHAR(15) NOT NULL,
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

-- 5. Tabla de Marcas Mínimas (Objetivos separados por Sexo)
CREATE TABLE marcas_minimas (
    id SERIAL PRIMARY KEY,
    categoria VARCHAR(50) NOT NULL,
    estilo VARCHAR(50) NOT NULL,
    sexo tipo_sexo NOT NULL DEFAULT 'Masculino',
    segundos FLOAT NOT NULL,
    UNIQUE(categoria, estilo, sexo)
);

-- ==========================================
-- 6. NUEVAS TABLAS (V3)
-- ==========================================

-- 6a. Incidencias de Clase
CREATE TABLE incidencias_clase (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL,
    grupo VARCHAR(50),
    tipo VARCHAR(50) NOT NULL,  -- 'Nadador Individual' | 'Clase Completa' | 'Test Federación'
    id_nadador INTEGER REFERENCES nadadores(id) ON DELETE SET NULL,
    descripcion TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6b. Tests de Rendimiento
CREATE TABLE tests (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    fecha DATE NOT NULL,
    grupo VARCHAR(50),
    descripcion TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6c. Resultados de Tests
CREATE TABLE resultados_test (
    id SERIAL PRIMARY KEY,
    id_test INTEGER REFERENCES tests(id) ON DELETE CASCADE,
    id_nadador INTEGER REFERENCES nadadores(id) ON DELETE CASCADE,
    resultado TEXT NOT NULL,
    observaciones TEXT
);

-- 6d. Datos Fisiológicos
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

-- 6e. Tiempos de Entrenamiento
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

-- ==========================================
-- 7. DATOS INICIALES (Usuario Master)
-- ==========================================
INSERT INTO usuarios (nombre, email, clave, rol, validado) 
VALUES ('Administrador Master', 'master@club.cl', 'admin123', 'Master', true);

