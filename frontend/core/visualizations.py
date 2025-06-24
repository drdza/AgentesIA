from typing import List

import pandas as pd
import streamlit as st
import altair as alt

def _suggest_chart_type(df: pd.DataFrame, dimensions: list[str], metrics: list[str]) -> str:
    if len(df) == 1 and len(metrics) <= 4:
        return "KPIs"
    if dimensions and any("fecha" in d.lower() or "mes" in d.lower() or "año" in d.lower() for d in dimensions):
        return "Lineas"
    if len(df) <= 20:
        return "Barras"
    return "DataFrame"

def _prepare_chart_data(raw_df: pd.DataFrame, config: dict = None) -> tuple[pd.DataFrame, list[str], list[str], str]:
    """
    Limpia y transforma el DataFrame para visualización.
    
    Args:
        raw_df (pd.DataFrame): Data cruda devuelta por el modelo.
        config (dict, optional): Parámetros opcionales para forzar formato, filtros, etc.
    
    Returns:
        df_limpio (pd.DataFrame): DataFrame limpio y listo para graficar.
        dimension_cols (list): Columnas categóricas.
        metric_cols (list): Columnas numéricas.
        chart_type (str): Tipo sugerido de visualización.
    """
    df = raw_df.copy()

    # --- Paso 1: Eliminar filas donde todas las métricas sean cero o NaN
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    df = df.loc[~(df[numeric_cols].fillna(0) == 0).all(axis=1)]

    # --- Paso 2: Rellenar vacíos en dimensiones
    text_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    for col in text_cols:
        df[col] = df[col].fillna("NO DEFINIDO").replace("", "NO DEFINIDO")

    # --- Paso 3: Detectar columnas tipo fecha y truncar si es necesario
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        elif any(kw in col.lower() for kw in ["fecha", "date", "mes", "año", "year", "periodo"]):
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
            except Exception:
                pass

    # --- Paso 4: Renombrar columnas a formato legible (title case)
    df.rename(columns=lambda c: c.replace("_", " ").title(), inplace=True)

    # --- Paso 5: Recalcular tipos luego del rename
    metric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    dimension_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

    # --- Paso 6: Ordenar por primera métrica si aplica
    if metric_cols:
        df.sort_values(by=metric_cols[0], ascending=False, inplace=True)

    # --- Paso 7: Sugerir tipo de visualización
    chart_type = _suggest_chart_type(df, dimension_cols, metric_cols)

    return df, dimension_cols, metric_cols, chart_type

def _render_dataframe(df: pd.DataFrame, placeholder: st.delta_generator.DeltaGenerator) -> None:
    """
    Renderiza el DataFrame con estilos básicos para fechas, porcentajes y numéricos.
    No modifica el DataFrame recibido.
    """
    styled = df.style

    for col in df.columns:
        col_lower = col.lower()

        if "fecha" in col_lower or "mes" in col_lower:
            styled = styled.format({col: lambda x: x.strftime("%Y-%m-%d") if pd.notnull(x) else ""})

        elif "%" in col_lower or "porcentaje" in col_lower:
            styled = styled.format({col: "{:.2%}"})

        elif any(kw in col_lower for kw in ["monto", "total", "importe", "precio"]):
            styled = styled.format({col: "${:,.2f}"})

        elif "count" in col_lower:
            styled = styled.format({col: "{:,}"})

        if pd.api.types.is_numeric_dtype(df[col]):
            styled = styled.background_gradient(cmap="Blues", subset=[col])

    placeholder.dataframe(styled, hide_index=True, use_container_width=True)

def _render_kpis(df: pd.DataFrame, placeholder: st.delta_generator.DeltaGenerator, metrics: list[str]) -> None:
    """
    Renderiza un bloque de métricas tipo KPI usando st.metric().
    Solo aplica si el DataFrame tiene una sola fila.
    """
    if df.shape[0] != 1 or not metrics:
        placeholder.warning("Los KPIs solo se muestran cuando hay una única fila con métricas.")
        return

    values = df.iloc[0][metrics].round(2)
    cols = st.columns(len(metrics))

    for i, col in enumerate(metrics):
        val = values[col]
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
    Renderiza un gráfico de barras usando Altair.
    Soporta una dimensión y múltiples métricas agrupadas.
    """
    if not dimensions or not metrics:
        placeholder.warning("Se requieren al menos una dimensión y una métrica para graficar barras.")
        return

    dim = dimensions[0]
    df_plot = df[[dim] + metrics].copy()

    # Altair requiere formato largo si hay más de una métrica
    if len(metrics) == 1:
        chart = (
            alt.Chart(df_plot)
            .mark_bar()
            .encode(
                x=alt.X(f"{dim}:N", sort=df_plot[dim].tolist(), title=dim),
                y=alt.Y(f"{metrics[0]}:Q", title=metrics[0]),
                tooltip=[dim] + metrics
            )
            .properties(height=400)
        )
    else:
        df_melted = df_plot.melt(id_vars=[dim], value_vars=metrics, var_name="Métrica", value_name="Valor")
        chart = (
            alt.Chart(df_melted)
            .mark_bar()
            .encode(
                x=alt.X(f"{dim}:N", sort=df_plot[dim].tolist(), title=dim),
                y=alt.Y("Valor:Q", title="Valor"),
                color="Métrica:N",
                tooltip=[dim, "Métrica", "Valor"]
            )
            .properties(height=400)
        )

    placeholder.altair_chart(chart, use_container_width=True)

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
    """
    Función principal que enruta la visualización según el tipo de gráfico requerido.

    Args:
        df (pd.DataFrame): Datos ya transformados y listos para graficar.
        placeholder: Elemento de Streamlit donde se renderiza el gráfico.
        chart_type (str): Uno de ["DataFrame", "Barras", "Lineas", "KPIs"].
        dimensions (List[str]): Columnas categóricas.
        metrics (List[str]): Columnas numéricas.
    """
    if df.empty:
        placeholder.warning("No hay datos disponibles para graficar.")
        return

    if chart_type == "DataFrame":
        _render_dataframe(df, placeholder)
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
    st.markdown("Aquí los resultados a tu pregunta.")
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
    st.markdown("##### El agente generó una consulta, pero falló al ejecutarla.")

    error_msg = data.get("result", {}).get("error", "Error desconocido.")
    st.error(f"😭 {error_msg}")
