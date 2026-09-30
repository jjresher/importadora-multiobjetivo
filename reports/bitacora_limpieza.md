# Bitácora de limpieza

Generada automáticamente por `src/limpieza.py` a partir de `data/raw/` (sin modificar).
El detalle de cada cambio está en `reports/cambios_limpieza.csv`.

## Reglas aplicadas

| Regla | Descripción |
|---|---|
| R1 | Duplicados exactos: se conserva una copia. Si una clave se repite con valores distintos, el script se detiene. |
| R2 | Etiquetas de municipio normalizadas contra un catálogo (sin tildes/mayúsculas, alias `B/manga`). Las uniones se hacen solo por ID. |
| R3 | Rangos: devoluciones ≤ pedidos; confiabilidad en [0,1]. Un valor fuera de rango en un campo que no entra al modelo se anula sin eliminar el registro. |
| R4 | Rutas: costo o tiempo nulo, ≤ 0 o atípico (fuera de 0.5–2.0 × la mediana de sus comparables) se imputa con la mediana de las 5 rutas válidas del mismo puerto (abastecimiento) o de la misma bodega (distribución) con distancia más cercana (±25%). Con menos de 3 comparables el arco se excluye. Nunca se usa cero. |
| R5 | Demanda y oferta: se concilian contra `09_controles_mensuales.csv` (el total del control menos la suma de celdas válidas). Si hay varias celdas inválidas en un mes, el residuo se reparte en proporción a referencia × factor del mes. |
| R6 | Bodegas con capacidad o costo fijo nulo se excluyen del modelo: son atributos propios del inmueble sin ficha ni dato comparable. |

Fundamento de R4 y R5 (verificado sobre los datos válidos):

- Dentro de cada puerto, costo y tiempo de abastecimiento dependen casi solo de la distancia (tiempo ≈ 0,6 + 0,00185·km; costo con residuo ≈ ±8 %); no hay efecto propio por bodega.
- En distribución, el tiempo tiene correlación 0,996 con la distancia y el costo 0,97. El transportista no explica varianza (<0,1 %); la bodega sí, un poco (≈ 5–11 %). Por eso los comparables son de la misma bodega.
- El pronóstico de cada celda válida es `referencia de octubre × factor del mes` con ruido de ±9 %. Cada control mensual es exactamente la suma de las 60 zonas.

## Resumen de cambios por archivo

| archivo                       |   anulado |   eliminado |   excluido |   imputado |   modificado |
|:------------------------------|----------:|------------:|-----------:|-----------:|-------------:|
| 01_zonas_demanda.csv          |         0 |           0 |          0 |          0 |            3 |
| 02_demanda_historica.csv      |         0 |           4 |          0 |          6 |            0 |
| 03_pronostico_demanda.csv     |         0 |           0 |          0 |          7 |            0 |
| 04_bodegas_candidatas.csv     |         0 |           0 |          4 |          0 |            2 |
| 06_oferta_puertos_mensual.csv |         0 |           0 |          0 |          1 |            0 |
| 07_rutas_puerto_bodega.csv    |         0 |           1 |          0 |          4 |            0 |
| 08_rutas_bodega_zona.csv      |         1 |           1 |          0 |         16 |            0 |

## Detalle de cambios

| archivo                       | clave        | campo                           | valor_original   | valor_nuevo         | regla                                                                                                                                                              | accion     |
|:------------------------------|:-------------|:--------------------------------|:-----------------|:--------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------|
| 01_zonas_demanda.csv          | Z008         | ciudad_canonica                 | Bogota           | Bogotá              | R2: normalizar contra catálogo de municipios                                                                                                                       | modificado |
| 01_zonas_demanda.csv          | Z024         | ciudad_canonica                 | CALI             | Cali                | R2: normalizar contra catálogo de municipios                                                                                                                       | modificado |
| 01_zonas_demanda.csv          | Z045         | ciudad_canonica                 | B/manga          | Bucaramanga         | R2: normalizar contra catálogo de municipios                                                                                                                       | modificado |
| 02_demanda_historica.csv      | 2025-10|Z013 | (fila completa)                 | duplicado exacto | eliminada           | R1: duplicado exacto; se conserva una copia                                                                                                                        | eliminado  |
| 02_demanda_historica.csv      | 2025-11|Z054 | (fila completa)                 | duplicado exacto | eliminada           | R1: duplicado exacto; se conserva una copia                                                                                                                        | eliminado  |
| 02_demanda_historica.csv      | 2026-01|Z028 | (fila completa)                 | duplicado exacto | eliminada           | R1: duplicado exacto; se conserva una copia                                                                                                                        | eliminado  |
| 02_demanda_historica.csv      | 2026-04|Z052 | (fila completa)                 | duplicado exacto | eliminada           | R1: duplicado exacto; se conserva una copia                                                                                                                        | eliminado  |
| 02_demanda_historica.csv      | 2025-10|Z018 | pedidos_realizados              | NA               | 1268                | R4: nulo; promedio de meses vecinos de la zona                                                                                                                     | imputado   |
| 02_demanda_historica.csv      | 2025-11|Z029 | pedidos_realizados              | -14              | 1058                | R4: negativo; promedio de meses vecinos de la zona                                                                                                                 | imputado   |
| 02_demanda_historica.csv      | 2026-04|Z042 | pedidos_realizados              | NA               | 645                 | R4: nulo; promedio de meses vecinos de la zona                                                                                                                     | imputado   |
| 02_demanda_historica.csv      | 2026-01|Z051 | pedidos_realizados              | NA               | 345                 | R4: nulo; promedio de meses vecinos de la zona                                                                                                                     | imputado   |
| 02_demanda_historica.csv      | 2026-07|Z060 | pedidos_realizados              | NA               | 499                 | R4: nulo; promedio de meses vecinos de la zona                                                                                                                     | imputado   |
| 02_demanda_historica.csv      | 2026-02|Z021 | devoluciones                    | 9999             | 12                  | R3: devoluciones > pedidos; mediana de la zona en otros meses                                                                                                      | imputado   |
| 03_pronostico_demanda.csv     | 2026-10|Z003 | pedidos_proyectados             | NA               | 4567                | R5: conciliar con control mensual (control - suma de celdas válidas); motivo: nulo; esperado=4567                                                                  | imputado   |
| 03_pronostico_demanda.csv     | 2026-12|Z006 | pedidos_proyectados             | NA               | 4698                | R5: conciliar con control mensual; residuo 8539 repartido entre 2 celdas en proporción a referencia x factor; motivo: nulo; esperado=4556                          | imputado   |
| 03_pronostico_demanda.csv     | 2026-12|Z014 | pedidos_proyectados             | -250             | 3841                | R5: conciliar con control mensual; residuo 8539 repartido entre 2 celdas en proporción a referencia x factor; motivo: negativo; esperado=3725                      | imputado   |
| 03_pronostico_demanda.csv     | 2027-02|Z046 | pedidos_proyectados             | NA               | 749                 | R5: conciliar con control mensual (control - suma de celdas válidas); motivo: nulo; esperado=696                                                                   | imputado   |
| 03_pronostico_demanda.csv     | 2027-03|Z023 | pedidos_proyectados             | 99000            | 2289                | R5: conciliar con control mensual (control - suma de celdas válidas); motivo: atípico; esperado=2277                                                               | imputado   |
| 03_pronostico_demanda.csv     | 2027-05|Z051 | pedidos_proyectados             | NA               | 449                 | R5: conciliar con control mensual (control - suma de celdas válidas); motivo: nulo; esperado=474                                                                   | imputado   |
| 03_pronostico_demanda.csv     | 2027-08|Z011 | pedidos_proyectados             | NA               | 2149                | R5: conciliar con control mensual (control - suma de celdas válidas); motivo: nulo; esperado=2299                                                                  | imputado   |
| 04_bodegas_candidatas.csv     | B019         | municipio                       | BUCARAMANGA      | Bucaramanga         | R2: normalizar contra catálogo de municipios                                                                                                                       | modificado |
| 04_bodegas_candidatas.csv     | B038         | municipio                       | MALAMBO          | Malambo             | R2: normalizar contra catálogo de municipios                                                                                                                       | modificado |
| 04_bodegas_candidatas.csv     | B027         | capacidad_pedidos_mes           | NA               | NA (sitio excluido) | R6: atributo propio del sitio sin información comparable; excluir candidato                                                                                        | excluido   |
| 04_bodegas_candidatas.csv     | B068         | capacidad_pedidos_mes           | NA               | NA (sitio excluido) | R6: atributo propio del sitio sin información comparable; excluir candidato                                                                                        | excluido   |
| 04_bodegas_candidatas.csv     | B092         | capacidad_pedidos_mes           | NA               | NA (sitio excluido) | R6: atributo propio del sitio sin información comparable; excluir candidato                                                                                        | excluido   |
| 04_bodegas_candidatas.csv     | B080         | costo_fijo_adicional_cop_mes    | NA               | NA (sitio excluido) | R6: atributo propio del sitio sin información comparable; excluir candidato                                                                                        | excluido   |
| 06_oferta_puertos_mensual.csv | 2027-01|P01  | pedidos_disponibles             | NA               | 55912               | R5: control total - otro puerto (verificado con fracción: 55911.6)                                                                                                 | imputado   |
| 07_rutas_puerto_bodega.csv    | P01|B078     | (fila completa)                 | duplicado exacto | eliminada           | R1: duplicado exacto; se conserva una copia                                                                                                                        | eliminado  |
| 07_rutas_puerto_bodega.csv    | P01|B017     | costo_abastecimiento_cop_pedido | NA               | 2876                | R4: nulo; mediana de 5 rutas del mismo puerto_id con distancia más cercana a 147.4 km: B035(141 km), B004(138 km), B037(134 km), B038(128 km), B016(128 km)        | imputado   |
| 07_rutas_puerto_bodega.csv    | P01|B091     | costo_abastecimiento_cop_pedido | NA               | 2876                | R4: nulo; mediana de 5 rutas del mismo puerto_id con distancia más cercana a 142.1 km: B035(141 km), B004(138 km), B037(134 km), B038(128 km), B016(128 km)        | imputado   |
| 07_rutas_puerto_bodega.csv    | P02|B013     | costo_abastecimiento_cop_pedido | -120             | 2395                | R4: no positivo; mediana de 5 rutas del mismo puerto_id con distancia más cercana a 89.2 km: B067(86 km), B069(83 km), B003(96 km), B068(79 km), B014(100 km)      | imputado   |
| 07_rutas_puerto_bodega.csv    | P02|B057     | costo_abastecimiento_cop_pedido | NA               | 5060                | R4: nulo; mediana de 5 rutas del mismo puerto_id con distancia más cercana a 378.0 km: B056(375 km), B011(387 km), B063(368 km), B040(364 km), B012(398 km)        | imputado   |
| 08_rutas_bodega_zona.csv      | B005|Z011    | (fila completa)                 | duplicado exacto | eliminada           | R1: duplicado exacto; se conserva una copia                                                                                                                        | eliminado  |
| 08_rutas_bodega_zona.csv      | B003|Z032    | confiabilidad_pct               | 1.8              | NA                  | R3: fuera de [0,1]; se deja nulo (no interviene en el modelo), arco se conserva                                                                                    | anulado    |
| 08_rutas_bodega_zona.csv      | B001|Z051    | costo_distribucion_cop_pedido   | NA               | 9176                | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 233.1 km: Z056(234 km), Z052(235 km), Z054(243 km), Z055(223 km), Z058(251 km)        | imputado   |
| 08_rutas_bodega_zona.csv      | B016|Z023    | costo_distribucion_cop_pedido   | NA               | 26911               | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 1208.5 km: Z026(1203 km), Z029(1236 km), Z027(1177 km), Z024(1146 km), Z028(1133 km)  | imputado   |
| 08_rutas_bodega_zona.csv      | B028|Z025    | costo_distribucion_cop_pedido   | NA               | 6082                | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 97.5 km: Z024(98 km), Z029(98 km), Z023(96 km), Z026(94 km), Z028(101 km)             | imputado   |
| 08_rutas_bodega_zona.csv      | B048|Z025    | costo_distribucion_cop_pedido   | NA               | 11466               | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 413.4 km: Z046(413 km), Z029(413 km), Z049(410 km), Z026(408 km), Z042(420 km)        | imputado   |
| 08_rutas_bodega_zona.csv      | B052|Z043    | costo_distribucion_cop_pedido   | -4000            | 10061               | R4: no positivo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 372.4 km: Z048(362 km), Z041(358 km), Z028(391 km), Z044(397 km), Z050(347 km) | imputado   |
| 08_rutas_bodega_zona.csv      | B061|Z002    | costo_distribucion_cop_pedido   | NA               | 10059               | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 339.0 km: Z001(334 km), Z005(326 km), Z008(325 km), Z003(320 km), Z010(315 km)        | imputado   |
| 08_rutas_bodega_zona.csv      | B086|Z001    | costo_distribucion_cop_pedido   | NA               | 5862                | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 107.8 km: Z007(108 km), Z008(109 km), Z004(111 km), Z006(103 km), Z003(113 km)        | imputado   |
| 08_rutas_bodega_zona.csv      | B100|Z013    | costo_distribucion_cop_pedido   | NA               | 12797               | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 461.5 km: Z012(472 km), Z018(449 km), Z014(481 km), Z020(487 km), Z011(506 km)        | imputado   |
| 08_rutas_bodega_zona.csv      | B001|Z012    | tiempo_entrega_dias             | NA               | 1.89                | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 289.9 km: Z018(291 km), Z019(294 km), Z013(306 km), Z014(306 km), Z011(310 km)        | imputado   |
| 08_rutas_bodega_zona.csv      | B004|Z042    | tiempo_entrega_dias             | NA               | 2.72                | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 612.1 km: Z044(626 km), Z043(596 km), Z050(635 km), Z046(639 km), Z048(646 km)        | imputado   |
| 08_rutas_bodega_zona.csv      | B009|Z020    | tiempo_entrega_dias             | NA               | 1.89                | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 318.2 km: Z013(320 km), Z016(322 km), Z015(326 km), Z019(328 km), Z017(308 km)        | imputado   |
| 08_rutas_bodega_zona.csv      | B017|Z040    | tiempo_entrega_dias             | NA               | 0.83                | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 14.1 km: Z032(14 km), Z034(15 km), Z038(13 km), Z037(12 km), Z031(11 km)              | imputado   |
| 08_rutas_bodega_zona.csv      | B018|Z036    | tiempo_entrega_dias             | 180              | 0.76                | R4: atípico; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 8.0 km: Z033(8 km), Z037(8 km), Z039(8 km), Z032(10 km), Z035(11 km)               | imputado   |
| 08_rutas_bodega_zona.csv      | B039|Z054    | tiempo_entrega_dias             | NA               | 3.46                | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 924.9 km: Z009(920 km), Z010(913 km), Z052(909 km), Z001(901 km), Z006(898 km)        | imputado   |
| 08_rutas_bodega_zona.csv      | B068|Z036    | tiempo_entrega_dias             | NA               | 4.04                | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 1115.9 km: Z035(1110 km), Z033(1124 km), Z039(1100 km), Z037(1142 km), Z034(1079 km)  | imputado   |
| 08_rutas_bodega_zona.csv      | B097|Z021    | tiempo_entrega_dias             | NA               | 4.05                | R4: nulo; mediana de 5 rutas del mismo bodega_id con distancia más cercana a 1064.8 km: Z029(1060 km), Z024(1057 km), Z025(1147 km), Z028(1153 km), Z027(1158 km)  | imputado   |

## Filas y conciliaciones

| archivo                    |   filas_crudas |   filas_o_elementos_utilizables |
|:---------------------------|---------------:|--------------------------------:|
| 02_demanda_historica.csv   |            724 |                             720 |
| 03_pronostico_demanda.csv  |            720 |                             720 |
| 04_bodegas_candidatas.csv  |            100 |                              96 |
| 07_rutas_puerto_bodega.csv |            201 |                             200 |
| 08_rutas_bodega_zona.csv   |           6001 |                            6000 |

## Validaciones del modelo del mes base

- Demanda 2026-10 cruda (suma sin nulos): 95,433
- Demanda 2026-10 limpia: 100,000
- Oferta 2026-10: P01=60,000, P02=40,000
- Bodegas en el modelo: 96 (B001 + 95 candidatas)
- Arcos puerto→bodega: 192
- Arcos bodega→zona: 5760
- Zonas con al menos una ruta: 60 / 60
- Capacidad máxima alcanzable (B001 + 2 mayores): 191,000

Además, `validar_tablas_limpias()` comprueba con asserts, para los 12 meses: claves únicas, municipios en el catálogo, sin nulos ni negativos, devoluciones ≤ pedidos, pronóstico = control, oferta = demanda y fracciones por puerto, bodegas habilitadas completas, rutas válidas con costo y tiempo > 0, y confiabilidad en [0,1]. Si alguna falla, el script se detiene.

## Validaciones cruzadas

- Pronóstico 2026-10|Z003 imputado = 4567; `pedidos_octubre_referencia` de 01_zonas = 4567 → coincide.
- Pronóstico limpio de 2026-10 igual a la referencia de 01_zonas en 60 / 60 zonas.

Rutas imputadas: valor con R4 (mediana de vecinos) frente a una regresión lineal sobre la distancia ajustada con las rutas válidas no imputadas del mismo grupo:

| archivo | clave | campo | R4 | regresión | diferencia |
|---|---|---|---:|---:|---:|
| 07 | P01|B017 | costo_abastecimiento_cop_pedido | 2,876.00 | 2,895.83 | -0.7% |
| 07 | P01|B091 | costo_abastecimiento_cop_pedido | 2,876.00 | 2,854.00 | +0.8% |
| 07 | P02|B013 | costo_abastecimiento_cop_pedido | 2,395.00 | 2,475.61 | -3.3% |
| 07 | P02|B057 | costo_abastecimiento_cop_pedido | 5,060.00 | 4,700.46 | +7.6% |
| 08 | B001|Z051 | costo_distribucion_cop_pedido | 9,176.00 | 8,287.61 | +10.7% |
| 08 | B016|Z023 | costo_distribucion_cop_pedido | 26,911.00 | 28,258.69 | -4.8% |
| 08 | B028|Z025 | costo_distribucion_cop_pedido | 6,082.00 | 6,075.69 | +0.1% |
| 08 | B048|Z025 | costo_distribucion_cop_pedido | 11,466.00 | 12,031.49 | -4.7% |
| 08 | B052|Z043 | costo_distribucion_cop_pedido | 10,061.00 | 11,178.97 | -10.0% |
| 08 | B061|Z002 | costo_distribucion_cop_pedido | 10,059.00 | 10,615.49 | -5.2% |
| 08 | B086|Z001 | costo_distribucion_cop_pedido | 5,862.00 | 5,743.22 | +2.1% |
| 08 | B100|Z013 | costo_distribucion_cop_pedido | 12,797.00 | 12,967.88 | -1.3% |
| 08 | B001|Z012 | tiempo_entrega_dias | 1.89 | 1.74 | +8.5% |
| 08 | B004|Z042 | tiempo_entrega_dias | 2.72 | 2.60 | +4.5% |
| 08 | B009|Z020 | tiempo_entrega_dias | 1.89 | 1.81 | +4.2% |
| 08 | B017|Z040 | tiempo_entrega_dias | 0.83 | 0.85 | -2.4% |
| 08 | B018|Z036 | tiempo_entrega_dias | 0.76 | 0.77 | -1.1% |
| 08 | B039|Z054 | tiempo_entrega_dias | 3.46 | 3.51 | -1.4% |
| 08 | B068|Z036 | tiempo_entrega_dias | 4.04 | 4.05 | -0.1% |
| 08 | B097|Z021 | tiempo_entrega_dias | 4.05 | 3.89 | +4.0% |

Desviación máxima de las rutas válidas no imputadas frente a su propia recta (si es pequeña, no quedan atípicos sin detectar):

- 07_rutas_puerto_bodega.csv · costo_abastecimiento_cop_pedido: 17.9%
- 08_rutas_bodega_zona.csv · costo_distribucion_cop_pedido: 27.9%
- 08_rutas_bodega_zona.csv · tiempo_entrega_dias: 28.0%

## Observaciones que no se corrigen

- `11_diccionario_datos.csv` declara la unidad de `porcentaje_pedidos_urgentes` como «pedidos/mes», pero los valores son fracciones en [0,1]. Se interpreta como fracción; no interviene en el modelo.
- El histórico de septiembre de 2026 supera la referencia de octubre de 2026 en las 60 zonas (mediana +18 %, mínimo +2,7 %), y la tendencia del histórico es creciente. El pronóstico base (100.000) parece conservador frente a la tendencia reciente. No se ajusta porque el control mensual lo fija, pero conviene revisar la sensibilidad a la demanda.
- `habilitada_octubre_2026` vale 1 para las 100 bodegas; la exclusión por datos faltantes se registra en la columna nueva `habilitada_modelo`.
