from typing import List
from math import ceil
import os
import sys
import pandas as pd
import streamlit as st
import altair as alt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import  load_css_style




def _convert_numeric_column(col: pd.Series) -> pd.Series:
    """Convierte floats a enteros si no hay decimales. Redondea a 2 si los hay."""
    if pd.api.types.is_float_dtype(col):
        col_non_null = col.dropna()
        if (col_non_null % 1 == 0).all():
            return col.astype("Int64")  # permite NaNs como enteros
        else:
            return col.round(2)
    return col

def _suggest_chart_type(df: pd.DataFrame, dimensions: list[str], metrics: list[str]) -> str:       
    if len(df) == 1 and len(metrics) <= 4:
        return "KPIs"
    if dimensions and any("fecha" in d.lower() or "mes" in d.lower() or "año" in d.lower() for d in dimensions):
        return "Lineas"
    if len(df) <= 20:
        return "Barras"
    return "DataFrame"

def _rename_columns_flexibly(df: pd.DataFrame) -> pd.DataFrame:
    try:        
        df.rename(columns=lambda c: c.replace("_", " ").title(), inplace=True)
        rename_rules = {
            "anio": "año",
            "count": "conteo",
            "mes numero": "mes",
            "porcentaje": "(%)",
            "estatus ticket": "estatus"
        }

        new_columns = []
        for col in df.columns:
            col_lower = col.lower()
            new_col = col  # valor por defecto

            for pattern, replacement in rename_rules.items():
                if pattern in col_lower:
                    new_col = col_lower.replace(pattern, replacement).title()
                    break

            new_columns.append(new_col)

        df.columns = new_columns
        
        return df
    except Exception as e:
        return df
    
def _prepare_chart_data(raw_df: pd.DataFrame, config: dict = None) -> tuple[pd.DataFrame, list[str], list[str], str]:    
    df = raw_df.copy()
    df = _rename_columns_flexibly(df)    

    try:
        # Primer detección de Métricas y Dimensiones
        metric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        dimension_cols = df.select_dtypes(exclude=["number"]).columns.tolist()
        
        # Forzar dimensiones con semantida de fecha (pueden ser númericas)
        forced_dimensions = ["año", "mes", "anio", "month", "year", "folio"]
        for col in metric_cols[:]:
            if any(kw in col.lower() for kw in forced_dimensions):
                metric_cols.remove(col)
                dimension_cols.append(col)

        # Limpieza de datos en Dimensiones
        df = df.loc[~(df[metric_cols].fillna(0) == 0).all(axis=1)]
        for col in dimension_cols:
            df[col] = df[col].fillna("NO DEFINIDO").replace("", "NO DEFINIDO")                        

        # Detección de fechas y casteo a datetime
        for col in dimension_cols:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
            elif any(kw in col.lower() for kw in forced_dimensions):
                df[col] = df[col].astype(int)
            elif any(kw in col.lower() for kw in ["fecha", "periodo"]):
                try:
                    df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
                except Exception:
                    pass

        # Eliminación de COLUMNAS de tipo Dimensión que estén vacías, nulas o ceros
        df = df.drop(columns=[
            col for col in dimension_cols
            if df[col].apply(lambda x: pd.isna(x) or x == 0 or (isinstance(x, str) and x.strip() == "")).all()
        ])
        
        # Definición final de dimensiones
        dimension_cols = [col for col in dimension_cols if col in df.columns]
        #metric_cols = [col for col in metric_cols if col in df.columns]

        for col in metric_cols:
            df[col] = _convert_numeric_column(df[col])

        # Ordenamiento por la primera métrica
        if metric_cols:
            df.sort_values(by=metric_cols[0], ascending=False, inplace=True)

        # Sugerencia del tipo de gráfico
        chart_type = _suggest_chart_type(df, dimension_cols, metric_cols)

        return df, dimension_cols, metric_cols, chart_type
    except Exception as e:                     
        return raw_df.copy(), [], [], "DataFrame"

def _render_dataframe(df: pd.DataFrame, placeholder: st.delta_generator.DeltaGenerator,
                      dimensions: List[str], metrics: List[str]) -> None:
    styled = df.style
    format_dict = {}    

    try:
        for col in metrics:
            col_lower = col.lower()            
            if "%" in col_lower or "porcentaje" in col_lower:
                format_dict[col] = lambda x: f"{int(x)/100:.2%}" 

            elif any(kw in col_lower for kw in ["folio", "ticket", "tiempo"]):
                format_dict[col] = lambda x: f"{int(x):,}" if pd.notnull(x) else ""            

            elif "fecha" in col_lower:
                format_dict[col] = lambda x: x.strftime("%Y-%m-%d") if pd.notnull(x) else ""                       

            elif "count" in col_lower:
                format_dict[col] = "{:,}"            

            if pd.api.types.is_numeric_dtype(df[col]):
                styled = styled.background_gradient(cmap="Blues", subset=[col])
    except Exception as e:
        print(f"Error: {e}")

    styled = styled.format(format_dict)
    placeholder.dataframe(styled, hide_index=True, use_container_width=True)

def _render_kpis(df: pd.DataFrame, placeholder: st.delta_generator.DeltaGenerator, metrics: list[str]) -> None:
    """
    Renderiza un bloque de métricas tipo KPI usando st.metric().
    Solo aplica si el DataFrame tiene una sola fila.
    """
    if df.shape[0] != 1 or not metrics:
        placeholder.warning("Los KPIs solo se muestran cuando hay una única fila con métricas.")
        return
        
    values = df.iloc[0][metrics]
    cols = st.columns(len(metrics))    
    
    for i, col in enumerate(metrics):
        col_lower = col.lower()
        val = None
        if "%" in col_lower or "porcentaje" in col_lower:
            val = f"{int(values[col])/100:.2%}"
        elif any(kw in col_lower for kw in ["folio", "tiempo"]):
            val = f"{int(values[col]):,}"
        else:
            val = f"{values[col]:,}"        

        delta = None

        # Buscar columnas tipo "col_anterior" para mostrar variación
        posibles = [c for c in df.columns if col in c and "anterior" in c.lower()]
        if posibles:
            delta_val = df.iloc[0][posibles[0]]
            if pd.notnull(delta_val):
                delta = round(val - delta_val, 2)

        with cols[i]:
            st.metric(label=col, value=val, delta=delta)

def _render_bar_chart(df: pd.DataFrame, placeholder: st.delta_generator.DeltaGenerator,
                      dimensions: List[str], metrics: List[str]) -> None:
    """
    Renderiza gráficos de barras en varias columnas, según la cantidad de dimensiones.
    """
    if not dimensions or not metrics:
        placeholder.warning("Se requieren al menos una dimensión y una métrica para graficar barras.")
        return
    
    # if len(dimensions) > 5:
    #     placeholder.warning("Se excede la cantidad de dimensiones")
    #     return

    columns_per_row = 3

    rows = [
        dimensions[i:i + columns_per_row]
        for i in range(0, len(dimensions), columns_per_row)
    ]

    for dim_group in rows:
        cols = st.columns(len(dim_group))

        for dim, col in zip(dim_group, cols):
            with col.container(height=380):  # Puedes ajustar altura
                df_plot = df[[dim] + metrics].copy()

                if len(metrics) == 1:
                    chart = (
                        alt.Chart(df_plot)
                        .mark_bar()
                        .encode(
                            x=alt.X(f"{dim}:N", sort=df_plot[dim].tolist(), title=dim),
                            y=alt.Y(f"{metrics[0]}:Q", title=metrics[0]),
                            tooltip=[dim] + metrics
                        )
                        .properties(height=300)
                    )
                else:
                    df_melted = df_plot.melt(
                        id_vars=[dim],
                        value_vars=metrics,
                        var_name="Métrica",
                        value_name="Valor"
                    )

                    chart = (
                        alt.Chart(df_melted)
                        .mark_bar()
                        .encode(
                            x=alt.X(f"{dim}:N", sort=df_plot[dim].tolist(), title=dim),
                            y=alt.Y("Valor:Q", title="Valor"),
                            color="Métrica:N",
                            tooltip=[dim, "Métrica", "Valor"]
                        )
                        .properties(height=300)
                    )

                st.markdown(f"**📊 {dim}**")
                st.altair_chart(chart, use_container_width=False)

def _render_line_chart(df: pd.DataFrame, placeholder: st.delta_generator.DeltaGenerator,
                       dimensions: List[str], metrics: List[str]) -> None:
    """
    Renderiza un gráfico de líneas usando Altair.
    Solo se utiliza la primera dimensión como eje X.
    """
    if not dimensions or not metrics:
        placeholder.warning("Se requieren al menos una dimensión y una métrica para graficar líneas.")
        return

    dim = dimensions[0]
    df_plot = df[[dim] + metrics].copy()

    # Preparar el DataFrame para Altair
    if len(metrics) == 1:
        chart = (
            alt.Chart(df_plot)
            .mark_line(point=True)
            .encode(
                x=alt.X(f"{dim}:O", sort="ascending", title=dim),
                y=alt.Y(f"{metrics[0]}:Q", title=metrics[0]),
                tooltip=[dim] + metrics
            )
            .properties(height=400)
        )
    else:
        df_melted = df_plot.melt(id_vars=[dim], value_vars=metrics, var_name="Métrica", value_name="Valor")
        chart = (
            alt.Chart(df_melted)
            .mark_line(point=True)
            .encode(
                x=alt.X(f"{dim}:O", sort="ascending", title=dim),
                y=alt.Y("Valor:Q", title="Valor"),
                color="Métrica:N",
                tooltip=[dim, "Métrica", "Valor"]
            )
            .properties(height=400)
        )

    placeholder.altair_chart(chart, use_container_width=True)

def _render_chart(
    df: pd.DataFrame,
    placeholder: st.delta_generator.DeltaGenerator,
    chart_type: str,
    dimensions: List[str],
    metrics: List[str]
):
    if df.empty:
        placeholder.warning("No hay datos disponibles para graficar.")
        return

    if chart_type == "DataFrame":
        _render_dataframe(df, placeholder, dimensions, metrics)
    elif chart_type == "Barras":
        _render_bar_chart(df, placeholder, dimensions, metrics)
    elif chart_type == "Lineas":
        _render_line_chart(df, placeholder, dimensions, metrics)
    elif chart_type == "KPIs":
        _render_kpis(df, placeholder, metrics)
    else:
        placeholder.warning("Tipo de gráfico no soportado.")

def _render_agent_details(data: dict) -> None:
    """Muestra detalles del agente como reformulación, SQL y contexto."""
    if data.get("reformulation"):
        with st.expander("🔁 Reformulación", expanded=False):
            st.info(data["reformulation"])

    if data.get("sql"):
        with st.expander("🧠 SQL generado", expanded=False):
            st.code(data["sql"], language="sql")

    if data.get("context"):
        with st.expander("📚 Contexto útil", expanded=False):
            st.code(data["context"])

def render_visual_response(data: dict, index: int) -> None:
    """Muestra la visualización de resultados si el SQL se ejecutó correctamente."""
    st.markdown(f"Esto fue lo que encontré relacionado a tu pregunta - ( {data['duration']:.2f} seg. )")
    df_raw = pd.DataFrame(data["result"]["rows"], columns=data["result"]["columns"])

    df, dimensions, metrics, chart_type = _prepare_chart_data(df_raw)

    chart_options = ["DataFrame", "Barras", "Lineas", "KPIs"]
    
    with st.container(border=True):
        selected_chart = st.radio(
            "🔍 Cómo deseas visualizar los datos:",
            chart_options,
            index=chart_options.index(chart_type),
            key=f"viz_selector_{index}",
            horizontal=True
        )

        data["viz_type"] = selected_chart

    with st.container(border=True):
        st.markdown("##### 📊 Resultados")
        placeholder = st.empty()
        _render_chart(df, placeholder, selected_chart, dimensions, metrics)    

def render_error_with_agent_context(data: dict, index: int) -> None:
    """Muestra el SQL y la reformulación del agente aunque el resultado haya fallado."""
    st.markdown("Lo siento, algo falló al intentar responderte.")

    error_msg = data.get("result", {}).get("error", "Error desconocido.")
    st.error(f"😭 {error_msg}")

def render_out_domain_agent(data: dict, index: int) -> None:
    st.markdown(load_css_style("out_domain.css"), unsafe_allow_html=True)    
    dic_msg = data.get("result", {}).get("out_domain", "Error desconocido.")

    st.markdown( f"{dic_msg['mensaje']}") 
    
    st.markdown(f"""  
                <div class='out-domain-intention '>                
                  
                🧠 He detectado esta intención en tu pregunta: **{dic_msg['motivo']}**

                </div>
        """, unsafe_allow_html=True)
    
    st.divider()

    st.markdown("""
                <div class='out-domain-help'>                 
                También puedes revisar nuestra guía de ayuda <a href='/help#guia-rapida-de-uso'> aquí </a>.
                </div>
        """, unsafe_allow_html=True)