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

-- 3. Tabla de Tiempos
CREATE TABLE tiempos (
    id SERIAL PRIMARY KEY,
    id_nadador INTEGER REFERENCES nadadores(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    lugar VARCHAR(150),
    estilo VARCHAR(50) NOT NULL,
    tiempo VARCHAR(15) NOT NULL, 
    segundos FLOAT NOT NULL      
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
    estilo VARCHAR(50) NOT NULL,
    sexo tipo_sexo NOT NULL DEFAULT 'Masculino',
    segundos FLOAT NOT NULL,
    UNIQUE(categoria, estilo, sexo)
);
