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
            
            if not u_df.empty: u_df.rename(columns={'id': 'id_usuario'}, inplace=True)

            # Normalizar columnas de nadadores:
            # SIEMPRE usar el id auto-generado de Supabase como llave FK confiable
            if not n_df.empty:
                if 'id' in n_df.columns:
                    if 'id_nadador' in n_df.columns:
                        n_df = n_df.drop(columns=['id_nadador'])  # Descartar columna usuario (puede tener NULLs)
                    n_df = n_df.rename(columns={'id': 'id_nadador'})
                elif 'id_nadador' not in n_df.columns:
                    n_df.insert(0, 'id_nadador', range(1, len(n_df) + 1))

            # Normalizar columnas de tiempos (compatibilidad con esquemas viejos y nuevos)
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

            # Normalizar columnas de marcas_minimas
            if not m_df.empty:
                if 'segundos_objetivo' in m_df.columns and 'segundos' not in m_df.columns:
                    m_df.rename(columns={'segundos_objetivo': 'segundos'}, inplace=True)

            # Si hay usuarios en Base de Datos anulamos el fallback
            if not u_df.empty:
                return n_df, t_df, u_df, m_df
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
    
    return nadadores_df, tiempos_df, usuarios_df, marcas_minimas_df

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

                            # Traza de tiempos del nadador
                            _fig_ev.add_trace(go.Scatter(
                                x=_df_est['fecha'],
                                y=_df_est[_sec_col_ev],
                                mode='lines+markers',
                                name=nadador_seleccionado,
                                line=dict(color='#1f77b4', width=3),
                                marker=dict(size=9),
                                customdata=_df_est[_tf_col].values,
                                hovertemplate='<b>%{customdata}</b><br>%{x|%d/%m/%Y}<extra></extra>'
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
    """Muestra el contenido de la página de Asistencia."""
    st.header("Registro de Asistencia 🗓️")
    if st.session_state.user_role != 'Entrenador':
        st.warning("Esta sección es solo para entrenadores.")
        return

    user_info = st.session_state.user_info
    grupos_asignados = user_info['grupos_asignados']
    if 'Todos' in grupos_asignados or not grupos_asignados:
        grupos_asignados = st.session_state.nadadores_df['grupo'].unique().tolist()
    
    col1, col2 = st.columns(2)
    with col1:
        grupo_seleccionado = st.selectbox("Grupo:", grupos_asignados)
    with col2:
        fecha_seleccionada = st.date_input("Fecha de la clase:", datetime.today())

    nadadores_del_grupo = st.session_state.nadadores_df[st.session_state.nadadores_df['grupo'] == grupo_seleccionado]
    st.subheader(f"Lista de nadadores para el grupo: {grupo_seleccionado}")
    
    # Preparar DataFrame para Data Editor de asistencia
    asistencia_df = nadadores_del_grupo[['id_nadador', 'nombre']].copy()
    asistencia_df['estado'] = 'Ausente' # Por defecto
    
    edited_df = st.data_editor(
        asistencia_df,
        column_config={
            "id_nadador": None, # Ocultamos el campo en el UI
            "nombre": st.column_config.TextColumn("Nadador", disabled=True),
            "estado": st.column_config.SelectboxColumn("Asistencia", options=["Presente", "Ausente"], required=True)
        },
        use_container_width=True,
        hide_index=True
    )
        
    if st.button("Guardar Asistencia", type="primary"):
        presentes = edited_df[edited_df['estado'] == 'Presente']
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

def registrar_tiempos():
    st.header("Registrar Nuevos Tiempos ⏱️")
    if st.session_state.user_role not in ['Entrenador', 'Master', 'Directiva']:
        st.warning("Sección restringida.")
        return

    estilos_natacion = [
        '50 Libre', '100 Libre', '200 Libre', '400 Libre', '800 Libre', '1500 Libre',
        '50 Espalda', '100 Espalda', '200 Espalda', '50 Pecho', '100 Pecho', '200 Pecho',
        '50 Mariposa', '100 Mariposa', '200 Mariposa', '100 IM', '200 IM', '400 IM'
    ]

    nadadores = st.session_state.nadadores_df['nombre'].tolist()
    nadador_seleccionado = st.selectbox("Seleccionar Nadador:", nadadores)

    tab1, tab2 = st.tabs(["Registro Manual", "Carga Masiva"])
    
    with tab1:
        with st.form("form_tiempos"):
            col1, col2 = st.columns(2)
            with col1:
                fecha = st.date_input("Fecha", datetime.today())
                estilo = st.selectbox("Estilo:", estilos_natacion)
            with col2:
                lugar = st.text_input("Lugar / Competencia")
                tiempo_input = st.text_input("Tiempo (MM:SS,MS)", placeholder="01:05,50")
            tipo_piscina = st.selectbox(
                "Tipo de Piscina:",
                ["Piscina Corta (25m)", "Piscina Larga (50m)"],
                format_func=lambda x: f"🏊 {x}" if "Corta" in x else f"🌊 {x}"
            )
            
            if st.form_submit_button("Guardar Tiempo"):
                secs = convertir_tiempo_a_segundos(tiempo_input)
                supabase = init_connection()
                if supabase:
                    # Buscar el id del nadador de forma robusta
                    nadador_row = st.session_state.nadadores_df[
                        st.session_state.nadadores_df['nombre'] == nadador_seleccionado
                    ]
                    id_nad = None
                    if not nadador_row.empty:
                        fila = nadador_row.iloc[0]
                        # Intentar con 'id_nadador' primero, luego 'id'
                        for col_id in ['id_nadador', 'id']:
                            if col_id in fila.index and pd.notna(fila[col_id]):
                                id_nad = fila[col_id]
                                break
                    
                    # Si no se encontró localmente, consultar Supabase directamente
                    if id_nad is None:
                        try:
                            res = supabase.table("nadadores").select("id").eq("nombre", nadador_seleccionado).execute()
                            if res.data:
                                id_nad = res.data[0]['id']
                        except Exception:
                            pass
                    
                    if id_nad is None:
                        st.error(f"No se pudo encontrar el ID de '{nadador_seleccionado}'. Recarga la página e intenta de nuevo.")
                    else:
                        try:
                            supabase.table("tiempos").insert({
                                "id_nadador": int(id_nad), 
                                "fecha": fecha.strftime('%Y-%m-%d'),
                                "lugar": lugar, 
                                "estilo": estilo, 
                                "tiempo_formateado": tiempo_input,
                                "segundos_totales": secs,
                                "tipo_piscina": tipo_piscina
                            }).execute()
                            st.success(f"Guardado: {tiempo_input} ({secs}s)")
                        except Exception as e:
                            st.error(f"Error BD: {e}")
                else:
                    st.success("Modo local: Tiempo guardado (simulado).")

    with tab2:
        st.markdown("### 📥 Descargar Plantilla y Cargar Datos")
        st.write("Sigue estos pasos: 1. Baja el modelo, 2. Completa los datos (puedes borrar el ejemplo), 3. Sube el archivo.")
        
        import io
        
        # 1. CREAMOS LA LÍNEA DE EJEMPLO
        # Importante: Los nombres de columnas deben coincidir con tu SQL (tiempo_formateado)
        datos_ejemplo = {
            'id_nadador': [1],           # El ID se encuentra en la pestaña 'Perfiles'
            'fecha': ['2026-04-10'],
            'lugar': ['Piscina Valdivia'],
            'estilo': ['200 IM'],         # Debe ser exacto al ENUM de la BD
            'tipo_piscina': ['Piscina Corta (25m)'],  # o: Piscina Larga (50m)
            'tiempo_formateado': ['03:30,50']  # Formato MM:SS,MS
        }
        
        plantilla_df = pd.DataFrame(datos_ejemplo)
        
        # Preparamos el buffer para la descarga
        csv_buffer = io.StringIO()
        plantilla_df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 Descargar Modelo CSV con Ejemplo", 
            data=csv_buffer.getvalue().encode('utf-8'), 
            file_name="modelo_carga_tiempos.csv", 
            mime="text/csv"
        )
        
        st.markdown("---")
        
        # 2. SECCIÓN DE CARGA
        uploaded_file = st.file_uploader("Sube tu archivo corregido (CSV o Excel)", type=["csv", "xlsx"])
        
        if uploaded_file is not None:
            try:
                # Leer el archivo
                if uploaded_file.name.endswith('.csv'):
                    df_cargado = pd.read_csv(uploaded_file)
                else:
                    df_cargado = pd.read_excel(uploaded_file)
                
                st.write("🔍 Vista previa de los datos a subir:")
                st.dataframe(df_cargado, use_container_width=True)
                
                if st.button("🚀 Confirmar e Insertar en Base de Datos", type="primary"):
                    # MAGIA: Convertimos la columna MM:SS,MS a segundos numéricos
                    # Usamos la función convertir_tiempo_a_segundos que definimos al inicio
                    df_cargado['segundos_totales'] = df_cargado['tiempo_formateado'].apply(convertir_tiempo_a_segundos)
                    
                    supabase = init_connection()
                    if supabase:
                        try:
                            # Convertimos a lista de diccionarios para Supabase
                            recs = df_cargado.to_dict('records')
                            
                            # Insertamos masivamente
                            resultado = supabase.table("tiempos").insert(recs).execute()
                            
                            st.success(f"✅ ¡Éxito! Se han registrado {len(recs)} tiempos correctamente.")
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ Error de Base de Datos: {e}")
                    else:
                        st.info("💡 Modo Prototipo: Los datos se procesaron pero no hay conexión a Supabase.")
            
            except Exception as e:
                st.error(f"❌ Error al procesar el archivo: {e}")
                st.info("Asegúrate de no haber cambiado los nombres de las columnas en el CSV.")

def gestionar_nadadores():
    """Muestra el panel de gestión de perfiles de los nadadores (categorías, grupo, sexo)."""
    st.header("👥 Gestión de Perfiles de Nadadores")
    if st.session_state.user_role not in ['Entrenador', 'Master']:
        st.error("Solamente los entrenadores autorizados pueden modificar los perfiles.")
        return
        
    st.write("Crea nuevos nadadores o edita el grupo, categoría y sexo de los nadadores actuales.")
    
    df = st.session_state.nadadores_df.copy()
    if 'id' in df.columns:
        df = df.drop(columns=['id'])
        
    # Definir categorías oficiales
    cats_oficiales = ['Infantil A', 'Infantil B1', 'Infantil B2', 'Juvenil A1', 'Juvenil A2', 'Juvenil B', 'Mayores']

    edited_df = st.data_editor(
        df, 
        use_container_width=True, 
        num_rows="dynamic",
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
                    # Limpiar valores NaN antes de enviar a Supabase
                    r_clean = {k: v for k, v in r.items() if pd.notna(v)}
                    if pd.notna(id_val):  # Nadador existente → actualizar
                        supabase.table("nadadores").update(r_clean).eq("id", int(id_val)).execute()
                    else:  # Nadador nuevo → insertar
                        supabase.table("nadadores").insert(r_clean).execute()

                # Recargar IDs frescos de Supabase para mantener sesión sincronizada
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
# --- Lógica Principal de la Aplicación ---

# Inicializar st.session_state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = None
    st.session_state.user_info = None
    # Cargar datos una sola vez (desde BD si existe, si no locales)
    nadadores_df, tiempos_df, usuarios_df, marcas_df = cargar_datos()
    st.session_state.nadadores_df = nadadores_df
    st.session_state.tiempos_df = tiempos_df
    st.session_state.usuarios_df = usuarios_df
    st.session_state.marcas_df = marcas_df

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
    if st.session_state.user_role in ['Directiva', 'Master']:
        opciones_menu.append("🗓️ Asistencia")
    if st.session_state.user_role in ['Entrenador', 'Master']:
        opciones_menu.append("👥 Perfiles")
    if st.session_state.user_role in ['Entrenador', 'Master', 'Directiva']:
        opciones_menu.extend(["⏱️ Registrar Tiempos", "⚙️ Configurar Marcas"])
        
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
    elif page == "🛡️ Admin Usuarios":
        panel_master()
