############################################################
# PROYECTO: Datatón Dat4cción – ONU Mujeres / Fundar
# TEMA: Condiciones laborales de mujeres jornaleras agrícolas
# FUENTE DE DATOS: ENOE 2025, Trimestre 3 (INEGI)
#
# DESCRIPCIÓN GENERAL:
# Este script construye indicadores laborales descriptivos
# y un índice sintético de precariedad laboral para mujeres
# jornaleras agrícolas en México, incorporando:
#   - Diseño muestral complejo de la ENOE
#   - Estimaciones oficiales (media / mediana según variable)
#   - Criterios explícitos de confiabilidad estadística
#
# USO PREVISTO:
# Producción de insumos para visualización, análisis comparativo
# y comunicación pública en el marco del Datatón Dat4cción.
#
# AUTORÍA: Fundar, Centro de Análisis e Investigación
# RESPONSABLE TÉCNICA: Miriam Rangel
# FECHA: 10 de abril de 2026
############################################################

# ----------------------------------------------------------
# 1) LIBRERÍAS Y OPCIONES GLOBALES
# ----------------------------------------------------------

# Ajuste recomendado para dominios pequeños en encuestas complejas
options(survey.lonely.psu = "adjust")

library(renoe)     # Descarga y fusión ENOE
library(tidyverse) # Manipulación de datos
library(survey)    # Análisis con diseño muestral

# ----------------------------------------------------------
# 2) CARGA DE DATOS: ENOE 2025-T3
# ----------------------------------------------------------
# Se utiliza la ENOE completa (no modo rápido) para asegurar
# cobertura nacional por entidad federativa.


enoe_2025_t3 <- fusion_enoe(
  anio = 2025, #sustituir por 2023 y 2024 para años anteriores
  trimestre = 3,
  rapida = FALSE   # ← CLAVE
)

# ----------------------------------------------------------
# 3) UNIVERSO ANALÍTICO Y VARIABLES DERIVADAS
# ----------------------------------------------------------
# Se define el universo analítico de personas ocupadas
# y se construyen variables derivadas para identificar:
# - Sexo
# - Sector agropecuario
# - Condición de subordinación
# - Grupos específicos de jornalería agrícola
#
# Estas variables alimentan tanto los indicadores descriptivos
# como el índice sintético de precariedad laboral.



enoe_analitica <- enoe_2025_t3 %>%
  mutate(
    # Sexo
    mujer  = sex == 2,
    hombre = sex == 1,

    # Sector
    agricola = rama == 6,

    # Posición en la ocupación
    subordinada = pos_ocu == 1,

    # Grupos jornaleros
    mujer_jornalera  = mujer  & agricola & subordinada,
    hombre_jornalero = hombre & agricola & subordinada,

    # Grupos amplios
    grupo_amplio = case_when(
      mujer  & agricola  ~ "Mujeres agropecuarias",
      hombre & agricola  ~ "Hombres agropecuarios",
      mujer  & !agricola ~ "Mujeres no agropecuarias",
      hombre & !agricola ~ "Hombres no agropecuarios"
    ),

    # Variables laborales
    ingreso      = as.numeric(ingocup),
    horas_sem    = hrsocup,
    sobrejornada = if_else(hrsocup > 48, 1, 0),
    sin_ss       = if_else(imssissste != 1, 1, 0),

    # Auxiliar
    one = 1
  ) %>%
  select(
    upm, est_d_tri, fac_tri,    
    cve_ent, # En 2023 y 2024 se llama ent, en 2025 se llama cve_ent
    est, 
    sex, mujer, hombre,
    agricola, subordinada,
    mujer_jornalera, hombre_jornalero,
    grupo_amplio,
    ingreso, horas_sem, sobrejornada, sin_ss,
    one
  )


# ----------------------------------------------------------
# 4) ÍNDICE DE PRECARIEDAD LABORAL
# ----------------------------------------------------------
# El índice se construye como un promedio simple de tres
# dimensiones binarias de precariedad laboral.
#
# El índice toma valores en el rango [0,1] y puede
# interpretarse como la proporción de desventajas laborales
# presentes en cada persona ocupada.

# Salario mínimo general diario vigente en 2025 (pesos)
# Fuente: CONASAMI, Zona general
#2025
salario_min_diario <- 278.80
#2024
# salario_min_diario <- 248.93
#2023
# salario_min_diario <- 207.44

enoe_analitica <- enoe_analitica %>%
  mutate(
    ingreso_diario = ingreso / 30,

    d_ingreso_bajo = if_else(ingreso_diario < salario_min_diario, 1, 0),
    d_sobrejornada = sobrejornada,
    d_sin_ss = sin_ss,

    indice_precariedad = (
      d_ingreso_bajo +
      d_sobrejornada +
      d_sin_ss
    ) / 3
  )


# ----------------------------------------------------------
# 5) Categorización del índice de precariedad laboral
#     (baja / media / alta)
# ----------------------------------------------------------

# Interpretación basada en número de desventajas:
# 0–1 desventajas  -> Baja precariedad
# 2 desventajas    -> Precariedad media
# 3 desventajas  -> Alta precariedad

enoe_analitica <- enoe_analitica %>%
  mutate(
    precariedad_categoria = case_when(
      indice_precariedad < 0.25                    ~ "Baja",
      indice_precariedad >= 0.25 & indice_precariedad < 0.50 ~ "Media",
      indice_precariedad >= 0.50                   ~ "Alta",
      TRUE                                         ~ NA_character_
    )
  )

# ----------------------------------------------------------
# 6) Diseño muestral
# ----------------------------------------------------------

design_enoe <- svydesign(
  id      = ~upm,
  strata  = ~est_d_tri,
  weights = ~fac_tri,
  data    = enoe_analitica,
  nest    = TRUE
)

# ----------------------------------------------------------
# 6.1) Validaciones básicas
# ----------------------------------------------------------

table(enoe_analitica$mujer_jornalera)
table(enoe_analitica$hombre_jornalero)

svytotal(~mujer_jornalera, design_enoe)
svytotal(~hombre_jornalero, design_enoe)

svytotal(~(agricola & subordinada), design_enoe)

# ----------------------------------------------------------
# 8) Indicadores nacionales de jornalería agrícola
#    (Ingreso = mediana oficial; Horas = media oficial)
# ----------------------------------------------------------
# 8.1) Subdiseños poblacionales
design_mujer_jornalera  <- subset(design_enoe, mujer_jornalera)
design_hombre_jornalero <- subset(design_enoe, hombre_jornalero)

# 8.2) Función de cálculo de indicadores
indicadores_nacionales <- function(design, grupo_nombre) {

# 8.3) Estimaciones nacionales
  # --- INGRESO ---
  ingreso_media <- svymean(~ingreso, design, na.rm = TRUE)
  ingreso_media_ci <- confint(ingreso_media)

  ingreso_mediana <- svyquantile(
    ~ingreso,
    design,
    quantiles = 0.5,
    ci = TRUE,
    na.rm = TRUE
  )
  ingreso_mediana_ci <- confint(ingreso_mediana)

  # --- HORAS ---
  horas_media <- svymean(~horas_sem, design, na.rm = TRUE)
  horas_media_ci <- confint(horas_media)

  horas_mediana <- svyquantile(
    ~horas_sem,
    design,
    quantiles = 0.5,
    ci = TRUE,
    na.rm = TRUE
  )
  horas_mediana_ci <- confint(horas_mediana)

  # --- PROPORCIONES ---
  sobre_mean <- svymean(~sobrejornada, design, na.rm = TRUE)
  sinss_mean <- svymean(~sin_ss, design, na.rm = TRUE)

  tibble(
    grupo = grupo_nombre,

    # Ingreso (oficial = mediana)
    ingreso_mediana    = as.numeric(coef(ingreso_mediana)),
    ingreso_mediana_li = ingreso_mediana_ci[1],
    ingreso_mediana_ls = ingreso_mediana_ci[2],

    # Ingreso (analítico)
    ingreso_media      = as.numeric(ingreso_media),
    ingreso_media_li   = ingreso_media_ci[1],
    ingreso_media_ls   = ingreso_media_ci[2],

    # Horas (oficial = media)
    horas_media        = as.numeric(horas_media),
    horas_media_li     = horas_media_ci[1],
    horas_media_ls     = horas_media_ci[2],

    # Horas (analítico)
    horas_mediana      = as.numeric(coef(horas_mediana)),
    horas_mediana_li   = horas_mediana_ci[1],
    horas_mediana_ls   = horas_mediana_ci[2],

    # Proporciones
    prop_sobrejornada  = as.numeric(sobre_mean),
    prop_sin_ss        = as.numeric(sinss_mean)
  )
}

indic_mujeres <- indicadores_nacionales(
  design_mujer_jornalera,
  "Mujeres jornaleras agrícolas"
)

indic_hombres <- indicadores_nacionales(
  design_hombre_jornalero,
  "Hombres jornaleros agrícolas"
)
# 8.4) Población objetivo
# Población
pob_mujeres <- svytotal(~mujer_jornalera, design_enoe) %>%
  as.data.frame() %>%
  slice(2) %>%
  transmute(
    grupo = "Mujeres jornaleras agrícolas",
    poblacion = total
  )

pob_hombres <- svytotal(~hombre_jornalero, design_enoe) %>%
  as.data.frame() %>%
  slice(2) %>%
  transmute(
    grupo = "Hombres jornaleros agrícolas",
    poblacion = total
  )

# 8.5) Tabla nacional consolidada
tabla_nacional <- bind_rows(indic_mujeres, indic_hombres) %>%
  left_join(bind_rows(pob_mujeres, pob_hombres), by = "grupo")

# ----------------------------------------------------------
# 9) COMPOSICIÓN INTERSECCIONAL DEL SECTOR AGROPECUARIO
#    Sexo × Condición de jornalería (para visualización)
# ----------------------------------------------------------

# 9.1) Construcción de variable analítica
# Variable analítica solo para composición visual dentro del agro
enoe_analitica <- enoe_analitica %>%
  mutate(
    grupo_agro_sexo_jornal = case_when(
      mujer  & agricola & subordinada  ~ "Mujeres jornaleras",
      mujer  & agricola & !subordinada ~ "Mujeres no jornaleras",
      hombre & agricola & subordinada  ~ "Hombres jornaleros",
      hombre & agricola & !subordinada ~ "Hombres no jornaleros",
      TRUE ~ NA_character_
    )
  )

# ----------------------------------------------------------
# IMPORTANTE:
# Se recrea el diseño muestral para que incorpore la nueva
# variable grupo_agro_sexo_jornal
# ----------------------------------------------------------
# 9.2) Actualización del diseño muestral
design_enoe <- svydesign(
  id      = ~upm,
  strata  = ~est_d_tri,
  weights = ~fac_tri,
  data    = enoe_analitica,
  nest    = TRUE
)

# Subdiseño: solo población agropecuaria
design_agro <- subset(design_enoe, agricola)

# Población por grupo interseccional dentro del agro
pob_agro_grupos_raw <- svyby(
  ~one,
  ~grupo_agro_sexo_jornal,
  design_agro,
  svytotal,
  na.rm = TRUE,
  keep.var = FALSE,
  drop.empty.groups = TRUE
)
# 9.3) Estimaciones de composición poblacional
# Estandarizar nombre de columna (evita errores de rename)
pob_agro_grupos <- pob_agro_grupos_raw %>%
  as_tibble() %>%
  rename(
    poblacion = !!names(pob_agro_grupos_raw)[2]
  )

# Total agropecuario (para normalizar)
total_agro <- sum(pob_agro_grupos$poblacion, na.rm = TRUE)

# Tabla final de composición (lista para barra apilada / mosaico)
tabla_agro_composicion <- pob_agro_grupos %>%
  mutate(
    porcentaje = poblacion / total_agro
  )  
# ----------------------------------------------------------
# 10) INDICADORES ESTATALES: Mujeres jornaleras agrícolas
# ----------------------------------------------------------

# 10.1) Estimaciones estatales básicas

# Subdiseño mujeres jornaleras agrícolas
design_mujer_jornalera <- subset(design_enoe, mujer_jornalera)

# --- INGRESO: mediana (oficial) ---
ingreso_med_est_raw <- svyby(
  ~ingreso,
  ~cve_ent,
  design_mujer_jornalera,
  svyquantile,
  quantiles = 0.5,
  ci = TRUE,
  na.rm = TRUE,
  keep.var = FALSE,
  drop.empty.groups = TRUE
)

# Convertir a data.frame
ingreso_df <- as.data.frame(ingreso_med_est_raw)

# Columnas devueltas por svyby():
# 1 = cve_ent
# 2 = estimador del cuantil
# 3 = ci_l
# 4 = ci_u
ingreso_med_est <- tibble(
  cve_ent = ingreso_df[[1]],
  ingreso_mediana    = ingreso_df[[2]],
  ingreso_mediana_li = ingreso_df$ci_l,
  ingreso_mediana_ls = ingreso_df$ci_u
)

# --- HORAS: media (oficial) ---
horas_mean_est_raw <- svyby(
  ~horas_sem,
  ~cve_ent,
  design_mujer_jornalera,
  svymean,
  na.rm = TRUE,
  keep.var = FALSE,
  drop.empty.groups = TRUE
)

# Estandarizar salida de forma robusta
horas_df <- as.data.frame(horas_mean_est_raw)

horas_mean_est <- tibble(
  cve_ent = horas_df[[1]],
  horas_media = horas_df[[2]]
)

# --- PROPORCIÓN CON SOBREJORNADA ---
sobrejornada_est_raw <- svyby(
  ~sobrejornada,
  ~cve_ent,
  design_mujer_jornalera,
  svymean,
  na.rm = TRUE,
  keep.var = FALSE,
  drop.empty.groups = TRUE
)

# Estandarizar salida de forma robusta
sobrejornada_df <- as.data.frame(sobrejornada_est_raw)


# 10.2) Población por entidad federativa
sobrejornada_est <- tibble(
  cve_ent = sobrejornada_df[[1]],
  prop_sobrejornada = sobrejornada_df[[2]]
)


# 10.3) Índice de precariedad y categoría dominante
# --- ÍNDICE DE PRECARIEDAD ---
precariedad_est <- svyby(
  ~indice_precariedad,
  ~cve_ent,
  design_mujer_jornalera,
  svymean,
  na.rm = TRUE,
  keep.var = TRUE,
  drop.empty.groups = TRUE
) %>%
  rename(indice_precariedad = indice_precariedad)

# Categoría dominante de precariedad (para visualización)
precariedad_cat_est <- enoe_analitica %>%
  filter(mujer_jornalera) %>%
  count(cve_ent, precariedad_categoria, wt = fac_tri, name = "poblacion") %>%
  group_by(cve_ent) %>%
  slice_max(poblacion, n = 1) %>%
  ungroup() %>%
  select(cve_ent, precariedad_categoria)

# --- POBLACIÓN (sin varianza) ---
pob_est_raw <- svyby(
  ~one,
  ~cve_ent,
  design_mujer_jornalera,
  svytotal,
  na.rm = TRUE,
  keep.var = FALSE,
  drop.empty.groups = TRUE
)

# Estandarizar salida de forma robusta
pob_df <- as.data.frame(pob_est_raw)

pob_est <- tibble(
  cve_ent = pob_df[[1]],
  poblacion = pob_df[[2]]
)

# --- PROPORCIÓN SIN SEGURIDAD SOCIAL ---
sin_ss_est_raw <- svyby(
  ~sin_ss,
  ~cve_ent,
  design_mujer_jornalera,
  svymean,
  na.rm = TRUE,
  keep.var = FALSE,
  drop.empty.groups = TRUE
)

sin_ss_df <- as.data.frame(sin_ss_est_raw)

sin_ss_est <- tibble(
  cve_ent = sin_ss_df[[1]],
  prop_sin_ss = sin_ss_df[[2]]
)

# --- TABLA ESTATAL BASE ---
tabla_jornaleras_estatal <- ingreso_med_est %>%
  left_join(horas_mean_est,        by = "cve_ent") %>%
  left_join(sobrejornada_est,      by = "cve_ent") %>%
  left_join(sin_ss_est,            by = "cve_ent") %>%
  left_join(precariedad_est,       by = "cve_ent") %>%
  left_join(precariedad_cat_est,   by = "cve_ent") %>%
  left_join(pob_est,               by = "cve_ent")


# ----------------------------------------------------------
# 11) CRITERIO DE CONFIABILIDAD ESTADÍSTICA
# ----------------------------------------------------------
# Una estimación estatal se considera confiable si:
# - Población >= 500 personas
# - Coeficiente de variación (CV) <= 30 %
#
# En dominios donde no es posible estimar varianza,
# las estimaciones se clasifican como no confiables


# --- 11.1 Población con coeficiente de variación (CV) ---

pob_est_cv_raw <- svyby(
  ~one,
  ~cve_ent,
  design_mujer_jornalera,
  svytotal,
  na.rm = TRUE,
  keep.var = TRUE,
  drop.empty.groups = TRUE
)

pob_df  <- as.data.frame(pob_est_cv_raw)
var_pob <- attr(pob_est_cv_raw, "var")

if (is.null(var_pob) || length(var_pob) == 0) {

  pob_est_cv <- tibble(
    cve_ent      = pob_df[[1]],
    poblacion    = pob_df[[2]],
    cv_poblacion = NA_real_
  )

} else {

  se_vals <- sqrt(diag(var_pob))

  pob_est_cv <- tibble(
    cve_ent      = pob_df[[1]],
    poblacion    = pob_df[[2]],
    cv_poblacion = if_else(
      pob_df[[2]] > 0,
      se_vals / pob_df[[2]],
      NA_real_
    )
  )
}

# --- 11.2 Unir población y CV a la tabla estatal ---

tabla_jornaleras_estatal <- tabla_jornaleras_estatal %>%
  select(-matches("^poblacion"), -matches("^cv_poblacion")) %>%
  left_join(pob_est_cv, by = "cve_ent")

# --- 11.3 Definir confiabilidad estadística final ---

tabla_jornaleras_estatal <- tabla_jornaleras_estatal %>%
  mutate(
    confiable = poblacion >= 500 &
                !is.na(cv_poblacion) &
                cv_poblacion <= 0.30,

    categoria_precision = case_when(
      poblacion < 500           ~ "Baja cobertura poblacional",
      is.na(cv_poblacion)       ~ "Varianza no estimable",
      cv_poblacion > 0.30       ~ "Alta imprecisión estadística",
      TRUE                      ~ "Precisión aceptable"
    )
  )

# Nota:
# El criterio de confiabilidad combina tamaño poblacional y CV.
# En poblaciones pequeñas, es esperable que ninguna entidad
# alcance el umbral de confiabilidad, lo cual se refleja en la tabla.

# ----------------------------------------------------------
# 12) CHEQUEO DE CONSISTENCIA DEL ÍNDICE DE PRECARIEDAD
#    (diagnóstico metodológico interno)
# ----------------------------------------------------------
# NOTA IMPORTANTE:
# Este bloque NO forma parte del pipeline de producción.
# Se ejecuta únicamente para validar que los patrones del
# índice de precariedad no estén dominados por estados con
# baja confiabilidad estadística.
# Sus resultados se revisan manualmente y NO se exportan.

# Esta sección cumple exclusivamente una función de control
# metodológico interno y no forma parte del flujo productivo
# ni de los insumos entregables del proyecto.

# ----------------------------------------------------------
# 12.1 Promedio y mediana del índice
#     Estados confiables vs no confiables
# ----------------------------------------------------------

consistencia_promedio <- tabla_jornaleras_estatal %>%
  group_by(confiable) %>%
  summarise(
    promedio_precariedad = mean(indice_precariedad, na.rm = TRUE),
    mediana_precariedad  = median(indice_precariedad, na.rm = TRUE),
    n_estados            = n(),
    .groups = "drop"
  )

print(consistencia_promedio)

# ----------------------------------------------------------
# 12.2 Distribución de categorías de precariedad
# ----------------------------------------------------------

consistencia_categorias <- tabla_jornaleras_estatal %>%
  group_by(confiable, precariedad_categoria) %>%
  summarise(
    n_estados = n(),
    .groups = "drop"
  ) %>%
  group_by(confiable) %>%
  mutate(
    porcentaje = n_estados / sum(n_estados)
  )

print(consistencia_categorias)

# ----------------------------------------------------------
# 12.3 Estados con mayor índice de precariedad
#     (casos extremos, uso orientativo)
# ----------------------------------------------------------

extremos_precariedad <- tabla_jornaleras_estatal %>%
  ungroup() %>%
  arrange(desc(indice_precariedad)) %>%
  slice_head(n = 10) %>%
  select(
    cve_ent,
    indice_precariedad,
    precariedad_categoria,
    confiable,
    poblacion,
    cv_poblacion
  )

print(extremos_precariedad)

# ----------------------------------------------------------
# Interpretación:
# - Si los promedios y categorías son similares entre estados
#   confiables y no confiables, el índice es estructuralmente robusto.
# - Si los valores extremos se concentran en estados no confiables,
#   se justifica la advertencia visual en el dashboard.
# ----------------------------------------------------------

# ----------------------------------------------------------
# 13) EXPORTACIÓN DE TABLAS PARA PRODUCCIÓN
# ----------------------------------------------------------
# NOTA:
# Solo se exportan tablas de PRODUCCIÓN.
# Los objetos de diagnóstico metodológico (sección 12)
# no se exportan ni se integran al dashboard.

# --- Tabla nacional: jornalería agrícola ---
write_csv(
  tabla_nacional,
  "tabla_nacional_jornaleria_agricola_2025t3.csv"
)

# --- Composición interseccional del sector agropecuario ---
write_csv(
  tabla_agro_composicion,
  "tabla_composicion_agro_sexo_jornaleria_2025t3.csv"
)

# --- Tabla estatal: mujeres jornaleras agrícolas ---
write_csv(
  tabla_jornaleras_estatal %>% rename(ent = cve_ent),
  "tabla_estatal_mujeres_jornaleras_agricolas_2025t3.csv"
)
