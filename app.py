# ========================================
# Archivo Único: app.py
# Guarda todo este código en un solo archivo llamado app.py
# y corre el comando: streamlit run app.py
# ========================================

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
    /* Estilos para centrar y mejorar el menú de navegación */
    div.row-widget.stRadio > div {
        flex-direction: row;
        justify-content: center;
        gap: 2rem;
    }
    div.row-widget.stRadio > div > label {
        border: 2px solid #007bff;
        padding: 5px 15px;
        border-radius: 20px;
        background-color: #f0f2f6;
    }
    div.row-widget.stRadio > div > label:hover {
        background-color: #e1e5eb;
    }
    /* Ocultar el punto del radio button */
    div.row-widget.stRadio > div > label > div::before {
        display: none;
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
            n_df = pd.DataFrame(nad) if nad else pd.DataFrame(columns=['id', 'nombre', 'grupo', 'categoria', 'sexo'])
            t_df = pd.DataFrame(tie) if tie else pd.DataFrame(columns=['id', 'id_nadador', 'fecha', 'lugar', 'estilo', 'tiempo_formateado', 'segundos_totales', 'tipo_piscina'])
            m_df = pd.DataFrame(mar) if mar else pd.DataFrame(columns=['categoria', 'estilo', 'sexo', 'segundos'])

            # Nuevas tablas (tolerantes a que no existan aún)
            inc_df   = _safe("incidencias_clase", _cols_inc)
            tst_df   = _safe("tests", _cols_tst)
            res_df   = _safe("resultados_test", _cols_res)
            dfis_df  = _safe("datos_fisicos", _cols_dfis)
            tent_df  = _safe("tiempos_entrenamiento", _cols_tent)

            if not u_df.empty: u_df.rename(columns={'id': 'id_usuario'}, inplace=True)

            # Normalizar columnas de nadadores
            if not n_df.empty:
                if 'id' in n_df.columns:
                    if 'id_nadador' in n_df.columns:
                        n_df = n_df.drop(columns=['id_nadador'])
                    n_df = n_df.rename(columns={'id': 'id_nadador'})
                elif 'id_nadador' not in n_df.columns:
                    n_df.insert(0, 'id_nadador', range(1, len(n_df) + 1))

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
                return n_df, t_df, u_df, m_df, inc_df, tst_df, res_df, dfis_df, tent_df
        except Exception as e:
            st.sidebar.warning(f"Error conectando a BD: {e}. Usando modo local.")

    # --- FALLBACK DE PROTOTIPO ---
    nadadores_df = pd.DataFrame([
        {'id_nadador': 1, 'nombre': 'Ana', 'grupo': 'Competitivo', 'categoria': 'Infantil B1', 'sexo': 'Femenino'},
        {'id_nadador': 2, 'nombre': 'Luis', 'grupo': 'Competitivo', 'categoria': 'Infantil A', 'sexo': 'Masculino'},
        {'id_nadador': 3, 'nombre': 'Carla', 'grupo': 'Precompetitivo', 'categoria': 'Juvenil A1', 'sexo': 'Femenino'},
        {'id_nadador': 4, 'nombre': 'Pedro', 'grupo': 'Elite', 'categoria': 'Mayores', 'sexo': 'Masculino'},
    ])
    tiempos_df = pd.DataFrame([
        {'id_nadador': 1, 'fecha': '2023-10-15', 'lugar': 'Piscina Municipal', 'estilo': '50m Libre', 'tiempo_formateado': '00:28,50', 'segundos_totales': 28.5, 'tipo_piscina': 'Piscina Corta (25m)'},
        {'id_nadador': 1, 'fecha': '2023-11-20', 'lugar': 'Competencia Regional', 'estilo': '50m Libre', 'tiempo_formateado': '00:27,90', 'segundos_totales': 27.9, 'tipo_piscina': 'Piscina Larga (50m)'},
        {'id_nadador': 2, 'fecha': '2023-11-20', 'lugar': 'Competencia Regional', 'estilo': '100m Pecho', 'tiempo_formateado': '01:15,30', 'segundos_totales': 75.3, 'tipo_piscina': 'Piscina Corta (25m)'},
        {'id_nadador': 4, 'fecha': '2023-11-20', 'lugar': 'Competencia Regional', 'estilo': '200m Combinado', 'tiempo_formateado': '02:10,80', 'segundos_totales': 130.8, 'tipo_piscina': 'Piscina Larga (50m)'},
    ])
    usuarios_df = pd.DataFrame([
        {'id_usuario': 999, 'nombre': 'Super Master', 'rol': 'Master', 'grupos_asignados': [], 'email': 'master@club.cl', 'validado': True, 'clave': 'admin123'},
        {'id_usuario': 888, 'nombre': 'Junta Directiva', 'rol': 'Directiva', 'grupos_asignados': [], 'email': 'directiva@club.cl', 'validado': True, 'clave': '1234'},
        {'id_usuario': 101, 'nombre': 'Entrenador Alex', 'rol': 'Entrenador', 'grupos_asignados': ['Elite','Competitivo', 'Precompetitivo'], 'email': 'alex@club.cl', 'validado': True, 'clave': '1234'},
        {'id_usuario': 1, 'nombre': 'Ana', 'rol': 'Nadador', 'grupos_asignados': [], 'email': 'ana@club.cl', 'validado': True, 'clave': '1234'},
        {'id_usuario': 4, 'nombre': 'Pedro', 'rol': 'Nadador', 'grupos_asignados': [], 'email': 'pedro@club.cl', 'validado': True, 'clave': '1234'},
        {'id_usuario': 99, 'nombre': 'Usuario Nuevo', 'rol': 'Pendiente', 'grupos_asignados': [], 'email': 'nuevo@gmail.com', 'validado': False, 'clave': '1234'},
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
        pd.DataFrame(columns=_cols_tent)
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
        # Directiva obtiene todos los grupos; Entrenador solo los suyos (o todos si tiene el permiso 'Todos')
        grupos_asignados = user_info['grupos_asignados'] if st.session_state.user_role == 'Entrenador' else st.session_state.nadadores_df['grupo'].unique().tolist()
        if st.session_state.user_role == 'Entrenador' and ('Todos' in user_info['grupos_asignados'] or not user_info['grupos_asignados']):
            grupos_asignados = st.session_state.nadadores_df['grupo'].unique().tolist()
        
        # Opciones de resumen
        grupo_seleccionado = st.selectbox("Selecciona un grupo para ver el resumen masivo:", ["Todos"] + grupos_asignados)
        if grupo_seleccionado == "Todos":
            nadadores_del_grupo = st.session_state.nadadores_df[st.session_state.nadadores_df['grupo'].isin(grupos_asignados)]
        else:
            nadadores_del_grupo = st.session_state.nadadores_df[st.session_state.nadadores_df['grupo'] == grupo_seleccionado]
            
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
        id_nadador = user_info['id_usuario']
        tiempos_nadador = st.session_state.tiempos_df[st.session_state.tiempos_df['id_nadador'] == id_nadador]
        
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
    grupos_asignados = user_info.get('grupos_asignados', [])
    if solo_lectura or 'Todos' in grupos_asignados or not grupos_asignados:
        grupos_asignados = st.session_state.nadadores_df['grupo'].unique().tolist()

    col1, col2 = st.columns(2)
    with col1:
        grupo_seleccionado = st.selectbox("Grupo:", grupos_asignados)
    with col2:
        fecha_seleccionada = st.date_input("Fecha de la clase:", datetime.today())

    nadadores_del_grupo = st.session_state.nadadores_df[st.session_state.nadadores_df['grupo'] == grupo_seleccionado]
    st.subheader(f"Lista de nadadores para el grupo: {grupo_seleccionado}")

    asistencia_df = nadadores_del_grupo[['id_nadador', 'nombre']].copy()
    asistencia_df['presente'] = False

    edited_df = st.data_editor(
        asistencia_df,
        column_config={
            "id_nadador": None,
            "nombre": st.column_config.TextColumn("Nadador", disabled=True),
            "presente": st.column_config.CheckboxColumn("¿Presente?", default=False)
        },
        use_container_width=True,
        hide_index=True,
        disabled=solo_lectura
    )

    if not solo_lectura:
        if st.button("Guardar Asistencia", type="primary"):
            presentes = edited_df[edited_df['presente'] == True]
            supabase = init_connection()
            if supabase:
                fecha_str = fecha_seleccionada.strftime('%Y-%m-%d')
                data_to_insert = [{"id_nadador": int(row['id_nadador']), "fecha": fecha_str, "estado": "Presente"} for _, row in presentes.iterrows()]
                if data_to_insert:
                    try:
                        supabase.table("asistencias").upsert(data_to_insert).execute()
                    except Exception as e:
                        st.error(f"Error BD al guardar asistencias: {e}")
            st.success(f"Asistencia guardada para el {fecha_seleccionada.strftime('%d-%m-%Y')}. {len(presentes)} nadador(es) presente(s).")

    # --- Sección de Incidencias de Clase ---
    st.markdown("---")
    st.subheader("📝 Incidencias de la Clase")

    inc_df = st.session_state.get('incidencias_df', pd.DataFrame())
    # Filtrar incidencias de la fecha y grupo seleccionados
    if not inc_df.empty and 'fecha' in inc_df.columns:
        fecha_str_inc = fecha_seleccionada.strftime('%Y-%m-%d')
        inc_hoy = inc_df[
            (inc_df['fecha'].astype(str) == fecha_str_inc) &
            (inc_df['grupo'].astype(str) == grupo_seleccionado)
        ] if 'grupo' in inc_df.columns else inc_df[inc_df['fecha'].astype(str) == fecha_str_inc]
        if not inc_hoy.empty:
            for _, row in inc_hoy.iterrows():
                tipo_icon = {"Nadador Individual": "👤", "Clase Completa": "🚨", "Test Federación": "🏁"}.get(str(row.get('tipo','')), "📌")
                st.info(f"{tipo_icon} **{row.get('tipo','')}** — {row.get('descripcion','')}")
        else:
            st.caption("No hay incidencias registradas para esta clase.")
    else:
        st.caption("No hay incidencias registradas aún.")

    if not solo_lectura:
        with st.expander("➕ Registrar Nueva Incidencia"):
            with st.form("form_incidencia"):
                tipo_inc = st.selectbox(
                    "Tipo de Incidencia:",
                    ["Nadador Individual", "Clase Completa", "Test Federación"]
                )
                nadador_inc = None
                if tipo_inc == "Nadador Individual":
                    opciones_nad = nadadores_del_grupo['nombre'].tolist()
                    nadador_inc_nombre = st.selectbox("Nadador afectado:", opciones_nad)
                    fila_nad = nadadores_del_grupo[nadadores_del_grupo['nombre'] == nadador_inc_nombre]
                    nadador_inc = int(fila_nad.iloc[0]['id_nadador']) if not fila_nad.empty else None

                descripcion_inc = st.text_area(
                    "Descripción:",
                    placeholder="Describe la incidencia. Ej: El nadador se retiró antes por mareos. / Clase suspendida por corte de luz."
                )
                if st.form_submit_button("💾 Guardar Incidencia", type="primary"):
                    if descripcion_inc.strip():
                        rec_inc = {
                            "fecha": fecha_seleccionada.strftime('%Y-%m-%d'),
                            "grupo": grupo_seleccionado,
                            "tipo": tipo_inc,
                            "id_nadador": nadador_inc,
                            "descripcion": descripcion_inc.strip()
                        }
                        supabase = init_connection()
                        if supabase:
                            try:
                                supabase.table("incidencias_clase").insert(rec_inc).execute()
                                st.success("✅ Incidencia registrada correctamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error BD: {e}")
                        else:
                            st.success("Modo local: Incidencia guardada (simulado).")
                    else:
                        st.error("La descripción no puede estar vacía.")


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
    _nad_df = st.session_state.nadadores_df.copy()
    _id_col = 'id_nadador' if 'id_nadador' in _nad_df.columns else 'id'
    nadadores = _nad_df['nombre'].tolist()

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


def gestionar_nadadores():
    """Muestra el panel de gestión de perfiles de los nadadores."""
    st.header("👥 Gestión de Perfiles de Nadadores")
    if st.session_state.user_role not in ['Entrenador', 'Master']:
        st.error("Solamente los entrenadores autorizados pueden modificar los perfiles.")
        return

    tp1, tp2 = st.tabs(["Perfiles y Grupos", "📏 Datos Fisiológicos"])

    with tp1:
        st.write("Crea nuevos nadadores o edita el grupo, categoría y sexo de los nadadores actuales.")
        df = st.session_state.nadadores_df.copy()
        if 'id' in df.columns:
            df = df.drop(columns=['id'])
        cats_oficiales = ['Infantil A', 'Infantil B1', 'Infantil B2', 'Juvenil A1', 'Juvenil A2', 'Juvenil B', 'Mayores']
        edited_df = st.data_editor(
            df, use_container_width=True, num_rows="dynamic",
            column_config={
                "categoria": st.column_config.SelectboxColumn("Categoría", options=cats_oficiales, required=True),
                "sexo": st.column_config.SelectboxColumn("Sexo", options=["Masculino", "Femenino"], required=True)
            }
        )
        if st.button("Guardar Perfiles", type="primary"):
            st.session_state.nadadores_df = edited_df.copy()
            supabase = init_connection()
            if supabase:
                try:
                    for _, row in edited_df.iterrows():
                        r = row.to_dict()
                        id_val = r.pop('id_nadador', None)
                        r_clean = {k: v for k, v in r.items() if pd.notna(v)}
                        if pd.notna(id_val):
                            supabase.table("nadadores").update(r_clean).eq("id", int(id_val)).execute()
                        else:
                            supabase.table("nadadores").insert(r_clean).execute()
                    nad_fresh = supabase.table("nadadores").select("*").execute().data
                    if nad_fresh:
                        fresh_df = pd.DataFrame(nad_fresh)
                        if 'id' in fresh_df.columns:
                            if 'id_nadador' in fresh_df.columns:
                                fresh_df = fresh_df.drop(columns=['id_nadador'])
                            fresh_df = fresh_df.rename(columns={'id': 'id_nadador'})
                        st.session_state.nadadores_df = fresh_df
                    st.success("✅ Guardado seguro en Supabase.")
                except Exception as e:
                    st.error(f"Error Supabase guardando perfiles: {e}")
            else:
                st.success("Perfiles guardados en el Prototipo Temporal.")

    with tp2:
        st.write("Registra y visualiza la evolución física de cada nadador. Incluye medidas clave para el rendimiento en natación.")
        nad_fis_sel = st.selectbox("Selecciona un nadador:", st.session_state.nadadores_df['nombre'].tolist(), key="nad_fis")
        nad_fis_row = st.session_state.nadadores_df[st.session_state.nadadores_df['nombre'] == nad_fis_sel]
        id_nad_fis = int(nad_fis_row.iloc[0]['id_nadador']) if not nad_fis_row.empty else None

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

def configurar_marcas():
    """Muestra el contenido de la configuración de Marcas Mínimas por Categoría."""
    st.header("⚙️ Configuración de Marcas Mínimas")
    
    # 1. Verificación de permisos
    if st.session_state.user_role not in ['Entrenador', 'Master', 'Directiva']:
        st.error("No tienes permiso para configurar las metas del equipo.")
        return
        
    st.info("ℹ️ Ingresa los tiempos en formato **MM:SS,MS** (Ejemplo: 01:05,50). La columna 'Segundos' se calculará automáticamente al guardar.")
    
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
        hide_index=True
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


def panel_master():
    """Panel exclusivo del administrador."""
    st.header("🛡️ Panel de Administración Master")
    st.write("Gestiona el acceso de los usuarios nuevos que se han registrado.")
    st.write("Crea cuentas de acceso para tu equipo. Las cuentas creadas aquí se activan automáticamente.")
    
    with st.expander("➕ Crear Nueva Cuenta", expanded=True):
        with st.form("form_crear_usuario"):
            c1, c2 = st.columns(2)
            with c1:
                nuevo_nombre = st.text_input("Nombre Completo")
                nuevo_email = st.text_input("Correo Electrónico")
                nuevos_grupos = st.multiselect("Grupos Asignados (Opcional)", ["Todos", "Competitivo", "Precompetitivo", "Formativo", "Elite", "Master"])
            with c2:
                nueva_clave = st.text_input("Contraseña Temporal", type="password")
                nuevo_rol = st.selectbox("Rol del Usuario", ["Nadador", "Entrenador", "Directiva", "Master"])
            
            if st.form_submit_button("Crear y Autorizar Usuario"):
                if nuevo_nombre and nuevo_email and nueva_clave:
                    if nuevo_email in st.session_state.usuarios_df['email'].values:
                        st.error("Este correo ya existe en la base de datos.")
                    else:
                        supabase = init_connection()
                        if supabase:
                            try:
                                supabase.table("usuarios").insert({
                                    "nombre": nuevo_nombre, "email": nuevo_email, 
                                    "clave": nueva_clave, "rol": nuevo_rol, "validado": True,
                                    "grupos_asignados": nuevos_grupos
                                }).execute()
                                st.success(f"¡Cuenta para {nuevo_nombre} creada exitosamente en BD! Ya le puedes enviar su correo y contraseña provisional.")
                            except Exception as e: st.error(f"Error BD: {e}")
                        else:
                            st.info("Prototipo local: Usuario creado temporalmente.")
                else:
                    st.error("Completa todos los campos.")
                    
    st.markdown("---")
    st.subheader("Directorio de Usuarios Activos")
    st.dataframe(st.session_state.usuarios_df[['id_usuario', 'nombre', 'email', 'rol']], hide_index=True, use_container_width=True)


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
                            nad_ref = st.session_state.nadadores_df[['id_nadador', 'nombre']]
                            merged = res_t.merge(nad_ref, on='id_nadador', how='left') if 'id_nadador' in res_t.columns else res_t
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
                    grupo_t  = st.selectbox("Grupo", ['Competitivo', 'Precompetitivo', 'Elite', 'Formativo', 'Todos'])
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

                nad_df2  = st.session_state.nadadores_df
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
        incidencias_df, tests_df, resultados_test_df, datos_fisicos_df, tiempos_ent_df
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

# --- Pantalla de Login ---
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
                    st.rerun()
                else:
                    st.error("Tu perfil aún no ha sido validado.")
            else:
                st.error("Contraseña incorrecta.")
        else:
            st.error("Correo no encontrado. Solicita tu cuenta al administrador.")

# --- Contenido Principal (si el usuario está logueado) ---
else:
    # --- Menú de Navegación Condicional ---
    opciones_menu = ["📊 Dashboard"]
    if st.session_state.user_role in ['Entrenador', 'Directiva', 'Master']:
        opciones_menu.append("🗓️ Asistencia")
    if st.session_state.user_role in ['Entrenador', 'Master']:
        opciones_menu.append("👥 Perfiles")
    if st.session_state.user_role in ['Entrenador', 'Master', 'Directiva']:
        opciones_menu.extend(["⏱️ Registrar Tiempos", "⚙️ Configurar Marcas", "🏁 Tests"])
    if st.session_state.user_role == 'Master':
        opciones_menu.append("🛡️ Admin Usuarios")
    
    page = st.radio(
        "Navegación",
        opciones_menu,
        label_visibility="collapsed",
        horizontal=True,
        key="navigation"
    )
    
    # Botón de cerrar sesión en la barra lateral
    st.sidebar.image("logo.png", use_container_width=True)
    st.sidebar.success(f"{st.session_state.user_name} | {st.session_state.user_role}")
    
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ Mi Cuenta"):
        nueva_pass = st.text_input("Nueva Contraseña", type="password", key="new_pass")
        if st.checkbox("Cambiar Contraseña", key="chk_pass"):
            if nueva_pass:
                supabase = init_connection()
                if supabase:
                    try:
                        uid = int(st.session_state.user_info['id_usuario'])
                        supabase.table("usuarios").update({"clave": nueva_pass}).eq("id", uid).execute()
                        st.success("Contraseña actualizada en BD.")
                        st.session_state.user_info['clave'] = nueva_pass
                    except Exception as e: st.error(f"Error BD: {e}")
                else:
                    st.success("Contraseña actualizada en modo local.")
            else:
                st.error("Escribe una contraseña válida.")
                
    st.sidebar.markdown("---")            
    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.user_name = None
        st.session_state.user_info = None
        st.rerun()

    st.markdown("---") # Separador visual

    # --- Renderizado de la Página Seleccionada ---
    if page == "📊 Dashboard":
        mostrar_dashboard()
    elif page == "🗓️ Asistencia":
        mostrar_asistencia()
    elif page == "⏱️ Registrar Tiempos":
        registrar_tiempos()
    elif page == "👥 Perfiles":
        gestionar_nadadores()
    elif page == "⚙️ Configurar Marcas":
        configurar_marcas()
    elif page == "🏁 Tests":
        mostrar_tests()
    elif page == "🛡️ Admin Usuarios":
        panel_master()
