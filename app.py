st.subheader("Análisis de Tiempo - Daño C")

# Filtrar solo Daño C
df_c = df[df["Tipo de Daño"] == "C"].copy()

if df_c.empty:
    st.warning("No hay registros con Daño C")
    st.stop()

# Convertir columna de tiempo a numérica
df_c["Dif (2)"] = pd.to_numeric(df_c["Dif (2)"], errors="coerce")

# ---------------- KPI PRINCIPALES ----------------

col1, col2 = st.columns(2)

col1.metric("Cantidad registros Daño C", len(df_c))
col2.metric("Promedio general horas", round(df_c["Dif (2)"].mean(), 2))

# ---------------- TIEMPO POR ETAPA ----------------

st.subheader("Promedio de Horas por Etapa")

resumen_etapas = (
    df_c
    .groupby("Etapas")["Dif (2)"]
    .mean()
    .reset_index()
    .sort_values(by="Dif (2)", ascending=False)
)

st.dataframe(resumen_etapas)
st.bar_chart(resumen_etapas.set_index("Etapas"))

# ---------------- TIEMPO TOTAL POR PATENTE ----------------

st.subheader("Tiempo Total por Vehículo (Patente)")

resumen_patente = (
    df_c
    .groupby("Patente")["Dif (2)"]
    .sum()
    .reset_index()
    .sort_values(by="Dif (2)", ascending=False)
)

st.dataframe(resumen_patente)
st.bar_chart(resumen_patente.set_index("Patente"))
