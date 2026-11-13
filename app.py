# ========================================
# Archivo Único: app.py
# Guarda todo este código en un solo archivo llamado app.py
# y corre el comando: streamlit run app.py
# ========================================

import hashlib
import hmac
import time

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
try:
    from supabase import create_client, Client
except ImportError:
    pass

def convertir_tiempo_a_segundos(tiempo_str):
    """Convierte formato MM:SS,MS a float de segundos totales."""
    try:
        # Reemplazamos la coma por punto para que Python lo entienda como decimal
        tiempo_limpio = tiempo_str.replace(',', '.')
        if ':' in tiempo_limpio:
            minutos, resto = tiempo_limpio.split(':')
            return float(int(minutos) * 60 + float(resto))
        return float(tiempo_limpio)
    except Exception:
        return 0.0


def formatear_tiempo_con_icono(row):
    """Devuelve el tiempo formateado con un ícono según el tipo de piscina."""
    tiempo = row.get('tiempo_formateado', row.get('tiempo', ''))
    tipo = str(row.get('tipo_piscina', ''))
    if 'Corta' in tipo:
        return f"🏊 {tiempo}"
    elif 'Larga' in tipo:
        return f"🌊 {tiempo}"
    return str(tiempo)


def segundos_a_tiempo(secs):
    """Convierte segundos (float) al formato MM:SS,MS para mostrar al usuario."""
    try:
        secs = float(secs)
        minutos = int(secs // 60)
        resto = secs - minutos * 60
        return f"{minutos:02d}:{resto:05.2f}".replace('.', ',')
    except:
        return str(secs)


# Temporada en la que las categorías ya guardadas son válidas.
# La edad FECHIDA es la cumplida al 31 de diciembre: año de temporada − año de nacimiento.
# 2026 − 11 = 2015 para Infantil A. No usar 2011: en 2026 ese año es Juvenil A2 (15 años).
ANIO_DE_CATEGORIAS_GUARDADAS = 2026

# (edad desde, edad hasta, categoría). Juvenil A1 = 14 y Juvenil A2 = 15.
TRAMOS_CATEGORIA = [
    (8, 8, "Infantil E"),
    (9, 9, "Infantil D"),
    (10, 10, "Infantil C"),
    (11, 11, "Infantil A"),
    (12, 12, "Infantil B1"),
    (13, 13, "Infantil B2"),
    (14, 14, "Juvenil A1"),
    (15, 15, "Juvenil A2"),
    (16, 18, "Juvenil B"),
    (19, 120, "Mayores"),
]

# Solo estas categorías permiten deducir un único año. Juvenil B y Mayores abarcan varios.
EDAD_UNICA_POR_CATEGORIA = {
    "Infantil E": 8,
    "Infantil D": 9,
    "Infantil C": 10,
    "Infantil A": 11,
    "Infantil B1": 12,
    "Infantil B2": 13,
    "Juvenil A1": 14,
    "Juvenil A2": 15,
}


def _anio_entero(valor):
    """Devuelve un año como int, o None si el valor está vacío."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except TypeError:
        pass
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


def fichas_por_id(nadadores):
    """Nombre de la ficha según su id. Los vacíos no entran."""
    if nadadores is None or getattr(nadadores, "empty", True):
        return {}
    if "id_nadador" not in nadadores.columns or "nombre" not in nadadores.columns:
        return {}
    return {
        clave: nombre
        for clave, nombre in (
            (_anio_entero(i), n) for i, n in zip(nadadores["id_nadador"], nadadores["nombre"])
        )
        if clave is not None
    }


def anio_temporada_actual():
    """Año cuyos 31 de diciembre definen la categoría vigente."""
    return datetime.now().year


def categoria_por_anio_nacimiento(anio_nacimiento, anio_temporada=None):
    """Categoría FECHIDA a partir del año de nacimiento."""
    anio = _anio_entero(anio_nacimiento)
    if anio is None:
        return None
    temporada = int(anio_temporada or anio_temporada_actual())
    edad = temporada - anio
    for desde, hasta, nombre in TRAMOS_CATEGORIA:
        if desde <= edad <= hasta:
            return nombre
    return None


def anio_nacimiento_por_categoria(categoria, anio_referencia=None):
    """Año de nacimiento deducido de una categoría de una sola edad. None si abarca varias."""
    edad = EDAD_UNICA_POR_CATEGORIA.get(str(categoria or "").strip())
    if edad is None:
        return None
    return int(anio_referencia or ANIO_DE_CATEGORIAS_GUARDADAS) - edad


def aplicar_categoria_en_memoria(df):
    """Recalcula la categoría en la copia local cuando el año de nacimiento ya está guardado."""
    if df is None or df.empty or "anio_nacimiento" not in df.columns:
        return df
    df = df.copy()
    for i, row in df.iterrows():
        cat = categoria_por_anio_nacimiento(row.get("anio_nacimiento"))
        if cat:
            df.at[i, "categoria"] = cat
    return df


def sugerir_anios_nacimiento(df):
    """Completa en pantalla el año que falta, solo si la categoría actual es de una sola edad."""
    df = df.copy()
    if "anio_nacimiento" not in df.columns:
        df["anio_nacimiento"] = pd.NA
    for i, row in df.iterrows():
        if _anio_entero(row.get("anio_nacimiento")) is None:
            sugerido = anio_nacimiento_por_categoria(row.get("categoria"))
            if sugerido is not None:
                df.at[i, "anio_nacimiento"] = sugerido
        cat = categoria_por_anio_nacimiento(df.at[i, "anio_nacimiento"])
        if cat:
            df.at[i, "categoria"] = cat
    return df


def sincronizar_categorias_calculadas(supabase, df):
    """Escribe la categoría calculada solo si ya hay año guardado y el texto cambió. No borra filas."""
    if supabase is None or df is None or df.empty or "anio_nacimiento" not in df.columns:
        return
    if "id_nadador" not in df.columns:
        return
    for _, row in df.iterrows():
        anio = _anio_entero(row.get("anio_nacimiento"))
        id_nad = _anio_entero(row.get("id_nadador"))
        if anio is None or id_nad is None:
            continue
        cat = categoria_por_anio_nacimiento(anio)
        if not cat or cat == row.get("categoria"):
            continue
        try:
            supabase.table("nadadores").update({"categoria": cat}).eq("id", id_nad).execute()
        except Exception:
            continue


_ALIAS_COLUMNAS_MARCA = {
    "categoria": "categoria",
    "categoría": "categoria",
    "estilo": "estilo",
    "prueba": "estilo",
    "sexo": "sexo",
    "tiempo_objetivo": "tiempo_objetivo",
    "tiempo": "tiempo_objetivo",
    "tiempo_formateado": "tiempo_objetivo",
    "marca": "tiempo_objetivo",
}
_SEXOS_MARCA = {"masculino": "Masculino", "femenino": "Femenino", "ambos": "Ambos"}


def _estilo_canonico(texto, estilos):
    """Acepta '50 Libre' y también '50m Libre', sin distinguir mayúsculas."""
    bruto = " ".join(str(texto or "").strip().split())
    if not bruto:
        return None
    por_nombre = {e.lower(): e for e in estilos}
    if bruto.lower() in por_nombre:
        return por_nombre[bruto.lower()]
    token = bruto.lower()
    for dist in ("1500", "800", "400", "200", "100", "50"):
        token = token.replace(f"{dist}m", dist)
    token = " ".join(token.split())
    return por_nombre.get(token)


def preparar_carga_marcas(df, categorias, estilos):
    """Valida un CSV o Excel de marcas mínimas.

    Devuelve registros listos para guardar, errores que impiden la carga
    y avisos. Las filas sin tiempo se omiten. No borra marcas existentes.
    """
    trabajo = df.copy()
    trabajo.columns = [str(c).strip().lower() for c in trabajo.columns]
    trabajo = trabajo.rename(columns={c: _ALIAS_COLUMNAS_MARCA[c] for c in trabajo.columns if c in _ALIAS_COLUMNAS_MARCA})
    faltan = [c for c in ("categoria", "estilo", "sexo", "tiempo_objetivo") if c not in trabajo.columns]
    if faltan:
        return [], [f"Faltan columnas: {', '.join(faltan)}. Usa categoria, estilo, sexo y tiempo_objetivo."], []

    cats = {c.lower(): c for c in categorias}
    errores = []
    avisos = []
    vistos = {}
    for pos, (_, row) in enumerate(trabajo.iterrows()):
        fila = pos + 2
        tiempo_raw = row.get("tiempo_objetivo")
        if pd.isna(tiempo_raw) or not str(tiempo_raw).strip():
            continue
        cat_in = str(row.get("categoria") or "").strip()
        est_in = str(row.get("estilo") or "").strip()
        sexo_in = str(row.get("sexo") or "").strip()
        cat = cats.get(cat_in.lower())
        est = _estilo_canonico(est_in, estilos)
        sexo = _SEXOS_MARCA.get(sexo_in.lower())
        problemas = []
        if not cat:
            problemas.append(f"categoría '{cat_in}'")
        if not est:
            problemas.append(f"estilo '{est_in}'")
        if not sexo:
            problemas.append(f"sexo '{sexo_in}'")
        secs = convertir_tiempo_a_segundos(str(tiempo_raw).strip())
        if secs <= 0:
            problemas.append(f"tiempo '{tiempo_raw}'")
        if problemas:
            errores.append(f"Fila {fila}: " + ", ".join(problemas) + ".")
            continue
        clave = (cat, est, sexo)
        if clave in vistos:
            avisos.append(f"Fila {fila}: {cat} / {est} / {sexo} está repetida. Se usa este tiempo.")
        vistos[clave] = {
            "categoria": cat,
            "estilo": est,
            "sexo": sexo,
            "tiempo_objetivo": str(tiempo_raw).strip(),
            "segundos_objetivo": secs,
        }
    return list(vistos.values()), errores, avisos


GRUPOS_INICIALES = ["Competitivo", "Precompetitivo", "Formativo", "Elite", "Master"]


def _texto_limpio(valor):
    if valor is None:
        return ""
    try:
        if pd.isna(valor):
            return ""
    except TypeError:
        pass
    texto = str(valor).strip()
    return "" if texto.lower() in ("none", "nan") else texto


def texto_observacion_guardado(motivo, detalle):
    """La nota libre manda. Si solo había un motivo antiguo, se muestra ese texto."""
    detalle = _texto_limpio(detalle)
    if detalle:
        return detalle
    motivo = _texto_limpio(motivo)
    if motivo in ("", "—", "Otro"):
        return ""
    return motivo


def marca_inicial(estado, motivo, detalle):
    """Una fila ya guardada vuelve como completa, parcial o ausencia, y su nota."""
    texto = texto_observacion_guardado(motivo, detalle)
    estado = str(estado or "").strip()
    if estado == "Parcial" or (estado in ("Presente", "Completa") and texto):
        return "parcial", texto
    if estado in ("Presente", "Completa"):
        return "completa", ""
    if estado == "Ausente":
        return "ausente", ""
    return "", ""


def marcar_asistencia_exclusiva(prefijo, elegida):
    """Si se marca una casilla, las otras dos de esa fila quedan vacías."""
    if not st.session_state.get(f"{prefijo}_{elegida}"):
        return
    for marca in ("completa", "parcial", "ausente"):
        if marca != elegida:
            st.session_state[f"{prefijo}_{marca}"] = False
    if elegida != "parcial":
        st.session_state[f"{prefijo}_nota"] = ""


def filas_asistencia_para_guardar(df, fecha):
    """Arma las filas a guardar. Si hay errores, no devuelve registros."""
    errores = []
    recs = []
    for _, row in df.iterrows():
        nombre = _texto_limpio(row.get("nombre")) or "Nadador"
        marcas = [
            etiqueta
            for campo, etiqueta in (
                ("completa", "Completa"),
                ("parcial", "Parcial"),
                ("ausente", "Ausente"),
            )
            if bool(row.get(campo))
        ]
        if len(marcas) != 1:
            errores.append(f"{nombre}: marca una sola opción, completa, parcial o ausencia.")
            continue
        estado = marcas[0]
        nota = _texto_limpio(row.get("observacion"))
        if estado != "Parcial":
            nota = ""
        elif not nota:
            errores.append(f"{nombre}: escribe la observación de la asistencia parcial.")
            continue
        id_nad = _anio_entero(row.get("id_nadador"))
        if id_nad is None:
            continue
        recs.append({
            "id_nadador": id_nad,
            "fecha": fecha,
            "estado": estado,
            "motivo": None,
            "observacion": nota or None,
        })
    if errores:
        return [], errores
    return recs, []


def _resumen_asistencia(recs, fecha):
    completas = sum(1 for r in recs if r["estado"] == "Completa")
    parciales = sum(1 for r in recs if r["estado"] == "Parcial")
    ausentes = sum(1 for r in recs if r["estado"] == "Ausente")
    return (
        f"Asistencia del {fecha.strftime('%d-%m-%Y')}: "
        f"{completas} completa(s), {parciales} parcial(es), {ausentes} ausente(s)."
    )


def parse_fecha_nacimiento(valor):
    """Acepta DD/MM/AAAA. Devuelve date, None si está vacío, o 'invalid'."""
    texto = _texto_limpio(valor)
    if not texto:
        return None
    if hasattr(valor, "year") and hasattr(valor, "month") and hasattr(valor, "day"):
        try:
            return datetime(valor.year, valor.month, valor.day).date()
        except (TypeError, ValueError):
            return "invalid"
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(texto[:10], fmt).date()
        except ValueError:
            continue
    return "invalid"


def valores_calculados_de_nacimiento(valor, anio_temporada=None):
    """Edad al 31 de diciembre y categoría FECHIDA. None si la fecha no está completa."""
    fecha = parse_fecha_nacimiento(valor)
    if not fecha or fecha == "invalid":
        return None, None
    temporada = int(anio_temporada or anio_temporada_actual())
    edad = temporada - fecha.year
    if edad < 0:
        return None, None
    return edad, categoria_por_anio_nacimiento(fecha.year, temporada)


def con_edad_y_categoria(df):
    """Completa edad y categoría a partir de la fecha. Sin fecha válida, ambas quedan vacías."""
    df = df.copy()
    edades = []
    categorias = []
    for _, row in df.iterrows():
        fecha = parse_fecha_nacimiento(row.get("fecha_nacimiento"))
        if fecha and fecha != "invalid":
            edad, cat = valores_calculados_de_nacimiento(fecha)
            edades.append("" if edad is None else str(int(edad)))
            categorias.append(cat or "")
        else:
            edades.append("")
            categorias.append("")
    df["edad"] = edades
    df["categoria"] = categorias
    return df


def _proyectar_ediciones_perfiles(df, estado):
    """Aplica lo que ya se escribió en el editor para recalcular edad y categoría."""
    if not isinstance(estado, dict):
        return df
    out = df.copy()
    for idx, cambios in (estado.get("edited_rows") or {}).items():
        if isinstance(cambios, dict):
            cambios.pop("edad", None)
            cambios.pop("categoria", None)
        i = int(idx)
        if i < 0 or i >= len(out):
            continue
        for col, valor in cambios.items():
            if col in out.columns and col not in ("edad", "categoria", "id_nadador"):
                out.iat[i, out.columns.get_loc(col)] = valor
    for fila in estado.get("added_rows") or []:
        edad, cat = valores_calculados_de_nacimiento(fila.get("fecha_nacimiento"))
        fila["edad"] = "" if edad is None else str(edad)
        fila["categoria"] = cat or ""
    return out


COLOR_CELDA_EDITABLE = "#ffffff"
COLOR_CELDA_BLOQUEADA = "#d9dde3"


def presentacion_perfiles(df, solo_lectura):
    """Fondo blanco en lo editable y gris en edad, categoría y el resto bloqueado."""
    bloqueadas = set(df.columns) if solo_lectura else {"edad", "categoria"}

    def pintar(columna):
        color = COLOR_CELDA_BLOQUEADA if columna.name in bloqueadas else COLOR_CELDA_EDITABLE
        return [f"background-color: {color}"] * len(columna)

    return df.style.apply(pintar, axis=0)


def es_cumpleanos(fecha_nacimiento, fecha_clase):
    """El día y el mes de la clase coinciden con el nacimiento. El año no importa."""
    fecha = parse_fecha_nacimiento(fecha_nacimiento)
    if not fecha or fecha == "invalid" or fecha_clase is None:
        return False
    return fecha.month == fecha_clase.month and fecha.day == fecha_clase.day


def nombre_en_lista(nombre, fecha_nacimiento, fecha_clase):
    nombre = _texto_limpio(nombre) or "Nadador"
    if es_cumpleanos(fecha_nacimiento, fecha_clase):
        return f"{nombre} 🎂🥳"
    return nombre


def formatear_fecha_nacimiento(valor):
    fecha = parse_fecha_nacimiento(valor)
    if not fecha or fecha == "invalid":
        return ""
    return fecha.strftime("%d/%m/%Y")


def catalogo_grupos(grupos_df, nadadores_df):
    """La tabla de grupos manda. Si todavía no existe, se usan los grupos iniciales y los de las fichas."""
    nombres = []
    tiene_catalogo = False
    if grupos_df is not None and not getattr(grupos_df, "empty", True) and "nombre" in grupos_df.columns:
        for nombre in grupos_df["nombre"].tolist():
            nombre = _texto_limpio(nombre)
            if nombre and nombre not in nombres:
                nombres.append(nombre)
                tiene_catalogo = True
    if not tiene_catalogo:
        nombres.extend(GRUPOS_INICIALES)
    if nadadores_df is not None and not getattr(nadadores_df, "empty", True) and "grupo" in nadadores_df.columns:
        for nombre in nadadores_df["grupo"].dropna().tolist():
            nombre = _texto_limpio(nombre)
            if nombre and nombre not in nombres:
                nombres.append(nombre)
    return nombres


def cambios_de_grupos(filas):
    """Separa renombres y grupos nuevos. Un nombre vacío o repetido detiene el guardado."""
    errores = []
    renombres = []
    agregados = []
    vistos = []
    for fila in filas:
        anterior = _texto_limpio(fila.get("anterior"))
        nombre = _texto_limpio(fila.get("nombre"))
        if not nombre:
            if anterior:
                errores.append(f"El grupo «{anterior}» no puede quedar sin nombre.")
            continue
        if nombre in vistos:
            errores.append(f"El nombre «{nombre}» está repetido.")
            continue
        vistos.append(nombre)
        if not anterior:
            agregados.append(nombre)
        elif nombre != anterior:
            renombres.append((anterior, nombre))
    if errores:
        return [], [], errores
    return renombres, agregados, errores


def lista_grupos():
    return catalogo_grupos(
        st.session_state.get("grupos_df"),
        st.session_state.get("nadadores_df"),
    )


def es_nadador_activo(valor):
    """Sin la columna, o con el valor vacío, el nadador sigue visible."""
    if valor is None:
        return True
    try:
        if pd.isna(valor):
            return True
    except TypeError:
        pass
    if isinstance(valor, str):
        return valor.strip().lower() not in ("false", "0", "no", "inactivo")
    return bool(valor)


def filtrar_nadadores_activos(df):
    if df is None or df.empty or "activo" not in df.columns:
        return df
    return df.loc[df["activo"].map(es_nadador_activo)].copy()


def _secreto_sesion():
    """La firma usa la llave del servidor. No va en el repositorio ni en la cookie."""
    try:
        if "supabase" in st.secrets:
            key = st.secrets["supabase"].get("SUPABASE_KEY", "")
        else:
            key = st.secrets.get("SUPABASE_KEY", "")
        if key:
            return str(key)
    except Exception:
        pass
    return "acuatico-local-demo"


def firmar_sesion(id_usuario, secreto, ahora=None, dias=14):
    expira = int((ahora if ahora is not None else time.time()) + dias * 86400)
    mensaje = f"{int(id_usuario)}.{expira}"
    firma = hmac.new(secreto.encode(), mensaje.encode(), hashlib.sha256).hexdigest()
    return f"{mensaje}.{firma}"


def leer_sesion(token, secreto, ahora=None):
    partes = str(token or "").split(".")
    if len(partes) != 3:
        return None
    mensaje = f"{partes[0]}.{partes[1]}"
    firma = hmac.new(secreto.encode(), mensaje.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(firma, partes[2]):
        return None
    try:
        expira = int(partes[1])
        uid = int(partes[0])
    except ValueError:
        return None
    if expira < int(ahora if ahora is not None else time.time()):
        return None
    return uid


def _token_de_url():
    try:
        valor = st.query_params.get("sesion", "")
    except Exception:
        return ""
    if isinstance(valor, (list, tuple)):
        valor = valor[-1] if valor else ""
    return str(valor or "")


def _token_de_cookie():
    try:
        return str(st.context.cookies.get("acuatico_sesion", "") or "")
    except Exception:
        return ""


def sincronizar_cookie_sesion(token="", borrar=False):
    try:
        import streamlit.components.v1 as components
    except Exception:
        return
    max_age = 0 if borrar else 14 * 24 * 3600
    valor = "" if borrar else str(token)
    try:
        components.html(
            f"""<script>
            (function () {{
              var valor = "acuatico_sesion=" + encodeURIComponent({valor!r});
              var extra = "; path=/; max-age={max_age}; SameSite=Lax";
              var proto = "http:";
              try {{ proto = window.parent.location.protocol; }} catch (e) {{
                try {{ proto = location.protocol; }} catch (e2) {{}}
              }}
              if (proto === "https:") extra += "; Secure";
              var cookie = valor + extra;
              try {{ document.cookie = cookie; }} catch (e) {{}}
              try {{ window.parent.document.cookie = cookie; }} catch (e) {{}}
            }})();
            </script>""",
            height=0,
            width=0,
        )
    except Exception:
        return


def anclar_sesion(id_usuario):
    """Deja el ingreso en la dirección de la página para que recargar no cierre la sesión."""
    uid = _anio_entero(id_usuario)
    if uid is None:
        return ""
    secreto = _secreto_sesion()
    actual = _token_de_url()
    if leer_sesion(actual, secreto) != uid:
        actual = firmar_sesion(uid, secreto)
        try:
            st.query_params["sesion"] = actual
        except Exception:
            pass
    sincronizar_cookie_sesion(actual)
    return actual


def cerrar_sesion_guardada():
    sincronizar_cookie_sesion(borrar=True)
    try:
        if "sesion" in st.query_params:
            del st.query_params["sesion"]
    except Exception:
        pass


def restaurar_usuario(token, usuarios_df):
    uid = leer_sesion(token, _secreto_sesion())
    if uid is None or usuarios_df is None or usuarios_df.empty or "id_usuario" not in usuarios_df.columns:
        return None
    ids = usuarios_df["id_usuario"].map(_anio_entero)
    match = usuarios_df.loc[ids == uid]
    if match.empty:
        return None
    user = match.iloc[0]
    try:
        autorizado = bool(user.get("validado")) or user.get("rol") == "Master"
    except Exception:
        autorizado = user.get("rol") == "Master"
    if not autorizado:
        return None
    return user


def cuenta_debe_cambiar_clave(user):
    """Verdadero solo si la cuenta fue creada con clave temporal y aún no la cambió."""
    if user is None:
        return False
    if not isinstance(user, dict) and hasattr(user, "to_dict"):
        user = user.to_dict()
    if not isinstance(user, dict):
        return False
    valor = user.get("debe_cambiar_clave")
    if valor is None:
        return False
    try:
        if pd.isna(valor):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(valor, str):
        return valor.strip().lower() in {"true", "1", "t", "si", "sí", "yes"}
    return bool(valor)


def _aplicar_clave_en_sesion(uid, nueva):
    df = st.session_state.usuarios_df
    if df is not None and not df.empty and "id_usuario" in df.columns:
        mask = df["id_usuario"].map(_anio_entero) == uid
        df.loc[mask, "clave"] = nueva
        if "debe_cambiar_clave" in df.columns:
            df.loc[mask, "debe_cambiar_clave"] = False
    info = st.session_state.user_info
    if isinstance(info, dict):
        info["clave"] = nueva
        info["debe_cambiar_clave"] = False


def guardar_clave_propia(nueva, repetida):
    """La persona cambia su propia clave. No muestra la anterior."""
    if not nueva:
        return False, "Escribe la nueva contraseña."
    if nueva != repetida:
        return False, "Las dos contraseñas no coinciden."
    info = st.session_state.user_info if isinstance(st.session_state.user_info, dict) else {}
    if cuenta_debe_cambiar_clave(info) and nueva == info.get("clave"):
        return False, "La contraseña nueva tiene que ser distinta de la temporal."
    uid = _anio_entero(info.get("id_usuario"))
    if uid is None:
        return False, "No se encontró la cuenta para actualizar."
    supabase = init_connection()
    if supabase:
        try:
            supabase.table("usuarios").update(
                {"clave": nueva, "debe_cambiar_clave": False}
            ).eq("id", uid).execute()
        except Exception as e:
            if "debe_cambiar_clave" not in str(e):
                return False, f"No se pudo cambiar la contraseña: {e}"
            try:
                supabase.table("usuarios").update({"clave": nueva}).eq("id", uid).execute()
            except Exception as e2:
                return False, f"No se pudo cambiar la contraseña: {e2}"
    _aplicar_clave_en_sesion(uid, nueva)
    return True, "Contraseña actualizada."


# --- Configuración de la página ---
st.set_page_config(
    page_title="Club de Natación Acuático Valdivia",
    page_icon="🏊", # Puedes cambiar esto por la ruta a tu logo si quieres que sea el ícono de la pestaña
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Ocultar elementos de UI de Streamlit y estilos del menú ---
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* header no se oculta para no perder el menú hamburguesa en móviles */
    /* Reduce el espacio en la parte superior */
    .st-emotion-cache-18ni7ap {
        padding-top: 1rem;
    }
    /* Solapas tipo carpeta. El primer grupo vale en local; el segundo, en la app publicada. */
    .block-container {
        padding-bottom: 4.5rem;
    }
    p, .stCaption, [data-testid="stMarkdown"] {
        overflow-wrap: break-word;
    }
    .stTabs [data-baseweb="tab-list"],
    .stTabs [role="tablist"] {
        gap: 6px;
        border-bottom: 2px solid #c5d4e8;
        padding-top: 8px;
        overflow-x: auto;
        flex-wrap: nowrap;
    }
    .stTabs [role="tablist"]::after {
        display: none !important;
    }
    .stTabs [data-baseweb="tab"],
    .stTabs [role="tab"] {
        margin-top: 8px;
        height: auto !important;
        border-radius: 14px 14px 0 0 !important;
        border: 1px solid #d5deea !important;
        border-bottom: none !important;
        background: #e7eef6 !important;
        padding: 0.55rem 1rem !important;
        color: #3d4d63 !important;
        box-shadow: none !important;
        white-space: nowrap;
        flex: 0 0 auto;
    }
    .stTabs [role="tab"] p {
        color: #3d4d63 !important;
        font-weight: 500 !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"],
    .stTabs [role="tab"][aria-selected="true"],
    .stTabs [role="tab"][data-selected] {
        margin-top: 0;
        background: #ffffff !important;
        color: #0b4f9c !important;
        font-weight: 700 !important;
        border-color: #b7cbe4 !important;
        box-shadow: 0 -7px 16px rgba(20, 50, 90, 0.18), 5px 0 10px rgba(20, 50, 90, 0.06) !important;
        position: relative;
        z-index: 2;
    }
    .stTabs [role="tab"][aria-selected="true"] p,
    .stTabs [role="tab"][data-selected] p {
        color: #0b4f9c !important;
        font-weight: 700 !important;
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs .react-aria-SelectionIndicator {
        background-color: transparent !important;
        display: none !important;
    }
    .stTabs [data-baseweb="tab-panel"],
    .stTabs [role="tabpanel"] {
        background: #ffffff;
        border: 1px solid #d5deea;
        border-top: none;
        border-radius: 0 0 12px 12px;
        padding-top: 0.6rem;
        box-shadow: 0 10px 18px rgba(20, 50, 90, 0.07);
    }
    @media (min-width: 761px) {
        [class*="st-key-asist-fila"] [data-testid="stCheckbox"] label > div:last-child {
            display: none;
        }
    }
    @media (max-width: 760px) {
        .block-container {
            padding-left: 0.7rem !important;
            padding-right: 0.7rem !important;
        }
        h1 { font-size: 1.45rem !important; }
        h2 { font-size: 1.2rem !important; }
        .stTabs [data-baseweb="tab"],
        .stTabs [role="tab"] {
            padding: 0.4rem 0.55rem !important;
            font-size: 0.78rem !important;
        }
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.35rem 0.4rem !important;
        }
        [data-testid="stColumn"] {
            flex: 1 1 150px !important;
            width: auto !important;
            min-width: min(100%, 150px) !important;
        }
        .st-key-asist-cabecera { display: none !important; }
        [class*="st-key-asist-fila"] [data-testid="stHorizontalBlock"] {
            align-items: end;
        }
        [class*="st-key-asist-fila"] [data-testid="stColumn"]:nth-child(1),
        [class*="st-key-asist-fila"] [data-testid="stColumn"]:nth-child(5) {
            flex: 1 1 100% !important;
            width: 100% !important;
            min-width: 100% !important;
        }
        [class*="st-key-asist-fila"] [data-testid="stColumn"]:nth-child(2),
        [class*="st-key-asist-fila"] [data-testid="stColumn"]:nth-child(3),
        [class*="st-key-asist-fila"] [data-testid="stColumn"]:nth-child(4) {
            flex: 1 1 30% !important;
            width: 30% !important;
            min-width: 0 !important;
        }
    }
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: transparent;
        color: #888;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        z-index: 100;
        pointer-events: none;
    }
    .footer p { margin: 0; pointer-events: auto; }
    .footer a {
        color: #007bff;
        text-decoration: none;
        font-weight: bold;
    }
    .footer a:hover {
        text-decoration: underline;
    }
    </style>
    <div class="footer">
        <p>Desarrollado por <a href="https://www.linkedin.com/in/marcocede" target="_blank">Marco Cedeño</a></p>
    </div>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# --- Datos de ejemplo (luego vendrán de la BD) ---
@st.cache_resource
def init_connection():
    try:
        if "supabase" in st.secrets:
            url = st.secrets["supabase"].get("SUPABASE_URL", "")
            key = st.secrets["supabase"].get("SUPABASE_KEY", "")
        else:
            url = st.secrets.get("SUPABASE_URL", "")
            key = st.secrets.get("SUPABASE_KEY", "")
            
        if "LLAVE_ANON" in key or "URL_DE_TU_PROYECTO" in url or not url: 
            return None
        return create_client(url, key)
    except Exception: return None

def cargar_datos():
    """Carga datos desde Supabase o usa simulados si no hay conexión."""
    supabase = init_connection()

    # Columnas por defecto de las nuevas tablas
    _cols_inc   = ['id','fecha','grupo','tipo','id_nadador','descripcion']
    _cols_tst   = ['id','nombre','fecha','grupo','descripcion']
    _cols_res   = ['id','id_test','id_nadador','resultado','observaciones']
    _cols_dfis  = ['id','id_nadador','fecha','estatura_cm','peso_kg','envergadura_cm','talla_sentado_cm','porc_grasa','observaciones']
    _cols_tent  = ['id','id_nadador','fecha','prueba','tiempo_formateado','segundos_totales','serie','tipo_piscina','observaciones']

    def _safe(tbl, cols):
        """Carga una tabla tolerando que no exista aún."""
        try:
            data = supabase.table(tbl).select("*").execute().data
            return pd.DataFrame(data) if data else pd.DataFrame(columns=cols)
        except Exception:
            return pd.DataFrame(columns=cols)

    if supabase:
        try:
            usu = supabase.table("usuarios").select("*").execute().data
            nad = supabase.table("nadadores").select("*").execute().data
            tie = supabase.table("tiempos").select("*").execute().data
            mar = supabase.table("marcas_minimas").select("*").execute().data

            u_df = pd.DataFrame(usu) if usu else pd.DataFrame(columns=['id', 'nombre', 'email', 'rol', 'validado', 'grupos_asignados', 'clave'])
            n_df = pd.DataFrame(nad) if nad else pd.DataFrame(columns=['id', 'nombre', 'grupo', 'categoria', 'sexo', 'anio_nacimiento'])
            t_df = pd.DataFrame(tie) if tie else pd.DataFrame(columns=['id', 'id_nadador', 'fecha', 'lugar', 'estilo', 'tiempo_formateado', 'segundos_totales', 'tipo_piscina'])
            m_df = pd.DataFrame(mar) if mar else pd.DataFrame(columns=['categoria', 'estilo', 'sexo', 'segundos'])

            # Nuevas tablas (tolerantes a que no existan aún)
            inc_df   = _safe("incidencias_clase", _cols_inc)
            tst_df   = _safe("tests", _cols_tst)
            res_df   = _safe("resultados_test", _cols_res)
            dfis_df  = _safe("datos_fisicos", _cols_dfis)
            tent_df  = _safe("tiempos_entrenamiento", _cols_tent)
            grupos_df = _safe("grupos", ["id", "nombre"])

            if not u_df.empty: u_df.rename(columns={'id': 'id_usuario'}, inplace=True)

            # Normalizar columnas de nadadores
            if not n_df.empty:
                if 'id' in n_df.columns:
                    if 'id_nadador' in n_df.columns:
                        n_df = n_df.drop(columns=['id_nadador'])
                    n_df = n_df.rename(columns={'id': 'id_nadador'})
                elif 'id_nadador' not in n_df.columns:
                    n_df.insert(0, 'id_nadador', range(1, len(n_df) + 1))
                sincronizar_categorias_calculadas(supabase, n_df)
                n_df = aplicar_categoria_en_memoria(n_df)

            # Normalizar columnas de tiempos
            if not t_df.empty:
                _rn = {}
                if 'nadador_id' in t_df.columns and 'id_nadador' not in t_df.columns:
                    _rn['nadador_id'] = 'id_nadador'
                if 'tiempo' in t_df.columns and 'tiempo_formateado' not in t_df.columns:
                    _rn['tiempo'] = 'tiempo_formateado'
                if 'segundos' in t_df.columns and 'segundos_totales' not in t_df.columns:
                    _rn['segundos'] = 'segundos_totales'
                if _rn:
                    t_df.rename(columns=_rn, inplace=True)

            # Normalizar marcas_minimas
            if not m_df.empty:
                if 'segundos_objetivo' in m_df.columns and 'segundos' not in m_df.columns:
                    m_df.rename(columns={'segundos_objetivo': 'segundos'}, inplace=True)

            if not u_df.empty:
                return n_df, t_df, u_df, m_df, inc_df, tst_df, res_df, dfis_df, tent_df, grupos_df
        except Exception as e:
            st.sidebar.warning(f"Error conectando a BD: {e}. Usando modo local.")

    # --- FALLBACK DE PROTOTIPO ---
    nadadores_df = aplicar_categoria_en_memoria(pd.DataFrame([
        {'id_nadador': 1, 'nombre': 'Ana', 'grupo': 'Competitivo', 'categoria': 'Infantil B1', 'sexo': 'Femenino', 'anio_nacimiento': 2014, 'fecha_nacimiento': '2014-03-15', 'activo': True},
        {'id_nadador': 2, 'nombre': 'Luis', 'grupo': 'Competitivo', 'categoria': 'Infantil A', 'sexo': 'Masculino', 'anio_nacimiento': 2015, 'activo': True},
        {'id_nadador': 3, 'nombre': 'Carla', 'grupo': 'Precompetitivo', 'categoria': 'Juvenil A1', 'sexo': 'Femenino', 'anio_nacimiento': 2012, 'activo': True},
        {'id_nadador': 4, 'nombre': 'Pedro', 'grupo': 'Elite', 'categoria': 'Mayores', 'sexo': 'Masculino', 'anio_nacimiento': None, 'activo': False},
    ]))
    tiempos_df = pd.DataFrame([
        {'id_nadador': 1, 'fecha': '2023-10-15', 'lugar': 'Piscina Municipal', 'estilo': '50m Libre', 'tiempo_formateado': '00:28,50', 'segundos_totales': 28.5, 'tipo_piscina': 'Piscina Corta (25m)'},
        {'id_nadador': 1, 'fecha': '2023-11-20', 'lugar': 'Competencia Regional', 'estilo': '50m Libre', 'tiempo_formateado': '00:27,90', 'segundos_totales': 27.9, 'tipo_piscina': 'Piscina Larga (50m)'},
        {'id_nadador': 2, 'fecha': '2023-11-20', 'lugar': 'Competencia Regional', 'estilo': '100m Pecho', 'tiempo_formateado': '01:15,30', 'segundos_totales': 75.3, 'tipo_piscina': 'Piscina Corta (25m)'},
        {'id_nadador': 4, 'fecha': '2023-11-20', 'lugar': 'Competencia Regional', 'estilo': '200m Combinado', 'tiempo_formateado': '02:10,80', 'segundos_totales': 130.8, 'tipo_piscina': 'Piscina Larga (50m)'},
    ])
    usuarios_df = pd.DataFrame([
        {'id_usuario': 999, 'nombre': 'Super Master', 'rol': 'Master', 'grupos_asignados': [], 'email': 'master@club.cl', 'validado': True, 'clave': 'admin123', 'id_nadador': None},
        {'id_usuario': 888, 'nombre': 'Junta Directiva', 'rol': 'Directiva', 'grupos_asignados': [], 'email': 'directiva@club.cl', 'validado': True, 'clave': '1234', 'id_nadador': None},
        {'id_usuario': 101, 'nombre': 'Entrenador Alex', 'rol': 'Entrenador', 'grupos_asignados': ['Elite','Competitivo', 'Precompetitivo'], 'email': 'alex@club.cl', 'validado': True, 'clave': '1234', 'id_nadador': None},
        {'id_usuario': 1, 'nombre': 'Ana', 'rol': 'Nadador', 'grupos_asignados': [], 'email': 'ana@club.cl', 'validado': True, 'clave': '1234', 'id_nadador': 1},
        {'id_usuario': 4, 'nombre': 'Pedro', 'rol': 'Nadador', 'grupos_asignados': [], 'email': 'pedro@club.cl', 'validado': True, 'clave': '1234', 'id_nadador': 4},
        {'id_usuario': 99, 'nombre': 'Usuario Nuevo', 'rol': 'Pendiente', 'grupos_asignados': [], 'email': 'nuevo@gmail.com', 'validado': False, 'clave': '1234', 'id_nadador': None},
    ])
    marcas_minimas_df = pd.DataFrame([
        {'categoria': 'Infantil A', 'estilo': '50m Libre', 'sexo': 'Femenino', 'segundos': 32.0},
        {'categoria': 'Infantil A', 'estilo': '50m Libre', 'sexo': 'Masculino', 'segundos': 30.0},
        {'categoria': 'Infantil B', 'estilo': '50m Libre', 'sexo': 'Femenino', 'segundos': 28.0},
        {'categoria': 'Infantil B', 'estilo': '50m Libre', 'sexo': 'Masculino', 'segundos': 26.0},
        {'categoria': 'Juvenil A', 'estilo': '50m Libre', 'sexo': 'Femenino', 'segundos': 25.0},
        {'categoria': 'Juvenil A', 'estilo': '50m Libre', 'sexo': 'Masculino', 'segundos': 23.0},
        {'categoria': 'Mayor', 'estilo': '50m Libre', 'sexo': 'Femenino', 'segundos': 24.0},
        {'categoria': 'Mayor', 'estilo': '50m Libre', 'sexo': 'Masculino', 'segundos': 22.0},
    ])
    return (
        nadadores_df, tiempos_df, usuarios_df, marcas_minimas_df,
        pd.DataFrame(columns=_cols_inc), pd.DataFrame(columns=_cols_tst),
        pd.DataFrame(columns=_cols_res), pd.DataFrame(columns=_cols_dfis),
        pd.DataFrame(columns=_cols_tent),
        pd.DataFrame({"id": list(range(1, len(GRUPOS_INICIALES) + 1)), "nombre": GRUPOS_INICIALES}),
    )

# --- Definición de las Páginas como Funciones ---

def mostrar_dashboard():
    """Muestra el contenido de la página Dashboard."""
    if st.session_state.user_role in ['Entrenador', 'Directiva', 'Master']:
        if st.session_state.user_role == 'Directiva':
            st.header("Vista Directiva (Solo Lectura) 👁️")
            st.info("Visualización general del rendimiento del club. No se permiten modificaciones.")
        else:
            st.header("Dashboard del Entrenador 📋")
            
        user_info = st.session_state.user_info
        roster = filtrar_nadadores_activos(st.session_state.nadadores_df)
        # Directiva obtiene todos los grupos; Entrenador solo los suyos (o todos si tiene el permiso 'Todos')
        grupos_asignados = user_info['grupos_asignados'] if st.session_state.user_role == 'Entrenador' else roster['grupo'].dropna().unique().tolist()
        if st.session_state.user_role == 'Entrenador' and ('Todos' in user_info['grupos_asignados'] or not user_info['grupos_asignados']):
            grupos_asignados = roster['grupo'].dropna().unique().tolist()
        grupos_asignados = [g for g in grupos_asignados if pd.notna(g) and str(g).strip()]
        
        # Opciones de resumen
        if not grupos_asignados:
            st.info("No hay nadadores activos para mostrar. Quienes dejaron de venir siguen en Perfiles, con la casilla Activo desmarcada.")
            nadadores_del_grupo = roster.iloc[0:0]
            grupo_seleccionado = None
        else:
            grupo_seleccionado = st.selectbox("Selecciona un grupo para ver el resumen masivo:", ["Todos"] + grupos_asignados)
            if grupo_seleccionado == "Todos":
                nadadores_del_grupo = roster[roster['grupo'].isin(grupos_asignados)]
            else:
                nadadores_del_grupo = roster[roster['grupo'] == grupo_seleccionado]
            
        st.subheader("Resumen de Marcas del Grupo")
        resumen_data = []
        for _, nad in nadadores_del_grupo.iterrows():
            _id_col = 'id_nadador' if 'id_nadador' in st.session_state.tiempos_df.columns else 'id'
            _id_nad = nad.get('id_nadador', nad.get('id', None))
            tiempos_nad = st.session_state.tiempos_df[st.session_state.tiempos_df[_id_col] == _id_nad] if pd.notna(_id_nad) else st.session_state.tiempos_df.iloc[0:0]
            _sec = 'segundos_totales' if 'segundos_totales' in tiempos_nad.columns else 'segundos'
            mejores = tiempos_nad.groupby('estilo')[_sec].min().to_dict() if not tiempos_nad.empty else {}
            resumen_data.append({
            'Nadador': nad['nombre'], 
            'Categoría': nad['categoria'], 
            **{k: v for k, v in mejores.items()}})
            

        st.dataframe(pd.DataFrame(resumen_data).fillna('-'), use_container_width=True)
        
        st.markdown("---")
        st.subheader("Análisis Individual Detallado")
        nadador_seleccionado = st.selectbox("Selecciona un nadador en particular:", [""] + nadadores_del_grupo['nombre'].tolist())
        
        if nadador_seleccionado:
            nadador_row = nadadores_del_grupo[nadadores_del_grupo['nombre'] == nadador_seleccionado].iloc[0]
            id_nadador = nadador_row.get('id_nadador', nadador_row.get('id', None))
            cat_actual = nadador_row['categoria']
            _id_col_t = 'id_nadador' if 'id_nadador' in st.session_state.tiempos_df.columns else 'id'
            tiempos_nadador = st.session_state.tiempos_df[st.session_state.tiempos_df[_id_col_t] == id_nadador] if pd.notna(id_nadador) else st.session_state.tiempos_df.iloc[0:0]
            
            col1, col2 = st.columns([1.2, 1])
            with col1:
                st.write(f"**Tiempos Registrados: {nadador_seleccionado} ({cat_actual})**")
                if not tiempos_nadador.empty:
                    _disp = tiempos_nadador.copy()
                    _disp['Tiempo'] = _disp.apply(formatear_tiempo_con_icono, axis=1)
                    st.dataframe(_disp[['fecha', 'lugar', 'estilo', 'Tiempo']], use_container_width=True)
                else:
                    st.warning("Este nadador aún no tiene tiempos registrados.")
            with col2:
                st.write("**Desempeño vs. Múltiples Categorías (Telaraña)**")
                
                # Obtener el sexo del nadador para filtrar la gráfica
                sexo_actual = nadador_row.get('sexo', 'Masculino')
                
                # Generar diccionario de marcas filtrado por el sexo del nadador actual
                marcas_obj = {}
                cats_plot = []
                
                marcas_filtradas = st.session_state.marcas_df[st.session_state.marcas_df['sexo'] == sexo_actual] if 'sexo' in st.session_state.marcas_df.columns else st.session_state.marcas_df
                
                for cat in marcas_filtradas['categoria'].unique():
                    subset = marcas_filtradas[marcas_filtradas['categoria'] == cat]
                    _sec_m = 'segundos' if 'segundos' in subset.columns else 'segundos_objetivo'
                    marcas_obj[cat] = dict(zip(subset['estilo'], subset[_sec_m]))
                    cats_plot.append(cat)
                
                # Por seguridad si la BD aún no tiene marcas insertadas
                if not marcas_obj:
                    marcas_obj = {'Temporal': {'50m Libre': 28}}
                    cats_plot = ['Temporal']
                
                # ── Filtrar por grupo de categoría del nadador ──────────────────
                # Guardar mapa completo ANTES de filtrar (para análisis de progresión)
                marcas_obj_completo = dict(marcas_obj)
                # Infantil ve sus categorías + Juvenil A1 como meta aspiracional
                # Juvenil y Mayores ven solo su grupo
                if 'Infantil' in cat_actual:
                    cats_grupo = [c for c in cats_plot if 'Infantil' in c or c == 'Juvenil A1']
                elif 'Juvenil' in cat_actual:
                    cats_grupo = [c for c in cats_plot if 'Juvenil' in c]
                elif 'Mayor' in cat_actual:
                    cats_grupo = [c for c in cats_plot if 'Mayor' in c]
                else:
                    cats_grupo = cats_plot  # fallback: mostrar todo
                # Aplicar filtro (solo si el filtro no dejó vacío el grupo)
                if cats_grupo:
                    cats_plot = cats_grupo
                    marcas_obj = {k: v for k, v in marcas_obj.items() if k in cats_plot}
                # ────────────────────────────────────────────────────────────────
                
                # Encontrar el mejor tiempo actual del nadador (en segundos)
                _sec2 = 'segundos_totales' if 'segundos_totales' in tiempos_nadador.columns else 'segundos'
                mejores_tiempos = tiempos_nadador.groupby('estilo')[_sec2].min().to_dict() if not tiempos_nadador.empty else {}
                categorias_estilos = list(set([e for cat in marcas_obj.values() for e in cat.keys()])) 
                if not categorias_estilos: categorias_estilos = ['50m Libre']
                
                # Determinar categoría top automáticamente (la menor de la lista)
                estilo_ref = categorias_estilos[0]
                try: cat_top = min(cats_plot, key=lambda c: marcas_obj[c].get(estilo_ref, 999))
                except: cat_top = cats_plot[0]
                
                def norm(t, est): 
                    val_obj = marcas_obj.get(cat_top, {}).get(est, 1E-9)
                    if val_obj == 0: val_obj = 1E-9
                    return (t / val_obj) * 100 if t > 0 else 180
                
                fig = go.Figure()
                colores = ['#aaaaaa', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
                
                # Plotear todas las categorías
                for i, c in enumerate(cats_plot):
                    color = colores[i % len(colores)]
                    vals_c = [norm(marcas_obj[c].get(est, 0), est) for est in categorias_estilos]
                    es_actual = (c == cat_actual)
                    fig.add_trace(go.Scatterpolar(r=vals_c, theta=categorias_estilos, name=f'Mínima {c}', 
                                                  line=dict(color=color, dash='solid' if es_actual else 'dot', width=3 if es_actual else 1)))

                # Plotear tiempos del nadador
                vals_nadador = [norm(mejores_tiempos.get(est, 0), est) if mejores_tiempos.get(est) else 180 for est in categorias_estilos]
                if any(mejores_tiempos):
                    fig.add_trace(go.Scatterpolar(r=vals_nadador, theta=categorias_estilos, fill='toself', name=f'Marca de {nadador_seleccionado}', line=dict(color='#1f77b4', width=3)))
                
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[160, 90])),
                    showlegend=True, 
                    title="Análisis contra metas superiores (%)", 
                    legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
                    margin=dict(l=90, r=90, t=40, b=80)
                )
                st.plotly_chart(fig, use_container_width=True)

            # ── Evolución Temporal por Prueba ───────────────────────────────────
            if not tiempos_nadador.empty:
                st.markdown("---")
                st.markdown("### 📈 Evolución Temporal por Prueba")
                st.caption("Cada gráfica muestra cómo han evolucionado los tiempos. Las líneas son marcas mínimas de categoría.")
                st.markdown(
                    '<span style="color:#1f77b4">&#9679; <b>Piscina Corta (25m)</b></span>'
                    '&nbsp;&nbsp;&nbsp;'
                    '<span style="color:#e07b00">&#9670; <b>Piscina Larga (50m)</b></span>',
                    unsafe_allow_html=True
                )
                st.markdown("")
                _sec_col_ev = 'segundos_totales' if 'segundos_totales' in tiempos_nadador.columns else 'segundos'
                _tf_col     = 'tiempo_formateado' if 'tiempo_formateado' in tiempos_nadador.columns else _sec_col_ev
                estilos_nad = sorted(tiempos_nadador['estilo'].unique())
                colores_cat = ['#636efa', '#ef553b', '#00cc96', '#ab63fa', '#ffa15a', '#19d3f3', '#ff6692']

                for _i in range(0, len(estilos_nad), 2):
                    _batch = estilos_nad[_i:_i+2]
                    _cols_ev = st.columns(len(_batch))
                    for _j, _estilo in enumerate(_batch):
                        _df_est = tiempos_nadador[tiempos_nadador['estilo'] == _estilo].copy()
                        _df_est['fecha'] = pd.to_datetime(_df_est['fecha'])
                        _df_est = _df_est.sort_values('fecha')

                        with _cols_ev[_j]:
                            _fig_ev = go.Figure()

                            # Línea de conexión suave entre todos los puntos (orden cronológico)
                            _fig_ev.add_trace(go.Scatter(
                                x=_df_est['fecha'], y=_df_est[_sec_col_ev],
                                mode='lines', showlegend=False,
                                line=dict(color='#aaaaaa', width=2),
                                hoverinfo='skip'
                            ))

                            # Marcadores diferenciados por tipo de piscina
                            _POOL_STYLES = {
                                'Piscina Corta (25m)': dict(color='#1f77b4', symbol='circle',  label='🏊 Corta (25m)'),
                                'Piscina Larga (50m)': dict(color='#e07b00', symbol='diamond', label='🌊 Larga (50m)'),
                            }
                            _has_tipo = 'tipo_piscina' in _df_est.columns
                            for _tipo_pool, _ps in _POOL_STYLES.items():
                                if _has_tipo:
                                    _sub = _df_est[_df_est['tipo_piscina'] == _tipo_pool]
                                else:
                                    _sub = _df_est if _tipo_pool == 'Piscina Corta (25m)' else _df_est.iloc[0:0]
                                if _sub.empty:
                                    continue
                                _fig_ev.add_trace(go.Scatter(
                                    x=_sub['fecha'], y=_sub[_sec_col_ev],
                                    mode='markers',
                                    name=_ps['label'],
                                    marker=dict(color=_ps['color'], symbol=_ps['symbol'],
                                                size=12, line=dict(width=1.5, color='white')),
                                    customdata=_sub[_tf_col].values,
                                    hovertemplate='<b>%{customdata}</b><br>%{x|%d/%m/%Y}<extra>'
                                                  + _ps['label'] + '</extra>',
                                    showlegend=False
                                ))

                            # Líneas horizontales de marcas mínimas por categoría
                            _ci = 0
                            for _cat_m, _marcas_m in marcas_obj.items():
                                if _estilo in _marcas_m:
                                    _fig_ev.add_hline(
                                        y=_marcas_m[_estilo],
                                        line_dash='solid' if _cat_m == cat_actual else 'dash',
                                        line_color=colores_cat[_ci % len(colores_cat)],
                                        line_width=2.5 if _cat_m == cat_actual else 1.5,
                                        annotation_text=_cat_m,
                                        annotation_position="right",
                                        annotation_font=dict(size=10)
                                    )
                                _ci += 1

                            _fig_ev.update_layout(
                                title=dict(text=f"<b>{_estilo}</b>", font=dict(size=14)),
                                xaxis=dict(title="Fecha", tickformat="%b %Y"),
                                yaxis=dict(title="Segundos", autorange=True),
                                showlegend=False,
                                margin=dict(l=55, r=130, t=45, b=40),
                                height=320,
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)'
                            )
                            st.plotly_chart(_fig_ev, use_container_width=True)
            # ──────────────────────────────────────────────────────────────────────

            # ── Bloque de progresión hacia siguiente categoría ───────────────
            SIGUIENTE_CAT = {
                'Infantil A': 'Infantil B1', 'Infantil B1': 'Infantil B2',
                'Infantil B2': 'Juvenil A1', 'Juvenil A1': 'Juvenil A2',
                'Juvenil A2': 'Juvenil B',   'Juvenil B': 'Mayores',
                'Mayores': None
            }
            next_cat = SIGUIENTE_CAT.get(cat_actual)
            _sec2b = 'segundos_totales' if 'segundos_totales' in tiempos_nadador.columns else 'segundos'
            mejores_seg = tiempos_nadador.groupby('estilo')[_sec2b].min().to_dict() if not tiempos_nadador.empty else {}

            if next_cat and next_cat in marcas_obj_completo and mejores_seg:
                next_marks = marcas_obj_completo[next_cat]
                estilos_comunes = [e for e in next_marks if e in mejores_seg]
                if estilos_comunes:
                    st.markdown(f"### 🎯 ¿Cuánto falta para **{next_cat}**?")
                    todos_ok = all(mejores_seg[e] <= next_marks[e] for e in estilos_comunes)
                    if todos_ok:
                        diferencias = [next_marks[e] - mejores_seg[e] for e in estilos_comunes]
                        prom = sum(diferencias) / len(diferencias)
                        st.success(
                            f"🎉 **¡Felicitaciones, {nadador_seleccionado}!** "
                            f"Ya superas **todas** las marcas mínimas de {next_cat}. "
                            f"Estás en promedio **{segundos_a_tiempo(prom)} por encima** de cada marca objetivo."
                        )
                    else:
                        cols_prog = st.columns(len(estilos_comunes))
                        for i, estilo in enumerate(estilos_comunes):
                            tiempo_nad = mejores_seg[estilo]
                            objetivo  = next_marks[estilo]
                            diferencia = tiempo_nad - objetivo
                            with cols_prog[i]:
                                if diferencia <= 0:  # ya clasificó en este estilo
                                    st.success(
                                        f"**{estilo}**\n\n"
                                        f"✅ Clasificado\n\n"
                                        f"Tu marca: `{segundos_a_tiempo(tiempo_nad)}`\n\n"
                                        f"Superaste por `{segundos_a_tiempo(abs(diferencia))}`"
                                    )
                                else:
                                    st.warning(
                                        f"**{estilo}**\n\n"
                                        f"⏱️ Faltan `{segundos_a_tiempo(diferencia)}`\n\n"
                                        f"Tu marca: `{segundos_a_tiempo(tiempo_nad)}`\n\n"
                                        f"Objetivo: `{segundos_a_tiempo(objetivo)}`"
                                    )
            elif not next_cat:
                st.info(f"🏆 **{nadador_seleccionado}** ya está en la categoría máxima (**Mayores**).")
            # ───────────────────────────────────────────────────────────────────

    elif st.session_state.user_role == 'Nadador':
        st.header("Mi Progreso Personal")
        user_info = st.session_state.user_info
        id_nadador = _anio_entero(user_info.get("id_nadador"))
        ficha = st.session_state.nadadores_df.iloc[0:0]
        if id_nadador is not None and "id_nadador" in st.session_state.nadadores_df.columns:
            ficha = st.session_state.nadadores_df[st.session_state.nadadores_df["id_nadador"].map(_anio_entero) == id_nadador]
        if id_nadador is None or ficha.empty:
            st.warning("Tu cuenta todavía no está vinculada a un nadador. El administrador debe asignarte la ficha en Admin Usuarios.")
        else:
            yo = ficha.iloc[0]
            st.subheader(f"{yo.get('nombre')} · {yo.get('categoria', '')}")
            tiempos_nadador = st.session_state.tiempos_df[st.session_state.tiempos_df["id_nadador"].map(_anio_entero) == id_nadador] if "id_nadador" in st.session_state.tiempos_df.columns else st.session_state.tiempos_df.iloc[0:0]
            st.subheader("Mis Tiempos Registrados")
            if not tiempos_nadador.empty:
                _disp = tiempos_nadador.copy()
                _disp['Tiempo'] = _disp.apply(formatear_tiempo_con_icono, axis=1)
                st.dataframe(_disp[['fecha', 'lugar', 'estilo', 'Tiempo']], use_container_width=True)
            else:
                st.warning("Aún no tienes tiempos registrados.")
            st.subheader("Mi Gráfica de Progreso")
            st.info("La gráfica de telaraña se mostrará aquí.")
    else:
        st.error("Rol no reconocido o cuenta pendiente.")

def mostrar_asistencia():
    """Muestra la página de Asistencia. Entrenador edita; Directiva/Master solo ven."""
    st.header("Registro de Asistencia 🗓️")

    rol = st.session_state.user_role
    if rol not in ['Entrenador', 'Directiva', 'Master']:
        st.warning("Esta sección no está disponible para tu perfil.")
        return

    solo_lectura = rol in ['Directiva', 'Master']
    if solo_lectura:
        st.info("👁️ **Modo vista** — solo los entrenadores pueden registrar la asistencia.")

    user_info = st.session_state.user_info
    roster = filtrar_nadadores_activos(st.session_state.nadadores_df)
    grupos_asignados = user_info.get('grupos_asignados', [])
    if solo_lectura or 'Todos' in grupos_asignados or not grupos_asignados:
        grupos_asignados = roster['grupo'].dropna().unique().tolist()
    grupos_asignados = [g for g in grupos_asignados if pd.notna(g) and str(g).strip()]

    if not grupos_asignados:
        st.info("No hay nadadores activos en este grupo.")
        nadadores_del_grupo = roster.iloc[0:0]
        grupo_seleccionado = ""
        fecha_seleccionada = datetime.today()
    else:
        col1, col2 = st.columns(2)
        with col1:
            grupo_seleccionado = st.selectbox("Grupo:", grupos_asignados)
        with col2:
            fecha_seleccionada = st.date_input("Fecha de la clase:", datetime.today())
        nadadores_del_grupo = roster[roster['grupo'] == grupo_seleccionado]
    st.caption("Marca una sola casilla por nadador: completa, parcial o ausencia. El texto de observación se habilita solo en parcial.")

    fecha_str = fecha_seleccionada.strftime('%Y-%m-%d')
    registros = {}
    supabase = init_connection()
    lectura_ok = supabase is None
    if supabase:
        try:
            guardadas = supabase.table("asistencias").select("*").eq("fecha", fecha_str).execute().data or []
            for row in guardadas:
                id_nad = _anio_entero(row.get("id_nadador"))
                if id_nad is not None:
                    registros[id_nad] = row
            lectura_ok = True
        except Exception as e:
            st.warning(f"No se pudo leer la asistencia ya guardada: {e}")

    filas = []
    for _, nad in nadadores_del_grupo.iterrows():
        id_nad = _anio_entero(nad.get("id_nadador"))
        previo = registros.get(id_nad, {})
        marca, nota = marca_inicial(
            previo.get("estado"), previo.get("motivo"), previo.get("observacion")
        )
        filas.append({
            "id_nadador": id_nad,
            "nombre": nombre_en_lista(nad.get("nombre"), nad.get("fecha_nacimiento"), fecha_seleccionada),
            "marca": marca,
            "observacion": nota,
        })

    anchos_asistencia = [2.3, 0.9, 0.9, 0.95, 2.8]
    with st.container(key="asist-cabecera"):
        cabecera = st.columns(anchos_asistencia, vertical_alignment="center")
        cabecera[0].markdown("**Nadador**")
        cabecera[1].markdown("**Completa**")
        cabecera[2].markdown("**Parcial**")
        cabecera[3].markdown("**Ausencia**")
        cabecera[4].markdown("**Observación**")

    editadas = []
    for fila in filas:
        id_nad = fila["id_nadador"]
        prefijo = f"asist_{grupo_seleccionado}_{fecha_str}_{id_nad}"
        if f"{prefijo}_completa" not in st.session_state:
            st.session_state[f"{prefijo}_completa"] = fila["marca"] == "completa"
            st.session_state[f"{prefijo}_parcial"] = fila["marca"] == "parcial"
            st.session_state[f"{prefijo}_ausente"] = fila["marca"] == "ausente"
        if f"{prefijo}_nota" not in st.session_state:
            st.session_state[f"{prefijo}_nota"] = fila["observacion"]
        with st.container(key=f"asist-fila-{grupo_seleccionado}-{id_nad}"):
            columnas = st.columns(anchos_asistencia, vertical_alignment="center")
            columnas[0].write(fila["nombre"])
            completa = columnas[1].checkbox(
                "Completa",
                key=f"{prefijo}_completa",
                disabled=solo_lectura,
                on_change=None if solo_lectura else marcar_asistencia_exclusiva,
                args=(prefijo, "completa"),
            )
            parcial = columnas[2].checkbox(
                "Parcial",
                key=f"{prefijo}_parcial",
                disabled=solo_lectura,
                on_change=None if solo_lectura else marcar_asistencia_exclusiva,
                args=(prefijo, "parcial"),
            )
            ausente = columnas[3].checkbox(
                "Ausencia",
                key=f"{prefijo}_ausente",
                disabled=solo_lectura,
                on_change=None if solo_lectura else marcar_asistencia_exclusiva,
                args=(prefijo, "ausente"),
            )
            observacion = columnas[4].text_input(
                "Observación",
                key=f"{prefijo}_nota",
                label_visibility="collapsed",
                disabled=solo_lectura or not parcial,
                placeholder="Ej.: llegó tarde, se retiró antes",
            )
        editadas.append({
            "id_nadador": id_nad,
            "nombre": fila["nombre"],
            "completa": completa,
            "parcial": parcial,
            "ausente": ausente,
            "observacion": observacion,
        })
    edited_df = pd.DataFrame(editadas)

    if not solo_lectura:
        if st.button("Guardar Asistencia", type="primary"):
            recs, errores = filas_asistencia_para_guardar(edited_df, fecha_str)
            if not lectura_ok:
                st.error("No se guardó nada: primero hay que poder leer la asistencia de ese día, para no pisar la que ya existe.")
            elif errores:
                st.error("No se guardó la lista. " + " ".join(errores))
            elif recs and supabase:
                try:
                    supabase.table("asistencias").upsert(recs, on_conflict="id_nadador,fecha").execute()
                    st.success(_resumen_asistencia(recs, fecha_seleccionada))
                except Exception as e:
                    if "motivo" in str(e) or "observacion" in str(e):
                        reducidos = [
                            {k: v for k, v in r.items() if k not in ("motivo", "observacion")}
                            for r in recs
                        ]
                        try:
                            supabase.table("asistencias").upsert(
                                reducidos, on_conflict="id_nadador,fecha"
                            ).execute()
                            st.warning(
                                "La asistencia quedó guardada, pero la base todavía no tiene motivo ni detalle. "
                                "Ejecuta migracion_asistencia.sql en Supabase para que esas observaciones se conserven."
                            )
                        except Exception as e2:
                            st.error(f"Error BD al guardar asistencias: {e2}")
                    else:
                        st.error(f"Error BD al guardar asistencias: {e}")
            elif recs:
                st.success(_resumen_asistencia(recs, fecha_seleccionada) + " (modo local)")
            else:
                st.info("No hay nadadores en este grupo para guardar.")

    st.markdown("---")
    st.subheader("📝 Incidencia de la clase")
    st.caption("Texto libre del entrenador: una pelea, un altercado, un derrumbe o lo que haya pasado en la clase.")

    inc_df = st.session_state.get('incidencias_df', pd.DataFrame())
    nota_id = None
    nota_texto = ""
    otras = []
    if not inc_df.empty and 'fecha' in inc_df.columns and grupo_seleccionado:
        fecha_str_inc = fecha_seleccionada.strftime('%Y-%m-%d')
        inc_hoy = inc_df[inc_df['fecha'].astype(str) == fecha_str_inc]
        if 'grupo' in inc_hoy.columns:
            inc_hoy = inc_hoy[inc_hoy['grupo'].astype(str) == str(grupo_seleccionado)]
        for _, row in inc_hoy.iterrows():
            if str(row.get("tipo") or "") == "Nota de clase":
                nota_id = row.get("id")
                nota_texto = _texto_limpio(row.get("descripcion"))
            else:
                otras.append(_texto_limpio(row.get("descripcion")))
    for texto_previo in otras:
        if texto_previo:
            st.info(texto_previo)

    incidencia = st.text_area(
        "Incidencia",
        value=nota_texto,
        height=140,
        disabled=solo_lectura,
        placeholder="Ej.: Pelea en el camarín. Altercado entre dos nadadores. Derrumbe de un carril.",
        key=f"incidencia_{grupo_seleccionado}_{fecha_str}",
        label_visibility="collapsed",
    )
    if not solo_lectura and st.button("Guardar incidencia", type="primary"):
        texto_inc = _texto_limpio(incidencia)
        if not texto_inc:
            st.error("Escribe la incidencia antes de guardar.")
        else:
            rec_inc = {
                "fecha": fecha_str,
                "grupo": grupo_seleccionado,
                "tipo": "Nota de clase",
                "id_nadador": None,
                "descripcion": texto_inc,
            }
            sb_inc = init_connection()
            if sb_inc:
                try:
                    if nota_id is not None and str(nota_id) not in ("", "nan"):
                        sb_inc.table("incidencias_clase").update(
                            {"descripcion": texto_inc}
                        ).eq("id", int(nota_id)).execute()
                    else:
                        sb_inc.table("incidencias_clase").insert(rec_inc).execute()
                    fresco = sb_inc.table("incidencias_clase").select("*").execute().data
                    st.session_state.incidencias_df = pd.DataFrame(fresco) if fresco else pd.DataFrame(
                        columns=['id', 'fecha', 'grupo', 'tipo', 'id_nadador', 'descripcion']
                    )
                    st.success("Incidencia guardada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error BD: {e}")
            else:
                if nota_texto and not inc_df.empty and "tipo" in inc_df.columns:
                    mascara = (
                        (inc_df["fecha"].astype(str) == fecha_str)
                        & (inc_df["grupo"].astype(str) == str(grupo_seleccionado))
                        & (inc_df["tipo"].astype(str) == "Nota de clase")
                    )
                    if mascara.any():
                        inc_df.loc[mascara, "descripcion"] = texto_inc
                        st.session_state.incidencias_df = inc_df
                    else:
                        st.session_state.incidencias_df = pd.concat(
                            [inc_df, pd.DataFrame([rec_inc])], ignore_index=True
                        )
                else:
                    st.session_state.incidencias_df = pd.concat(
                        [inc_df, pd.DataFrame([rec_inc])], ignore_index=True
                    )
                st.success("Incidencia guardada en esta sesión.")


def registrar_tiempos():
    st.header("Registrar Nuevos Tiempos ⏱️")
    if st.session_state.user_role not in ['Entrenador', 'Master', 'Directiva']:
        st.warning("Sección restringida.")
        return

    import io as _io

    estilos_natacion = [
        '50 Libre', '100 Libre', '200 Libre', '400 Libre', '800 Libre', '1500 Libre',
        '50 Espalda', '100 Espalda', '200 Espalda', '50 Pecho', '100 Pecho', '200 Pecho',
        '50 Mariposa', '100 Mariposa', '200 Mariposa', '100 IM', '200 IM', '400 IM'
    ]
    _nad_df = filtrar_nadadores_activos(st.session_state.nadadores_df.copy())
    _id_col = 'id_nadador' if 'id_nadador' in _nad_df.columns else 'id'
    nadadores = _nad_df['nombre'].tolist() if not _nad_df.empty else []
    if not nadadores:
        st.info("No hay nadadores activos para registrar tiempos. El historial de quienes ya no vienen se conserva en Perfiles.")
        return

    tab_comp, tab_ent = st.tabs(["🏆 Competencia", "🏋️ Entrenamiento"])

    # ══════════════════════════════════════════════════════════
    # PESTAÑA 1 — COMPETENCIA
    # ══════════════════════════════════════════════════════════
    with tab_comp:
        c1, c2 = st.tabs(["📝 Registro Individual", "📥 Carga Masiva"])

        with c1:
            nadador_sel = st.selectbox("Nadador:", nadadores, key="nad_comp")
            with st.form("form_tiempos_comp"):
                col1, col2 = st.columns(2)
                with col1:
                    fecha        = st.date_input("Fecha", datetime.today(), key="fecha_comp")
                    estilo       = st.selectbox("Estilo:", estilos_natacion)
                with col2:
                    lugar        = st.text_input("Lugar / Competencia")
                    tiempo_input = st.text_input("Tiempo (MM:SS,MS)", placeholder="01:05,50")
                tipo_piscina = st.selectbox(
                    "Tipo de Piscina:",
                    ["Piscina Corta (25m)", "Piscina Larga (50m)"],
                    format_func=lambda x: f"🏊 {x}" if "Corta" in x else f"🌊 {x}"
                )
                if st.form_submit_button("💾 Guardar Tiempo", type="primary"):
                    secs    = convertir_tiempo_a_segundos(tiempo_input)
                    sb      = init_connection()
                    id_nad  = None
                    nad_row = _nad_df[_nad_df['nombre'] == nadador_sel]
                    if not nad_row.empty:
                        for c_id in ['id_nadador', 'id']:
                            if c_id in nad_row.iloc[0].index and pd.notna(nad_row.iloc[0][c_id]):
                                id_nad = nad_row.iloc[0][c_id]; break
                    if sb and id_nad is None:
                        try:
                            r = sb.table("nadadores").select("id").eq("nombre", nadador_sel).execute()
                            if r.data: id_nad = r.data[0]['id']
                        except: pass
                    if sb:
                        if id_nad is None:
                            st.error(f"No se encontró el ID de '{nadador_sel}'.")
                        else:
                            try:
                                sb.table("tiempos").insert({
                                    "id_nadador": int(id_nad), "fecha": fecha.strftime('%Y-%m-%d'),
                                    "lugar": lugar, "estilo": estilo,
                                    "tiempo_formateado": tiempo_input,
                                    "segundos_totales": secs, "tipo_piscina": tipo_piscina
                                }).execute()
                                st.success(f"✅ Guardado: {tiempo_input} ({secs}s)")
                            except Exception as e:
                                st.error(f"Error BD: {e}")
                    else:
                        st.success("Modo local: Tiempo guardado (simulado).")

        with c2:
            st.info(
                "💡 **Pasos:**  \n"
                "1. Descarga la plantilla — ya tiene los nombres e IDs reales de los nadadores.  \n"
                "2. Completa: **fecha, lugar, estilo, tipo_piscina, tiempo_formateado**.  \n"
                "3. **No modifiques** las columnas `id_nadador` ni `nombre`."
            )
            plantilla_comp = pd.DataFrame({
                'id_nadador': _nad_df[_id_col].values, 'nombre': _nad_df['nombre'].values,
                'fecha': '', 'lugar': '', 'estilo': '', 'tipo_piscina': '', 'tiempo_formateado': ''
            })
            buf_comp = _io.StringIO()
            plantilla_comp.to_csv(buf_comp, index=False)
            st.download_button("📥 Descargar Plantilla de Competencia",
                               buf_comp.getvalue().encode('utf-8'),
                               "plantilla_carga_tiempos.csv", "text/csv")
            st.markdown("---")
            up_comp = st.file_uploader("Sube tu archivo (CSV o Excel)", type=["csv","xlsx"], key="up_comp")
            if up_comp:
                try:
                    df_comp = pd.read_csv(up_comp) if up_comp.name.endswith('.csv') else pd.read_excel(up_comp)
                    st.write("🔍 Vista previa:")
                    st.dataframe(df_comp, use_container_width=True)
                    if st.button("🚀 Insertar Tiempos de Competencia", type="primary"):
                        df_comp['segundos_totales'] = df_comp['tiempo_formateado'].apply(convertir_tiempo_a_segundos)
                        df_ins = df_comp[df_comp['tiempo_formateado'].notna() & (df_comp['tiempo_formateado'].astype(str).str.strip() != '')].copy()
                        df_ins = df_ins[[c for c in ['id_nadador','fecha','lugar','estilo','tipo_piscina','tiempo_formateado','segundos_totales'] if c in df_ins.columns]]
                        if df_ins.empty:
                            st.warning("⚠️ No hay filas con tiempos para insertar.")
                        else:
                            sb = init_connection()
                            if sb:
                                try:
                                    sb.table("tiempos").insert(df_ins.to_dict('records')).execute()
                                    st.success(f"✅ {len(df_ins)} tiempos de competencia registrados.")
                                    st.balloons()
                                except Exception as e: st.error(f"❌ Error BD: {e}")
                            else:
                                st.info("💡 Modo Prototipo: sin conexión a Supabase.")
                except Exception as e:
                    st.error(f"❌ Error al procesar archivo: {e}")

    # ══════════════════════════════════════════════════════════
    # PESTAÑA 2 — ENTRENAMIENTO
    # ══════════════════════════════════════════════════════════
    with tab_ent:
        e1, e2 = st.tabs(["📝 Registro Individual", "📥 Carga Masiva"])

        with e1:
            nad_ent_sel = st.selectbox("Nadador:", nadadores, key="nad_ent")
            with st.form("form_tiempos_ent"):
                ce1, ce2 = st.columns(2)
                with ce1:
                    fecha_ent  = st.date_input("Fecha", datetime.today(), key="fecha_ent")
                    prueba_ent = st.text_input("Prueba", placeholder="Ej: 200m Libre, 4×100m Espalda")
                    serie_ent  = st.number_input("Nº de serie", min_value=1, max_value=50, value=1)
                with ce2:
                    tipo_p_ent = st.selectbox("Tipo de Piscina:", ["Piscina Corta (25m)", "Piscina Larga (50m)"], key="tipo_p_ent")
                    tiempo_ent = st.text_input("Tiempo (MM:SS,MS)", placeholder="01:45,30")
                    obs_ent    = st.text_input("Observaciones", placeholder="Opcional")
                if st.form_submit_button("💾 Guardar Tiempo de Entrenamiento", type="primary"):
                    if prueba_ent and tiempo_ent:
                        secs_ent   = convertir_tiempo_a_segundos(tiempo_ent)
                        nr          = _nad_df[_nad_df['nombre'] == nad_ent_sel]
                        id_nad_ent  = int(nr.iloc[0][_id_col]) if not nr.empty else None
                        if id_nad_ent:
                            sb = init_connection()
                            if sb:
                                try:
                                    sb.table("tiempos_entrenamiento").insert({
                                        "id_nadador": id_nad_ent, "fecha": fecha_ent.strftime('%Y-%m-%d'),
                                        "prueba": prueba_ent, "tiempo_formateado": tiempo_ent,
                                        "segundos_totales": secs_ent, "serie": int(serie_ent),
                                        "tipo_piscina": tipo_p_ent, "observaciones": obs_ent
                                    }).execute()
                                    st.success(f"✅ Guardado: {prueba_ent} — {tiempo_ent}")
                                except Exception as e: st.error(f"Error BD: {e}")
                            else:
                                st.success("Modo local: Tiempo guardado (simulado).")
                        else:
                            st.error("No se encontró el nadador.")
                    else:
                        st.error("Completa al menos la prueba y el tiempo.")

            # Historial del nadador seleccionado
            tent_ss = st.session_state.get('tiempos_ent_df', pd.DataFrame())
            if not tent_ss.empty and 'id_nadador' in tent_ss.columns:
                nr2 = _nad_df[_nad_df['nombre'] == nad_ent_sel]
                if not nr2.empty:
                    hist_e = tent_ss[tent_ss['id_nadador'] == nr2.iloc[0][_id_col]]
                    if not hist_e.empty:
                        st.markdown(f"**Historial — {nad_ent_sel}:**")
                        cols_h = [c for c in ['fecha','prueba','serie','tiempo_formateado','tipo_piscina','observaciones'] if c in hist_e.columns]
                        st.dataframe(hist_e[cols_h].sort_values('fecha', ascending=False), use_container_width=True, hide_index=True)

        with e2:
            st.info(
                "💡 **Pasos:**  \n"
                "1. Descarga la plantilla — ya tiene los nombres e IDs de los nadadores.  \n"
                "2. Completa: **fecha, prueba, serie, tipo_piscina, tiempo_formateado, observaciones**.  \n"
                "3. **No modifiques** las columnas `id_nadador` ni `nombre`."
            )
            plantilla_ent = pd.DataFrame({
                'id_nadador': _nad_df[_id_col].values, 'nombre': _nad_df['nombre'].values,
                'fecha': '', 'prueba': '', 'serie': 1, 'tipo_piscina': '',
                'tiempo_formateado': '', 'observaciones': ''
            })
            buf_ent = _io.StringIO()
            plantilla_ent.to_csv(buf_ent, index=False)
            st.download_button("📥 Descargar Plantilla de Entrenamiento",
                               buf_ent.getvalue().encode('utf-8'),
                               "plantilla_tiempos_entrenamiento.csv", "text/csv")
            st.markdown("---")
            up_ent = st.file_uploader("Sube tu archivo (CSV o Excel)", type=["csv","xlsx"], key="up_ent")
            if up_ent:
                try:
                    df_eu = pd.read_csv(up_ent) if up_ent.name.endswith('.csv') else pd.read_excel(up_ent)
                    st.dataframe(df_eu, use_container_width=True)
                    if st.button("🚀 Insertar Tiempos de Entrenamiento", type="primary"):
                        df_eu['segundos_totales'] = df_eu['tiempo_formateado'].apply(convertir_tiempo_a_segundos)
                        df_ie = df_eu[df_eu['tiempo_formateado'].notna() & (df_eu['tiempo_formateado'].astype(str).str.strip() != '')].copy()
                        df_ie = df_ie[[c for c in ['id_nadador','fecha','prueba','serie','tipo_piscina','tiempo_formateado','segundos_totales','observaciones'] if c in df_ie.columns]]
                        if df_ie.empty:
                            st.warning("⚠️ No hay filas con tiempos para insertar.")
                        else:
                            sb = init_connection()
                            if sb:
                                try:
                                    sb.table("tiempos_entrenamiento").insert(df_ie.to_dict('records')).execute()
                                    st.success(f"✅ ¡{len(df_ie)} registros cargados!")
                                    st.balloons()
                                except Exception as e: st.error(f"❌ Error BD: {e}")
                            else:
                                st.info("💡 Modo Prototipo: sin conexión a Supabase.")
                except Exception as e:
                    st.error(f"❌ Error al procesar archivo: {e}")


def _aplicar_renombre_local(anterior, nuevo):
    nad = st.session_state.nadadores_df
    if nad is not None and not nad.empty and "grupo" in nad.columns:
        nad.loc[nad["grupo"].astype(str) == anterior, "grupo"] = nuevo
    usu = st.session_state.usuarios_df
    if usu is not None and not usu.empty and "grupos_asignados" in usu.columns:
        def _cambiar(valor):
            if isinstance(valor, list):
                return [nuevo if str(item) == anterior else item for item in valor]
            return valor
        usu["grupos_asignados"] = usu["grupos_asignados"].apply(_cambiar)
        if st.session_state.user_info and "grupos_asignados" in st.session_state.user_info:
            st.session_state.user_info["grupos_asignados"] = _cambiar(
                st.session_state.user_info.get("grupos_asignados")
            )
    for clave in ("incidencias_df", "tests_df"):
        frame = st.session_state.get(clave)
        if frame is not None and not frame.empty and "grupo" in frame.columns:
            frame.loc[frame["grupo"].astype(str) == anterior, "grupo"] = nuevo


def _guardar_catalogo_grupos(renombres, agregados, nombres_finales):
    supabase = init_connection()
    if supabase:
        try:
            for anterior, nuevo in renombres:
                supabase.table("nadadores").update({"grupo": nuevo}).eq("grupo", anterior).execute()
                for tabla in ("incidencias_clase", "tests"):
                    try:
                        supabase.table(tabla).update({"grupo": nuevo}).eq("grupo", anterior).execute()
                    except Exception:
                        pass
                try:
                    cuentas = supabase.table("usuarios").select("id, grupos_asignados").execute().data or []
                    for cuenta in cuentas:
                        grupos = cuenta.get("grupos_asignados") or []
                        if anterior in grupos:
                            nuevos = [nuevo if item == anterior else item for item in grupos]
                            supabase.table("usuarios").update(
                                {"grupos_asignados": nuevos}
                            ).eq("id", cuenta["id"]).execute()
                except Exception:
                    pass
            tabla_grupos = []
            try:
                tabla_grupos = supabase.table("grupos").select("id, nombre").execute().data or []
            except Exception as error_tabla:
                st.warning(
                    "La tabla de grupos todavía no existe. Ejecuta migracion_grupos_y_fecha.sql "
                    "en Supabase para que los nombres queden guardados. Si cambiaste un nombre, "
                    "las fichas sí se actualizaron."
                )
                if "grupos" not in str(error_tabla):
                    raise
            existentes = {_texto_limpio(fila.get("nombre")) for fila in tabla_grupos}
            if tabla_grupos:
                temporales = []
                for indice, (anterior, nuevo) in enumerate(renombres):
                    if anterior in existentes:
                        temporal = f"__tmp_{indice}"
                        supabase.table("grupos").update({"nombre": temporal}).eq("nombre", anterior).execute()
                        existentes.discard(anterior)
                        existentes.add(temporal)
                        temporales.append((temporal, nuevo))
                    elif nuevo not in existentes:
                        supabase.table("grupos").insert({"nombre": nuevo}).execute()
                        existentes.add(nuevo)
                for temporal, nuevo in temporales:
                    supabase.table("grupos").update({"nombre": nuevo}).eq("nombre", temporal).execute()
                    existentes.discard(temporal)
                    existentes.add(nuevo)
                pendientes = agregados
            else:
                pendientes = nombres_finales
            for nombre in pendientes:
                if nombre not in existentes:
                    try:
                        supabase.table("grupos").insert({"nombre": nombre}).execute()
                    except Exception:
                        pass
            for anterior, nuevo in renombres:
                _aplicar_renombre_local(anterior, nuevo)
            try:
                fresco = supabase.table("grupos").select("*").order("nombre").execute().data or []
                if fresco:
                    st.session_state.grupos_df = pd.DataFrame(fresco)
            except Exception:
                st.session_state.grupos_df = pd.DataFrame(
                    {"nombre": nombres_finales}
                )
            nad_fresh = supabase.table("nadadores").select("*").execute().data
            if nad_fresh:
                fresh_df = pd.DataFrame(nad_fresh)
                if "id" in fresh_df.columns:
                    fresh_df = fresh_df.rename(columns={"id": "id_nadador"})
                st.session_state.nadadores_df = aplicar_categoria_en_memoria(fresh_df)
            st.success("Grupos guardados.")
            st.rerun()
        except Exception as error_grupos:
            st.error(f"No se pudieron guardar los grupos: {error_grupos}")
        return

    for anterior, nuevo in renombres:
        _aplicar_renombre_local(anterior, nuevo)
    catalogo = st.session_state.get("grupos_df")
    if catalogo is None or catalogo.empty or "nombre" not in catalogo.columns:
        finales = nombres_finales
    else:
        mapa = dict(renombres)
        finales = []
        for nombre in catalogo["nombre"].tolist():
            nombre = mapa.get(_texto_limpio(nombre), _texto_limpio(nombre))
            if nombre and nombre not in finales:
                finales.append(nombre)
        for nombre in agregados:
            if nombre not in finales:
                finales.append(nombre)
    st.session_state.grupos_df = pd.DataFrame(
        {"id": list(range(1, len(finales) + 1)), "nombre": finales}
    )
    st.success("Grupos guardados en esta sesión.")
    st.rerun()


def gestionar_nadadores():
    """Muestra el panel de gestión de perfiles de los nadadores."""
    st.header("👥 Gestión de Perfiles de Nadadores")
    rol = st.session_state.user_role
    if rol not in ['Entrenador', 'Master', 'Directiva']:
        st.error("Solamente la directiva, los entrenadores y el master pueden entrar a perfiles.")
        return
    puede_editar_fichas = rol in ['Entrenador', 'Master']

    tp1, tp2, tp3 = st.tabs(["Perfiles", "📏 Datos Fisiológicos", "Configurar grupos"])

    with tp1:
        fichas_aviso = st.session_state.nadadores_df
        if fichas_aviso is not None and not fichas_aviso.empty and "nombre" in fichas_aviso.columns:
            if "fecha_nacimiento" in fichas_aviso.columns:
                faltan_fecha = [
                    str(n) for n, f in zip(fichas_aviso["nombre"], fichas_aviso["fecha_nacimiento"])
                    if not _texto_limpio(formatear_fecha_nacimiento(f)) and pd.notna(n) and str(n).strip()
                ]
            else:
                faltan_fecha = [str(n) for n in fichas_aviso["nombre"] if pd.notna(n) and str(n).strip()]
            if faltan_fecha:
                st.warning("Faltan nadadores con fecha de nacimiento: " + ", ".join(faltan_fecha))
        if puede_editar_fichas:
            st.write("Edita el nombre, la fecha de nacimiento, el grupo y el sexo. La edad y la categoría se calculan solas: el fondo gris indica que esa celda no se edita.")
        else:
            st.info("La directiva ve las fichas y puede cambiar los nombres de los grupos en Configurar grupos. El nombre y la fecha los editan el entrenador y el master.")
        st.caption("La fecha se escribe DD/MM/AAAA. La edad es la cumplida al 31 de diciembre y con ella se asigna la categoría. Sin fecha, la edad y la categoría quedan vacías. Desmarca Activo para ocultar a quien ya no viene: la ficha no se borra.")
        if st.session_state.pop("perfil_guardado", False):
            st.success("Guardado. La categoría quedó calculada con la fecha de nacimiento.")
        df = st.session_state.nadadores_df.copy()
        if 'id' in df.columns:
            df = df.drop(columns=['id'])
        if "activo" not in df.columns:
            df["activo"] = True
        else:
            df["activo"] = df["activo"].map(es_nadador_activo)
        df = sugerir_anios_nacimiento(df)
        if "fecha_nacimiento" not in df.columns:
            df["fecha_nacimiento"] = ""
        df["fecha_nacimiento"] = df["fecha_nacimiento"].map(formatear_fecha_nacimiento)
        if "grupo" not in df.columns:
            df["grupo"] = ""
        if "categoria" not in df.columns:
            df["categoria"] = ""
        df = _proyectar_ediciones_perfiles(df, st.session_state.get("editor_perfiles"))
        df = con_edad_y_categoria(df)
        columnas_editor = ["nombre", "fecha_nacimiento", "edad", "categoria", "grupo", "sexo", "activo", "id_nadador"]
        df = df[columnas_editor]
        opciones_grupo = lista_grupos()
        df["grupo"] = df["grupo"].map(_texto_limpio)
        for grupo_extra in df["grupo"].tolist():
            if grupo_extra and grupo_extra not in opciones_grupo:
                opciones_grupo.append(grupo_extra)
        if "" not in opciones_grupo:
            opciones_grupo = [""] + opciones_grupo
        edited_df = st.data_editor(
            presentacion_perfiles(df, solo_lectura=not puede_editar_fichas),
            use_container_width=True, num_rows="dynamic" if puede_editar_fichas else "fixed",
            disabled=not puede_editar_fichas,
            key="editor_perfiles",
            column_config={
                "id_nadador": None,
                "nombre": st.column_config.TextColumn("Nombre"),
                "fecha_nacimiento": st.column_config.TextColumn(
                    "Fecha de nacimiento", help="DD/MM/AAAA"
                ),
                "edad": st.column_config.TextColumn(
                    "Edad", disabled=True,
                    help="Edad cumplida al 31 de diciembre. Define la categoría."
                ),
                "categoria": st.column_config.TextColumn("Categoría", disabled=True),
                "grupo": st.column_config.SelectboxColumn("Grupo", options=opciones_grupo, required=True),
                "sexo": st.column_config.SelectboxColumn(
                    "Sexo", options=["Femenino", "Masculino"], required=True
                ),
                "activo": st.column_config.CheckboxColumn("Activo", default=True),
            }
        )
        if puede_editar_fichas and st.button("Guardar Perfiles", type="primary"):
            supabase = init_connection()
            if supabase:
                errores = []
                falta_columna = False
                try:
                    for _, row in edited_df.iterrows():
                        nombre = str(row.get("nombre") or "").strip()
                        if not nombre or nombre.lower() == "none":
                            continue
                        sexo = _texto_limpio(row.get("sexo"))
                        if sexo not in ("Femenino", "Masculino"):
                            errores.append(f"{nombre}: elige Femenino o Masculino.")
                            continue
                        id_val = _anio_entero(row.get("id_nadador"))
                        grupo = _texto_limpio(row.get("grupo"))
                        if not grupo:
                            errores.append(f"{nombre}: elige un grupo.")
                            continue
                        fecha = parse_fecha_nacimiento(row.get("fecha_nacimiento"))
                        if fecha == "invalid":
                            errores.append(f"{nombre}: la fecha debe ir en formato DD/MM/AAAA.")
                            continue
                        if fecha is None:
                            errores.append(f"{nombre}: indica la fecha de nacimiento (DD/MM/AAAA).")
                            continue
                        anio = fecha.year
                        if anio < 1920 or anio > datetime.now().year:
                            errores.append(f"{nombre}: el año {anio} no es válido.")
                            continue
                        cat = categoria_por_anio_nacimiento(anio)
                        if not cat:
                            errores.append(f"{nombre}: esa fecha no entra en una categoría FECHIDA.")
                            continue
                        rec = {
                            "nombre": nombre,
                            "sexo": sexo,
                            "categoria": cat,
                            "anio_nacimiento": anio,
                            "fecha_nacimiento": fecha.strftime("%Y-%m-%d"),
                            "grupo": grupo,
                            "activo": es_nadador_activo(row.get("activo")),
                        }

                        def _enviar(payload):
                            if id_val is not None:
                                supabase.table("nadadores").update(payload).eq("id", id_val).execute()
                            else:
                                supabase.table("nadadores").insert(payload).execute()

                        payload = dict(rec)
                        ultimo_error = None
                        for _intento in range(4):
                            try:
                                _enviar(payload)
                                ultimo_error = None
                                break
                            except Exception as e_fila:
                                ultimo_error = e_fila
                                msg = str(e_fila)
                                if "fecha_nacimiento" in payload and "fecha_nacimiento" in msg:
                                    payload.pop("fecha_nacimiento", None)
                                    falta_columna = True
                                    continue
                                if "anio_nacimiento" in payload and "anio_nacimiento" in msg:
                                    payload.pop("anio_nacimiento", None)
                                    falta_columna = True
                                    continue
                                if "activo" in payload and "activo" in msg:
                                    payload.pop("activo", None)
                                    falta_columna = True
                                    continue
                                break
                        if ultimo_error is not None:
                            errores.append(f"{nombre}: {ultimo_error}")

                    nad_fresh = supabase.table("nadadores").select("*").execute().data
                    if nad_fresh:
                        fresh_df = pd.DataFrame(nad_fresh)
                        if 'id' in fresh_df.columns:
                            if 'id_nadador' in fresh_df.columns:
                                fresh_df = fresh_df.drop(columns=['id_nadador'])
                            fresh_df = fresh_df.rename(columns={'id': 'id_nadador'})
                        fresh_df = aplicar_categoria_en_memoria(fresh_df)
                        st.session_state.nadadores_df = fresh_df
                    if falta_columna:
                        st.warning("La base todavía no tiene alguna columna nueva (fecha de nacimiento, año o activo). El resto del perfil se guardó. Ejecuta las migraciones en Supabase antes de volver a guardar.")
                    if errores:
                        st.error("No se guardaron algunas filas: " + " | ".join(errores))
                    elif not falta_columna:
                        st.session_state.perfil_guardado = True
                        st.rerun()
                except Exception as e:
                    st.error(f"Error Supabase guardando perfiles: {e}")
            else:
                editado = edited_df.copy()
                editado = editado[editado["nombre"].map(lambda n: bool(_texto_limpio(n)))].copy()
                fechas = editado["fecha_nacimiento"].map(parse_fecha_nacimiento)
                sexos_ok = editado["sexo"].map(lambda s: _texto_limpio(s) in ("Femenino", "Masculino"))
                grupos_ok = editado["grupo"].map(lambda g: bool(_texto_limpio(g)))
                if editado.empty:
                    st.error("No hay nadadores para guardar.")
                elif (fechas == "invalid").any() or fechas.map(lambda f: f is None).any():
                    st.error("Cada nadador necesita una fecha DD/MM/AAAA válida.")
                elif not sexos_ok.all() or not grupos_ok.all():
                    st.error("Cada nadador necesita sexo y grupo.")
                else:
                    editado = editado.drop(columns=["edad"], errors="ignore")
                    editado["anio_nacimiento"] = fechas.map(lambda f: f.year)
                    editado["fecha_nacimiento"] = fechas.map(lambda f: f.strftime("%Y-%m-%d"))
                    editado["categoria"] = editado["anio_nacimiento"].map(categoria_por_anio_nacimiento)
                    st.session_state.nadadores_df = aplicar_categoria_en_memoria(editado)
                    st.success("Perfiles guardados en el Prototipo Temporal.")

    with tp2:
        st.write("Registra y visualiza la evolución física de cada nadador. Incluye medidas clave para el rendimiento en natación.")
        nad_fis_sel = st.selectbox("Selecciona un nadador:", st.session_state.nadadores_df['nombre'].tolist(), key="nad_fis")
        nad_fis_row = st.session_state.nadadores_df[st.session_state.nadadores_df['nombre'] == nad_fis_sel]
        id_nad_fis = int(nad_fis_row.iloc[0]['id_nadador']) if not nad_fis_row.empty else None

        if not puede_editar_fichas:
            st.info("La directiva puede revisar las medidas. El entrenador y el master las registran.")
        else:
            with st.form("form_datos_fisicos"):
                st.markdown("**Medidas Antropométricas**")
                cf1, cf2, cf3 = st.columns(3)
                with cf1:
                    fecha_fis    = st.date_input("Fecha", datetime.today(), key="fecha_fis")
                    estatura     = st.number_input("Estatura (cm)", min_value=50.0, max_value=250.0, value=160.0, step=0.5, help="Talla de pie sin calzado")
                with cf2:
                    peso         = st.number_input("Peso (kg)", min_value=10.0, max_value=200.0, value=55.0, step=0.1)
                    envergadura  = st.number_input("Envergadura de brazos (cm)", min_value=50.0, max_value=300.0, value=165.0, step=0.5,
                                                   help="Distancia punta a punta con los brazos extendidos horizontalmente")
                with cf3:
                    talla_sent   = st.number_input("Talla sentado (cm)", min_value=30.0, max_value=160.0, value=85.0, step=0.5,
                                                   help="Altura desde la silla hasta la coronilla. Indica longitud de tronco.")
                    porc_grasa   = st.number_input("% Grasa corporal", min_value=0.0, max_value=60.0, value=15.0, step=0.1,
                                                   help="Porcentaje de masa grasa estimado (pliegues cutáneos o bioimpedancia)")
                obs_fis = st.text_input("Observaciones", placeholder="Opcional")

                if st.form_submit_button("💾 Guardar Datos Físicos", type="primary"):
                    if id_nad_fis:
                        rec_fis = {
                            "id_nadador": id_nad_fis,
                            "fecha": fecha_fis.strftime('%Y-%m-%d'),
                            "estatura_cm": estatura, "peso_kg": peso,
                            "envergadura_cm": envergadura, "talla_sentado_cm": talla_sent,
                            "porc_grasa": porc_grasa, "observaciones": obs_fis
                        }
                        supabase = init_connection()
                        if supabase:
                            try:
                                supabase.table("datos_fisicos").insert(rec_fis).execute()
                                st.success("✅ Datos físicos guardados.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error BD: {e}")
                        else:
                            st.success("Modo local: Datos guardados (simulado).")

        # ── Historial tabular + gráficas ──
        dfis = st.session_state.get('datos_fisicos_df', pd.DataFrame())
        if not dfis.empty and 'id_nadador' in dfis.columns and id_nad_fis:
            hist_fis = dfis[dfis['id_nadador'] == id_nad_fis].copy()
            if not hist_fis.empty:
                hist_fis['fecha'] = pd.to_datetime(hist_fis['fecha'])
                hist_fis = hist_fis.sort_values('fecha')
                # IMC calculado
                if 'peso_kg' in hist_fis.columns and 'estatura_cm' in hist_fis.columns:
                    hist_fis['IMC'] = (hist_fis['peso_kg'] / ((hist_fis['estatura_cm']/100)**2)).round(2)
                # Índice Envergadura/Estatura (bueno en natación si > 1)
                if 'envergadura_cm' in hist_fis.columns and 'estatura_cm' in hist_fis.columns:
                    hist_fis['Env/Est'] = (hist_fis['envergadura_cm'] / hist_fis['estatura_cm']).round(3)

                st.markdown(f"**Historial Fisiológico — {nad_fis_sel}:**")
                cols_fis = [c for c in ['fecha','estatura_cm','peso_kg','IMC','envergadura_cm','Env/Est','talla_sentado_cm','porc_grasa','observaciones'] if c in hist_fis.columns]
                st.dataframe(hist_fis[cols_fis], use_container_width=True, hide_index=True)

                # Gráfica 1: Estatura, Envergadura y Talla sentado
                fig_talla = go.Figure()
                fig_talla.add_trace(go.Scatter(x=hist_fis['fecha'], y=hist_fis['estatura_cm'], name='Estatura (cm)', line=dict(color='#1f77b4', width=2)))
                if 'envergadura_cm' in hist_fis.columns:
                    fig_talla.add_trace(go.Scatter(x=hist_fis['fecha'], y=hist_fis['envergadura_cm'], name='Envergadura (cm)', line=dict(color='#2ca02c', width=2, dash='dash')))
                if 'talla_sentado_cm' in hist_fis.columns:
                    fig_talla.add_trace(go.Scatter(x=hist_fis['fecha'], y=hist_fis['talla_sentado_cm'], name='Talla sentado (cm)', line=dict(color='#9467bd', width=2, dash='dot')))
                fig_talla.update_layout(
                    title=f"Medidas de Longitud — {nad_fis_sel}",
                    xaxis=dict(title="Fecha"), yaxis=dict(title="cm"),
                    legend=dict(orientation='h', y=-0.25), height=320,
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_talla, use_container_width=True)

                # Gráfica 2: Peso y % Grasa
                fig_comp = go.Figure()
                fig_comp.add_trace(go.Scatter(x=hist_fis['fecha'], y=hist_fis['peso_kg'], name='Peso (kg)', line=dict(color='#e07b00', width=2)))
                if 'porc_grasa' in hist_fis.columns:
                    fig_comp.add_trace(go.Scatter(x=hist_fis['fecha'], y=hist_fis['porc_grasa'], name='% Grasa', line=dict(color='#d62728', width=2, dash='dash'), yaxis='y2'))
                fig_comp.update_layout(
                    title=f"Composición Corporal — {nad_fis_sel}",
                    xaxis=dict(title="Fecha"),
                    yaxis=dict(title="Peso (kg)"),
                    yaxis2=dict(title="% Grasa", overlaying='y', side='right'),
                    legend=dict(orientation='h', y=-0.25), height=320,
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_comp, use_container_width=True)
            else:
                st.info("Aún no hay datos fisiológicos registrados para este nadador.")
        else:
            st.info("Aún no hay datos fisiológicos registrados.")

    with tp3:
        st.write("Agrega grupos o cámbiales el nombre. Esos nombres son los que aparecen en el menú de cada ficha.")
        st.caption("Un cambio de nombre se aplica en las fichas, en las cuentas de entrenador, en las incidencias y en los tests. Desde aquí no se elimina un grupo.")
        editor_grupos = pd.DataFrame({"anterior": lista_grupos(), "nombre": lista_grupos()})
        grupos_editados = st.data_editor(
            editor_grupos,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "anterior": None,
                "nombre": st.column_config.TextColumn("Grupo", required=True),
            },
            key="editor_grupos",
        )
        if st.button("Guardar grupos", type="primary"):
            filas_grupo = grupos_editados.to_dict("records")
            renombres, agregados, errores_grupo = cambios_de_grupos(filas_grupo)
            if errores_grupo:
                st.error(" ".join(errores_grupo))
            else:
                nombres_finales = []
                for fila in filas_grupo:
                    nombre = _texto_limpio(fila.get("nombre"))
                    if nombre and nombre not in nombres_finales:
                        nombres_finales.append(nombre)
                _guardar_catalogo_grupos(renombres, agregados, nombres_finales)

def configurar_marcas():
    """Muestra el contenido de la configuración de Marcas Mínimas por Categoría."""
    st.header("⚙️ Configuración de Marcas Mínimas")
    
    # 1. Verificación de permisos
    if st.session_state.user_role not in ['Entrenador', 'Master', 'Directiva']:
        st.error("No tienes permiso para configurar las metas del equipo.")
        return
        
    if st.session_state.pop("marcas_cargadas", None):
        st.success(st.session_state.pop("marcas_cargadas_msg", "Marcas actualizadas."))

    tab_una, tab_masiva = st.tabs(["📝 Una a una", "📥 Carga masiva"])

    # 2. Definición de opciones para los desplegables (Matching con la DB)
    cats_oficiales = [
        'Infantil A', 'Infantil B1', 'Infantil B2', 
        'Juvenil A1', 'Juvenil A2', 'Juvenil B', 'Mayores'
    ]
    
    estilos_oficiales = [
        '50 Libre', '100 Libre', '200 Libre', '400 Libre', '800 Libre', '1500 Libre',
        '50 Espalda', '100 Espalda', '200 Espalda',
        '50 Pecho', '100 Pecho', '200 Pecho',
        '50 Mariposa', '100 Mariposa', '200 Mariposa',
        '100 IM', '200 IM', '400 IM'
    ]

    with tab_una:
        st.info("ℹ️ Ingresa los tiempos en formato **MM:SS,MS** (Ejemplo: 01:05,50). La columna 'Segundos' se calculará automáticamente al guardar.")

        # 3. Preparar los datos para el editor
        df = st.session_state.marcas_df.copy()
        
        # Asegurarnos de que las columnas necesarias existan para evitar errores en el editor
        for col in ['categoria', 'estilo', 'sexo', 'tiempo_objetivo', 'segundos']:
            if col not in df.columns:
                df[col] = None

        # 4. El Editor de Datos (Data Editor)
        edited_df = st.data_editor(
            df, 
            use_container_width=True, 
            num_rows="dynamic",
            column_config={
                "categoria": st.column_config.SelectboxColumn("Categoría", options=cats_oficiales, required=True),
                "estilo": st.column_config.SelectboxColumn("Estilo", options=estilos_oficiales, required=True),
                "sexo": st.column_config.SelectboxColumn("Sexo", options=["Masculino", "Femenino", "Ambos"], required=True),
                "tiempo_objetivo": st.column_config.TextColumn("Marca (MM:SS,MS)", required=True),
                "segundos": st.column_config.NumberColumn("Segundos (Auto)", disabled=True, format="%.2f")
            },
            hide_index=True,
            key="editor_marcas"
        )
        
        # 5. Lógica de Guardado
        if st.button("Guardar Cambios permanentemente", type="primary"):
            # PASO CRÍTICO: Convertir el texto de tiempo a segundos antes de enviar a Supabase
            try:
                # Aplicamos la función de conversión a cada fila
                edited_df['segundos'] = edited_df['tiempo_objetivo'].apply(convertir_tiempo_a_segundos)
                
                # Actualizamos el estado de la sesión
                st.session_state.marcas_df = edited_df.copy()
                
                supabase = init_connection()
                if supabase:
                    # Limpiar datos viejos y cargar los nuevos (Estrategia de reseteo)
                    # Nota: .neq("categoria", "ELIMINATODO") es un truco para borrar todo el contenido
                    supabase.table("marcas_minimas").delete().neq("categoria", "ELIMINATODO").execute()

                    # Dentro de la lógica de guardado:
                    recs = edited_df.to_dict('records')
                    # Asegúrate de que el diccionario tenga las llaves correctas para la BD
                    for r in recs:
                        r['segundos_objetivo'] = r.pop('segundos') # Cambiamos el nombre para que coincida con SQL
                    if recs:
                        supabase.table("marcas_minimas").insert(recs).execute()
                    
                    st.success("✅ ¡Configuración guardada exitosamente en la base de datos!")
                    st.balloons()
                else:
                    st.warning("⚠️ Modo local: Los cambios se guardaron solo para esta sesión.")
                    
            except Exception as e:
                st.error(f"❌ Error al procesar los datos: {e}")
                st.info("Asegúrate de que todos los tiempos tengan el formato correcto (ej: 01:30,00)")

    with tab_masiva:
        import io as _io
        st.info(
            "💡 **Pasos:**  \n"
            "1. Descarga la plantilla. Ya trae cada categoría, estilo y sexo, y el tiempo si ya existe.  \n"
            "2. Completa **tiempo_objetivo** en formato MM:SS,MS (ejemplo: 01:05,50). Las filas vacías se ignoran.  \n"
            "3. Sube el CSV o Excel. Solo se agregan o actualizan las filas del archivo; el resto de las marcas sigue igual."
        )
        actuales = {}
        base = st.session_state.marcas_df
        if not base.empty and {"categoria", "estilo", "sexo"}.issubset(base.columns):
            col_tiempo = "tiempo_objetivo" if "tiempo_objetivo" in base.columns else None
            for _, row in base.iterrows():
                tiempo = "" if col_tiempo is None or pd.isna(row.get(col_tiempo)) else str(row.get(col_tiempo)).strip()
                actuales[(str(row["categoria"]), str(row["estilo"]), str(row["sexo"]))] = tiempo
        filas_plantilla = []
        for cat in cats_oficiales:
            for estilo in estilos_oficiales:
                for sexo in ("Masculino", "Femenino"):
                    filas_plantilla.append({
                        "categoria": cat,
                        "estilo": estilo,
                        "sexo": sexo,
                        "tiempo_objetivo": actuales.get((cat, estilo, sexo), ""),
                    })
        for (cat, estilo, sexo), tiempo in actuales.items():
            if sexo == "Ambos":
                filas_plantilla.append({
                    "categoria": cat, "estilo": estilo, "sexo": sexo, "tiempo_objetivo": tiempo,
                })
        buf_marcas = _io.StringIO()
        pd.DataFrame(filas_plantilla).to_csv(buf_marcas, index=False)
        st.download_button(
            "📥 Descargar plantilla de marcas",
            buf_marcas.getvalue().encode("utf-8"),
            "plantilla_marcas_minimas.csv",
            "text/csv",
        )
        st.markdown("---")
        up_marcas = st.file_uploader("Sube tu archivo (CSV o Excel)", type=["csv", "xlsx"], key="up_marcas")
        if up_marcas:
            try:
                df_up = pd.read_csv(up_marcas, encoding="utf-8-sig") if up_marcas.name.lower().endswith(".csv") else pd.read_excel(up_marcas)
                recs, errores, avisos = preparar_carga_marcas(df_up, cats_oficiales, estilos_oficiales)
                if errores:
                    st.error("No se cargó nada. Corrige el archivo y vuelve a subirlo.\n\n" + "\n".join(f"- {e}" for e in errores))
                else:
                    for aviso in avisos:
                        st.warning(aviso)
                    if not recs:
                        st.warning("No hay filas con tiempo para cargar.")
                    else:
                        st.write("🔍 Vista previa de lo que se va a guardar:")
                        st.dataframe(pd.DataFrame(recs), use_container_width=True, hide_index=True)
                        if st.button("🚀 Cargar marcas del archivo", type="primary"):
                            sb = init_connection()
                            if sb:
                                try:
                                    sb.table("marcas_minimas").upsert(
                                        recs, on_conflict="categoria,estilo,sexo"
                                    ).execute()
                                    fresco = sb.table("marcas_minimas").select("*").execute().data
                                    if fresco:
                                        m_df = pd.DataFrame(fresco)
                                        if "segundos_objetivo" in m_df.columns and "segundos" not in m_df.columns:
                                            m_df = m_df.rename(columns={"segundos_objetivo": "segundos"})
                                        st.session_state.marcas_df = m_df
                                    st.session_state.marcas_cargadas = True
                                    st.session_state.marcas_cargadas_msg = f"✅ {len(recs)} marcas cargadas. Las que no venían en el archivo se mantuvieron."
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error BD: {e}")
                            else:
                                nuevas = pd.DataFrame(recs).rename(columns={"segundos_objetivo": "segundos"})
                                previas = st.session_state.marcas_df.copy()
                                if not previas.empty and {"categoria", "estilo", "sexo"}.issubset(previas.columns):
                                    claves = set(zip(nuevas["categoria"], nuevas["estilo"], nuevas["sexo"]))
                                    mask = [
                                        (c, e, s) not in claves
                                        for c, e, s in zip(previas["categoria"], previas["estilo"], previas["sexo"])
                                    ]
                                    previas = previas.loc[mask]
                                st.session_state.marcas_df = pd.concat([previas, nuevas], ignore_index=True)
                                st.session_state.marcas_cargadas = True
                                st.session_state.marcas_cargadas_msg = f"✅ {len(recs)} marcas cargadas en esta sesión. Las que no venían en el archivo se mantuvieron."
                                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al procesar archivo: {e}")


def panel_master():
    """Panel exclusivo del administrador."""
    st.header("🛡️ Panel de Administración Master")
    st.write("Gestiona el acceso de los usuarios nuevos que se han registrado.")
    st.write("Crea cuentas de acceso para tu equipo. Las cuentas creadas aquí se activan automáticamente.")
    
    etiquetas_fichas = {}
    fichas = st.session_state.nadadores_df
    if fichas is not None and not fichas.empty:
        for _, ficha in fichas.iterrows():
            id_ficha = _anio_entero(ficha.get("id_nadador"))
            if id_ficha is None:
                continue
            marca = "" if es_nadador_activo(ficha.get("activo")) else " · inactivo"
            etiquetas_fichas[f"{ficha.get('nombre')} ({ficha.get('grupo') or 'sin grupo'}){marca}"] = id_ficha

    with st.expander("➕ Crear Nueva Cuenta", expanded=True):
        st.caption("La contraseña que escribas es temporal. En el primer ingreso, esa persona tendrá que cambiarla.")
        with st.form("form_crear_usuario"):
            c1, c2 = st.columns(2)
            with c1:
                nuevo_nombre = st.text_input("Nombre Completo")
                nuevo_email = st.text_input("Correo Electrónico")
                nuevos_grupos = st.multiselect("Grupos Asignados (Opcional)", ["Todos"] + lista_grupos())
            with c2:
                nueva_clave = st.text_input("Contraseña Temporal", type="password")
                nuevo_rol = st.selectbox("Rol del Usuario", ["Nadador", "Entrenador", "Directiva", "Master"])
                ficha_cuenta = st.selectbox(
                    "Ficha del nadador (obligatoria si el rol es Nadador)",
                    ["—"] + list(etiquetas_fichas),
                )
            
            if st.form_submit_button("Crear y Autorizar Usuario"):
                if nuevo_nombre and nuevo_email and nueva_clave:
                    if nuevo_email in st.session_state.usuarios_df['email'].values:
                        st.error("Este correo ya existe en la base de datos.")
                    elif nuevo_rol == "Nadador" and ficha_cuenta == "—":
                        st.error("Elige la ficha del nadador. Esa es la información que verá en su dashboard.")
                    else:
                        supabase = init_connection()
                        if supabase:
                            try:
                                rec_usuario = {
                                    "nombre": nuevo_nombre, "email": nuevo_email,
                                    "clave": nueva_clave, "rol": nuevo_rol, "validado": True,
                                    "grupos_asignados": nuevos_grupos,
                                    "debe_cambiar_clave": True,
                                }
                                if nuevo_rol == "Nadador":
                                    rec_usuario["id_nadador"] = int(etiquetas_fichas[ficha_cuenta])
                                pendiente = dict(rec_usuario)
                                ultimo_error = None
                                for _ in range(3):
                                    try:
                                        supabase.table("usuarios").insert(pendiente).execute()
                                        ultimo_error = None
                                        break
                                    except Exception as e_ins:
                                        ultimo_error = e_ins
                                        mensaje = str(e_ins)
                                        quito = False
                                        for col in ("id_nadador", "debe_cambiar_clave"):
                                            if col in pendiente and col in mensaje:
                                                pendiente.pop(col, None)
                                                quito = True
                                        if not quito:
                                            break
                                if ultimo_error is not None:
                                    raise ultimo_error
                                if nuevo_rol == "Nadador" and "id_nadador" not in pendiente:
                                    st.warning("La cuenta se creó, pero la base todavía no puede vincular la ficha. Ejecuta migracion_activo_y_cuenta.sql.")
                                if "debe_cambiar_clave" not in pendiente:
                                    st.warning("La cuenta se creó, pero esta base todavía no obliga a cambiar la contraseña en el primer ingreso. Ejecuta migracion_clave_inicial.sql.")
                                fresco = supabase.table("usuarios").select("*").execute().data
                                if fresco:
                                    u_df = pd.DataFrame(fresco)
                                    if "id" in u_df.columns:
                                        u_df = u_df.rename(columns={"id": "id_usuario"})
                                    st.session_state.usuarios_df = u_df
                                st.success(f"¡Cuenta para {nuevo_nombre} creada! Envíale el correo y la contraseña temporal. Al entrar por primera vez tendrá que cambiarla.")
                            except Exception as e: st.error(f"Error BD: {e}")
                        else:
                            st.info("Prototipo local: Usuario creado temporalmente.")
                else:
                    st.error("Completa todos los campos.")

    st.markdown("---")
    st.subheader("Vincular una cuenta que ya existe")
    st.write("La cuenta entra al dashboard del nadador. La ficha es el registro deportivo. Aquí se unen las dos.")
    cuentas_nad = st.session_state.usuarios_df
    if "rol" in cuentas_nad.columns:
        cuentas_nad = cuentas_nad[cuentas_nad["rol"] == "Nadador"]
    else:
        cuentas_nad = cuentas_nad.iloc[0:0]
    if cuentas_nad.empty or not etiquetas_fichas:
        st.info("Cuando exista una cuenta con rol Nadador y al menos una ficha, podrás vincularlas aquí.")
    else:
        opciones_cuentas = [
            f"{row.get('nombre')} · {row.get('email')}"
            for _, row in cuentas_nad.iterrows()
        ]
        cuenta_sel = st.selectbox("Cuenta", opciones_cuentas, key="vincular_cuenta")
        ficha_sel = st.selectbox("Ficha", list(etiquetas_fichas), key="vincular_ficha")
        if st.button("Guardar vínculo", type="primary"):
            fila_cuenta = cuentas_nad.iloc[opciones_cuentas.index(cuenta_sel)]
            supabase = init_connection()
            if supabase:
                try:
                    supabase.table("usuarios").update(
                        {"id_nadador": int(etiquetas_fichas[ficha_sel])}
                    ).eq("id", int(fila_cuenta["id_usuario"])).execute()
                    fresco = supabase.table("usuarios").select("*").execute().data
                    if fresco:
                        u_df = pd.DataFrame(fresco)
                        if "id" in u_df.columns:
                            u_df = u_df.rename(columns={"id": "id_usuario"})
                        st.session_state.usuarios_df = u_df
                    st.success("La cuenta quedó vinculada a esa ficha.")
                except Exception as e:
                    st.error(f"No se pudo vincular. Si la columna no existe, ejecuta migracion_activo_y_cuenta.sql. Detalle: {e}")
            else:
                st.info("Prototipo local: el vínculo no se guarda en Supabase.")

    st.markdown("---")
    st.subheader("Directorio de Usuarios Activos")
    directorio = st.session_state.usuarios_df.copy()
    try:
        if "id_nadador" in directorio.columns:
            nombres = fichas_por_id(st.session_state.nadadores_df)
            directorio["ficha"] = [
                nombres.get(_anio_entero(valor)) for valor in directorio["id_nadador"]
            ]
    except Exception:
        directorio["ficha"] = ""
    columnas_dir = [c for c in ["id_usuario", "nombre", "email", "rol", "ficha"] if c in directorio.columns]
    st.dataframe(directorio[columnas_dir], hide_index=True, use_container_width=True)


def mostrar_tests():
    """Gestión de Tests de Rendimiento de la Federación."""
    st.header("🏁 Tests de Rendimiento")
    rol = st.session_state.user_role
    if rol not in ['Entrenador', 'Master', 'Directiva']:
        st.warning("Sección no disponible para tu perfil.")
        return
    solo_lectura = (rol == 'Directiva')

    tv1, tv2, tv3 = st.tabs(["Ver Tests", "Crear Test", "Registrar Resultados"])

    # ── PESTAÑA 1: Ver Historial ──────────────────────────────────────────────
    with tv1:
        tst_df = st.session_state.get('tests_df', pd.DataFrame())
        res_df = st.session_state.get('resultados_test_df', pd.DataFrame())
        if tst_df.empty:
            st.info("No hay tests registrados aún. Usa la pestaña 'Crear Test'.")
        else:
            grupos_t = ['Todos'] + sorted(tst_df['grupo'].dropna().unique().tolist()) if 'grupo' in tst_df.columns else ['Todos']
            filtro_t = st.selectbox("Filtrar por grupo:", grupos_t, key="tst_filtro")
            df_show = tst_df if filtro_t == 'Todos' else tst_df[tst_df['grupo'] == filtro_t]
            for _, test in df_show.iterrows():
                with st.expander(f"📌 {test.get('nombre','')} — {test.get('fecha','')} | Grupo: {test.get('grupo','')}"):
                    if test.get('descripcion'):
                        st.write(f"**Descripción:** {test['descripcion']}")
                    t_id = test.get('id', -1)
                    if not res_df.empty and 'id_test' in res_df.columns:
                        res_t = res_df[res_df['id_test'] == t_id]
                        if not res_t.empty:
                            st.markdown("**Resultados:**")
                            nombres = fichas_por_id(st.session_state.nadadores_df)
                            res_t = res_t.copy()
                            if 'id_nadador' in res_t.columns:
                                res_t['nombre'] = [
                                    nombres.get(_anio_entero(valor)) for valor in res_t['id_nadador']
                                ]
                            merged = res_t
                            cols_r = [c for c in ['nombre', 'resultado', 'observaciones'] if c in merged.columns]
                            st.dataframe(merged[cols_r], use_container_width=True, hide_index=True)
                        else:
                            st.caption("Sin resultados registrados para este test.")

    # ── PESTAÑA 2: Crear Test ─────────────────────────────────────────────────
    with tv2:
        if solo_lectura:
            st.info("👁️ Solo lectura — no puedes crear tests.")
        else:
            with st.form("form_crear_test"):
                ct1, ct2 = st.columns(2)
                with ct1:
                    nombre_t = st.text_input("Nombre del Test", placeholder="Ej: 10×400m Libre")
                    fecha_t  = st.date_input("Fecha", datetime.today(), key="fecha_test")
                with ct2:
                    grupo_t  = st.selectbox("Grupo", ["Todos"] + lista_grupos())
                    desc_t   = st.text_area("Descripción", placeholder="Ej: 10 rep. de 400m libre con 30s descanso")
                if st.form_submit_button("✅ Crear Test", type="primary"):
                    if nombre_t.strip():
                        rec_t = {"nombre": nombre_t, "fecha": fecha_t.strftime('%Y-%m-%d'), "grupo": grupo_t, "descripcion": desc_t}
                        sb = init_connection()
                        if sb:
                            try:
                                sb.table("tests").insert(rec_t).execute()
                                st.success(f"✅ Test '{nombre_t}' creado.")
                                st.rerun()
                            except Exception as e: st.error(f"Error BD: {e}")
                        else:
                            st.success("Modo local: Test creado (simulado).")
                    else:
                        st.error("El nombre del test es obligatorio.")

    # ── PESTAÑA 3: Registrar Resultados ───────────────────────────────────────
    with tv3:
        if solo_lectura:
            st.info("👁️ Solo lectura.")
        else:
            tst_df2 = st.session_state.get('tests_df', pd.DataFrame())
            if tst_df2.empty:
                st.warning("Primero crea un test en la pestaña anterior.")
            else:
                opciones_t = tst_df2.apply(lambda r: f"{r.get('nombre','')} ({r.get('fecha','')})", axis=1).tolist()
                idx_t = st.selectbox("Selecciona el Test:", range(len(opciones_t)), format_func=lambda i: opciones_t[i])
                test_row = tst_df2.iloc[idx_t]
                test_id  = test_row.get('id')
                grupo_ts = test_row.get('grupo', 'Todos')

                nad_df2 = filtrar_nadadores_activos(st.session_state.nadadores_df)
                nads_filtrados = nad_df2 if grupo_ts == 'Todos' else nad_df2[nad_df2['grupo'] == grupo_ts]

                if nads_filtrados.empty:
                    st.warning("No hay nadadores en este grupo.")
                else:
                    res_input = pd.DataFrame({
                        'id_nadador':   nads_filtrados['id_nadador'].values,
                        'nombre':       nads_filtrados['nombre'].values,
                        'resultado':    '',
                        'observaciones': ''
                    })
                    st.write(f"**Test:** {test_row.get('nombre', '')}")
                    edited_r = st.data_editor(
                        res_input,
                        column_config={
                            "id_nadador": None,
                            "nombre": st.column_config.TextColumn("Nadador", disabled=True),
                            "resultado": st.column_config.TextColumn("Resultado"),
                            "observaciones": st.column_config.TextColumn("Observaciones")
                        },
                        use_container_width=True, hide_index=True, num_rows="fixed"
                    )
                    if st.button("💾 Guardar Resultados del Test", type="primary"):
                        validos = edited_r[edited_r['resultado'].astype(str).str.strip() != '']
                        if validos.empty:
                            st.warning("No hay resultados para guardar.")
                        else:
                            recs_r = [{"id_test": int(test_id), "id_nadador": int(r['id_nadador']),
                                       "resultado": r['resultado'], "observaciones": r.get('observaciones','')
                                      } for _, r in validos.iterrows()]
                            sb2 = init_connection()
                            if sb2:
                                try:
                                    sb2.table("resultados_test").insert(recs_r).execute()
                                    st.success(f"✅ {len(recs_r)} resultados guardados.")
                                    st.rerun()
                                except Exception as e: st.error(f"Error BD: {e}")
                            else:
                                st.success("Modo local: Resultados guardados (simulado).")


# --- Lógica Principal de la Aplicación ---

# Inicializar st.session_state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = None
    st.session_state.user_info = None
    # Cargar datos una sola vez (desde BD si existe, si no locales)
    (
        nadadores_df, tiempos_df, usuarios_df, marcas_df,
        incidencias_df, tests_df, resultados_test_df, datos_fisicos_df, tiempos_ent_df,
        grupos_df,
    ) = cargar_datos()
    st.session_state.nadadores_df         = nadadores_df
    st.session_state.tiempos_df           = tiempos_df
    st.session_state.usuarios_df          = usuarios_df
    st.session_state.marcas_df            = marcas_df
    st.session_state.incidencias_df       = incidencias_df
    st.session_state.tests_df             = tests_df
    st.session_state.resultados_test_df   = resultados_test_df
    st.session_state.datos_fisicos_df     = datos_fisicos_df
    st.session_state.tiempos_ent_df       = tiempos_ent_df
    st.session_state.grupos_df            = grupos_df
    token_url = _token_de_url()
    token_cookie = _token_de_cookie()
    usuario_previo = restaurar_usuario(token_url, st.session_state.usuarios_df) if token_url else None
    if usuario_previo is None and token_cookie and token_cookie != token_url:
        usuario_previo = restaurar_usuario(token_cookie, st.session_state.usuarios_df)
    if usuario_previo is None and token_url:
        try:
            del st.query_params["sesion"]
        except Exception:
            pass
    if usuario_previo is not None:
        st.session_state.logged_in = True
        st.session_state.user_role = usuario_previo["rol"]
        st.session_state.user_name = usuario_previo["nombre"]
        st.session_state.user_info = usuario_previo.to_dict()

# --- Pantalla de Login ---
if st.session_state.pop("borrar_cookie", False):
    cerrar_sesion_guardada()

if not st.session_state.logged_in:
    col1, col2 = st.columns([1, 5])
    with col1:
        # Asegúrate de que tu logo se llame 'logo.png' y esté en la misma carpeta
        try:
            st.image("logo.png", width=120)
        except Exception:
            st.warning("No se encontró 'logo.png'")
    
    with col2:
        st.title("Sistema de Progreso de Nadadores")
        st.subheader("Club Acuático Valdivia 🏊‍♂️")

    st.write("---")
    
    st.subheader("🔑 Iniciar Sesión")
    email_login = st.text_input("Correo electrónico", placeholder="ejemplo@club.cl").strip().lower()
    pass_login = st.text_input("Contraseña", type="password")
    
    if st.button("Entrar", type="primary"):
        user_match = st.session_state.usuarios_df[st.session_state.usuarios_df['email'].str.lower() == email_login]
        if not user_match.empty:
            user_info = user_match.iloc[0]
            if user_info['clave'] == pass_login:
                if user_info['validado'] or user_info['rol'] == 'Master':
                    st.session_state.logged_in = True
                    st.session_state.user_role = user_info['rol']
                    st.session_state.user_name = user_info['nombre']
                    st.session_state.user_info = user_info.to_dict()
                    anclar_sesion(user_info["id_usuario"])
                    st.rerun()
                else:
                    st.error("Tu perfil aún no ha sido validado.")
            else:
                st.error("Contraseña incorrecta.")
        else:
            st.error("Correo no encontrado. Solicita tu cuenta al administrador.")

# --- Contenido Principal (si el usuario está logueado) ---
else:
    pendiente_clave = cuenta_debe_cambiar_clave(st.session_state.user_info)
    # --- Menú de Navegación Condicional ---
    opciones_menu = ["📊 Dashboard"]
    if st.session_state.user_role in ['Entrenador', 'Directiva', 'Master']:
        opciones_menu.append("🗓️ Asistencia")
    if st.session_state.user_role in ['Entrenador', 'Directiva', 'Master']:
        opciones_menu.append("👥 Perfiles")
    if st.session_state.user_role in ['Entrenador', 'Master', 'Directiva']:
        opciones_menu.extend(["⏱️ Registrar Tiempos", "⚙️ Configurar Marcas", "🏁 Tests"])
    if st.session_state.user_role == 'Master':
        opciones_menu.append("🛡️ Admin Usuarios")
    
    paginas = {
        "📊 Dashboard": mostrar_dashboard,
        "🗓️ Asistencia": mostrar_asistencia,
        "👥 Perfiles": gestionar_nadadores,
        "⏱️ Registrar Tiempos": registrar_tiempos,
        "⚙️ Configurar Marcas": configurar_marcas,
        "🏁 Tests": mostrar_tests,
        "🛡️ Admin Usuarios": panel_master,
    }
    anclar_sesion(st.session_state.user_info.get("id_usuario"))

    st.sidebar.image("logo.png", use_container_width=True)
    st.sidebar.success(f"{st.session_state.user_name} | {st.session_state.user_role}")
    correo_cuenta = ""
    if isinstance(st.session_state.user_info, dict):
        correo_cuenta = str(st.session_state.user_info.get("email") or "")
    if correo_cuenta:
        st.sidebar.caption(correo_cuenta)

    st.sidebar.markdown("---")
    if not pendiente_clave:
        if st.sidebar.button("Cambiar contraseña", use_container_width=True):
            st.session_state.menu_cambiar_clave = not st.session_state.get("menu_cambiar_clave", False)
        if st.session_state.get("menu_cambiar_clave"):
            with st.sidebar.form("form_clave_menu"):
                clave_menu = st.text_input("Nueva contraseña", type="password")
                clave_menu_2 = st.text_input("Repite la nueva contraseña", type="password")
                if st.form_submit_button("Guardar contraseña", type="primary"):
                    ok_menu, msg_menu = guardar_clave_propia(clave_menu, clave_menu_2)
                    if ok_menu:
                        st.success(msg_menu)
                    else:
                        st.error(msg_menu)
        st.sidebar.markdown("---")
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.user_name = None
        st.session_state.user_info = None
        st.session_state.menu_cambiar_clave = False
        st.session_state.borrar_cookie = True
        cerrar_sesion_guardada()
        st.rerun()

    if pendiente_clave:
        st.header("Cambia tu contraseña")
        st.write(
            f"{st.session_state.user_name}, esta cuenta es nueva. "
            "Antes de continuar tienes que reemplazar la contraseña temporal. "
            "La anterior no se muestra."
        )
        with st.form("form_clave_obligatoria"):
            clave_obl = st.text_input("Nueva contraseña", type="password")
            clave_obl_2 = st.text_input("Repite la nueva contraseña", type="password")
            if st.form_submit_button("Guardar y entrar", type="primary"):
                ok_obl, msg_obl = guardar_clave_propia(clave_obl, clave_obl_2)
                if ok_obl:
                    st.rerun()
                else:
                    st.error(msg_obl)
    else:
        solapas = st.tabs(opciones_menu)
        for solapa, nombre in zip(solapas, opciones_menu):
            with solapa:
                paginas[nombre]()
