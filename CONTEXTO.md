# Optimización multiobjetivo: expansión logística de una importadora

## 1. Situación de apertura

> **«Vendemos más que nunca, pero estamos entregando cada vez más tarde. Importamos productos desde China y nuestra bodega de Bogotá ya no da abasto. La junta directiva quiere decidir dónde abrir una bodega adicional. ¿Qué ciudad escogerían?»**

La empresa colombiana vende pequeños electrodomésticos por comercio electrónico. En el escenario de octubre de 2026 recibe **100.000 pedidos mensuales** en seis ciudades, mientras que su bodega actual en Bogotá puede despachar **55.000**. Faltan **45.000 pedidos mensuales de capacidad**. Los productos llegan desde China a los puertos de Cartagena y Buenaventura.

Al comienzo de la clase se muestran únicamente tres alternativas:

| Ciudad de la nueva bodega | Capacidad adicional | Costo fijo mensual |
|---|---:|---:|
| Medellín | 60.000 pedidos | $240 millones |
| Cali | 50.000 pedidos | $220 millones |
| Barranquilla | 45.000 pedidos | $180 millones |

**Votación inicial:** el público dispone de 30 segundos para escoger una ciudad y justificarla. Las tres bodegas podrían resolver por sí solas el déficit de capacidad. Sin embargo, la tabla omite dónde están los compradores, cuánto cuesta abastecer cada bodega y cuánto tarda cada despacho.

**Pregunta de transición:** «¿Qué información necesitarían para defender su decisión ante la junta?».

La clase revela entonces la base completa: **60 zonas de clientes, 100 ubicaciones de bodega, dos puertos y unas 6.000 rutas de distribución**. Parte de los registros contiene nulos, duplicados e inconsistencias. La votación inicial se compara al final con las soluciones obtenidas tras limpiar los datos y optimizar la red.

> **Alcance:** es un caso didáctico completamente sintético. Las ubicaciones geográficas sirven para generar distancias aproximadas; costos, capacidades, tiempos, demanda y tarifas no representan datos comerciales ni rutas reales.

## 2. Qué decisión debe tomar la empresa

Bogotá permanece abierta. La empresa puede abrir **hasta dos bodegas adicionales** entre 99 sitios candidatos. También debe decidir cuántos pedidos de cada zona se despachan desde cada bodega y cómo abastecerlas desde los puertos.

| Ciudad de destino | Pedidos de referencia en octubre de 2026 |
|---|---:|
| Bogotá | 40.000 |
| Medellín | 22.000 |
| Cali | 17.000 |
| Barranquilla | 9.000 |
| Bucaramanga | 7.000 |
| Pereira | 5.000 |
| **Total** | **100.000** |

Las seis ciudades se subdividen en **diez zonas de clientes cada una**. Esta desagregación permite mostrar que incluso dentro de una misma ciudad puede variar el costo y el tiempo estimado de entrega.

La empresa busca simultáneamente:

1. **Minimizar el costo mensual total:** costos fijos de las bodegas nuevas, operación por pedido, abastecimiento desde los puertos y distribución a clientes.
2. **Minimizar el tiempo promedio de entrega al cliente:** días estimados desde la bodega que despacha hasta la zona de destino, ponderados por los pedidos asignados.

Debe atender la demanda proyectada, respetar capacidades, no usar sitios cerrados, abrir como máximo dos bodegas nuevas y distribuir los pedidos disponibles en los dos puertos. El tiempo de abastecimiento portuario figura en los datos, pero **no se suma al tiempo de entrega al cliente** en el modelo base: se asume inventario disponible en las bodegas. Puede estudiarse después como una extensión sobre reposición e inventarios.

## 3. Contenido del dataset

El archivo descargable contiene **12 CSV relacionados por identificadores**. Las filas adicionales debidas a duplicados intencionales se señalan abajo.

| Archivo | Granularidad y función | Filas aproximadas |
|---|---|---:|
| `01_zonas_demanda.csv` | Una fila por zona; ciudad, sector, ubicación y pedidos de referencia | 60 |
| `02_demanda_historica.csv` | Pedidos y devoluciones mensuales por zona, octubre de 2025 a septiembre de 2026 | 724, incluidas 4 duplicadas |
| `03_pronostico_demanda.csv` | Demanda mensual proyectada por zona, octubre de 2026 a septiembre de 2027 | 720 |
| `04_bodegas_candidatas.csv` | B001 Bogotá existente y B002–B100 candidatas; capacidades y costos | 100 |
| `05_puertos.csv` | Cartagena (P01) y Buenaventura (P02) | 2 |
| `06_oferta_puertos_mensual.csv` | Disponibilidad de producto por puerto y mes | 24 |
| `07_rutas_puerto_bodega.csv` | Costos y tiempos de abastecimiento para cada par puerto–bodega | 201, incluida 1 duplicada |
| `08_rutas_bodega_zona.csv` | Distancia, costo y tiempo de entrega por par bodega–zona | 6.001, incluida 1 duplicada |
| `09_controles_mensuales.csv` | Total mensual esperado, límite de aperturas y capacidad de Bogotá | 12 |
| `10_eventos_comerciales.csv` | Eventos y factores sintéticos de demanda | 12 |
| `11_diccionario_datos.csv` | Campos, tipos y unidades | Según columnas |
| `12_guia_calidad.csv` | Incidencias sembradas y tareas de revisión | 8 |

**Claves de unión:** `zona_id` enlaza zonas, histórico, pronóstico y distribución; `bodega_id` enlaza bodegas y ambas matrices de rutas; `puerto_id` enlaza puertos, oferta y rutas de abastecimiento; `mes` enlaza pronóstico, oferta y controles.

La primera ejecución usa **octubre de 2026**. Los meses posteriores permiten explorar crecimiento, estacionalidad y cambios de solución. El histórico sirve para evaluar e imputar pronósticos, pero **no se suma a la demanda proyectada**.

## 4. Limpieza antes de optimizar

Los errores se incluyeron para que la preparación de datos tenga consecuencias visibles en el resultado. Un costo nulo convertido accidentalmente en cero podría hacer parecer atractiva una bodega; una demanda duplicada podría sobredimensionar toda la red.

1. **Comprobar claves y duplicados.** Confirmar una fila por `(mes, zona_id)` en cada tabla de demanda, por `(puerto_id, bodega_id)` en abastecimiento y por `(bodega_id, zona_id)` en distribución. Revisar duplicados exactos y conservar una sola copia.
2. **Normalizar etiquetas.** Corregir variantes de mayúsculas y nombres de ciudades con ayuda del catálogo. Usar los identificadores como claves de unión; no unir por texto de municipio.
3. **Validar tipos y rangos.** Los pedidos, capacidades y costos no deben ser negativos; los tiempos deben ser positivos y plausibles; la confiabilidad debe estar entre 0 y 1. Investigar devoluciones superiores a pedidos.
4. **Tratar los nulos con reglas documentadas.** En demanda, contrastar el histórico y los controles mensuales; en rutas, estimar únicamente cuando exista información comparable. Si una ruta no puede estimarse con fundamento, excluirla del conjunto de arcos permitidos. Nunca reemplazar automáticamente costos o tiempos faltantes con cero.
5. **Reconciliar octubre.** Tras el tratamiento de registros inválidos, la demanda de las 60 zonas debe sumar **100.000 pedidos**, y la oferta de los puertos debe sumar lo mismo. Registrar por separado cada ajuste necesario para cuadrar el control.
6. **Construir las tablas limpias del modelo.** Seleccionar `mes = 2026-10`, conservar B001 como bodega obligatoria y los candidatos habilitados, y verificar que las rutas supervivientes permitan abastecer y atender todas las zonas.

La guía de calidad enumera los problemas intencionales, pero **no incluye una solución depurada**. Los valores imputados y las decisiones de exclusión son parte del ejercicio. Se debe conservar una copia de los CSV originales y una bitácora de cambios.

## 5. Formulación matemática

### Conjuntos e índices

- \(P\): puertos, indexados por \(p\).
- \(J\): bodegas existentes y candidatas, indexadas por \(j\). Bogotá es \(j=\mathrm{B001}\).
- \(I\): zonas de demanda, indexadas por \(i\).
- \(A^{\mathrm{in}}\) y \(A^{\mathrm{out}}\): rutas de abastecimiento y distribución utilizables después de la limpieza.

### Parámetros para un mes seleccionado

- \(d_i\): pedidos proyectados en la zona \(i\).
- \(s_p\): pedidos disponibles desde el puerto \(p\).
- \(K_j\): capacidad mensual de la bodega \(j\).
- \(F_j\): costo fijo mensual **adicional** de abrir la bodega candidata \(j\); \(F_{\mathrm{B001}}=0\) por ser una operación existente y constante entre alternativas.
- \(v_j\): costo variable de operación por pedido en \(j\).
- \(a_{pj}\): costo por pedido abastecido del puerto \(p\) a \(j\).
- \(c_{ji}\): costo por pedido distribuido desde \(j\) hacia \(i\).
- \(t_{ji}\): días estimados de entrega de \(j\) a \(i\).
- \(D=\sum_i d_i\): total mensual de pedidos.

### Variables de decisión

- \(y_j\in\{0,1\}\): indica si opera la bodega \(j\); \(y_{\mathrm{B001}}=1\).
- \(g_{pj}\geq 0\): pedidos abastecidos desde el puerto \(p\) hacia la bodega \(j\).
- \(x_{ji}\geq 0\): pedidos despachados desde la bodega \(j\) hacia la zona \(i\).

Para un plan mensual agregado, \(g\) y \(x\) pueden ser continuas; si se necesita contar cada pedido indivisible, se declaran enteras. Las rutas inexistentes o descartadas no se crean como variables.

### Objetivo 1: costo mensual

\[
C=\sum_{j\ne\mathrm{B001}}F_jy_j
 +\sum_j v_j\sum_i x_{ji}
 +\sum_{(p,j)\in A^{\mathrm{in}}}a_{pj}g_{pj}
 +\sum_{(j,i)\in A^{\mathrm{out}}}c_{ji}x_{ji}.
\]

### Objetivo 2: tiempo promedio de entrega

\[
T=\frac{\sum_{(j,i)\in A^{\mathrm{out}}}t_{ji}x_{ji}}{D}.
\]

El denominador \(D\) es conocido para el mes; por eso este objetivo sigue siendo lineal en las variables de asignación.

### Restricciones principales

\[
\sum_{j:(j,i)\in A^{\mathrm{out}}}x_{ji}=d_i
\quad \forall i\in I
\qquad\text{(atender cada zona).}
\]

\[
\sum_{i:(j,i)\in A^{\mathrm{out}}}x_{ji}\leq K_jy_j
\quad \forall j\in J
\qquad\text{(capacidad y apertura).}
\]

\[
\sum_{p:(p,j)\in A^{\mathrm{in}}}g_{pj}
=\sum_{i:(j,i)\in A^{\mathrm{out}}}x_{ji}
\quad \forall j\in J
\qquad\text{(flujo que entra y sale).}
\]

\[
\sum_{j:(p,j)\in A^{\mathrm{in}}}g_{pj}=s_p
\quad \forall p\in P
\qquad\text{(oferta portuaria).}
\]

\[
y_{\mathrm{B001}}=1,\qquad
\sum_{j\ne\mathrm{B001}}y_j\leq 2
\qquad\text{(bodega existente y máximo dos aperturas).}
\]

Debe verificarse \(\sum_p s_p=\sum_i d_i\) antes de resolver. La formulación supone productos intercambiables y no modela SKU, inventario ni ventanas horarias. Esto acota lo que significan sus resultados.

## 6. Cómo se resolvería computacionalmente

Se trata de un **modelo de programación lineal entera mixta**: \(y_j\) es binaria y los flujos son continuos en la versión agregada. Para mantener visible la naturaleza multiobjetivo, se obtiene más de una solución:

1. Resolver una vez **minimizando solo \(C\)** para conocer el menor costo factible.
2. Resolver una vez **minimizando solo \(T\)** para conocer el menor tiempo factible.
3. Seleccionar varios límites \(\tau\) entre esos dos extremos y, para cada uno, resolver
   \[
   \min C\quad\text{sujeto a}\quad T\leq\tau
   \]
   junto con todas las restricciones operativas.
4. Comparar las soluciones resultantes por costo y tiempo. Eliminar configuraciones dominadas o puntos repetidos y mostrar las alternativas eficientes en una gráfica: **costo mensual en X y tiempo promedio en Y**.
5. Para cada punto de interés, mostrar las bodegas abiertas, la asignación de pedidos por zona, la utilización de capacidad y los flujos desde cada puerto.

**Una ejecución individual** con un límite \(\tau\) minimiza un solo objetivo. **La exploración de varios límites y la construcción del frente de Pareto** constituye el análisis multiobjetivo. Así se puede explicar cuánto costo adicional exige una entrega más rápida.

En Python, el flujo sería: cargar CSV con `pandas`, validar y limpiar, construir el modelo con `Pyomo` o `PuLP`, resolverlo con un optimizador compatible de programación entera mixta y graficar con `matplotlib`. El código debe registrar supuestos y las filas rechazadas. El resultado de la limpieza debe conciliarse con los controles antes de llamar al optimizador.

Con 100 sitios, 60 zonas y dos puertos, hay hasta **6.000 flujos de distribución**, **200 flujos de abastecimiento** y 99 aperturas binarias por mes. Esto es una escala razonable para ilustrar el uso de un optimizador, aunque el tiempo de ejecución dependerá de los datos depurados, la formulación, el equipo y el solucionador. No hace falta enumerar manualmente cada combinación de sitios y cada posible reparto.

## 7. Demostración de 20 minutos

| Tiempo | Sección del índice | Desarrollo en clase |
|---|---|---|
| 0–2 min | **1. El reto empresarial** | Presentar el crecimiento de ventas, el déficit de 45.000 pedidos y la votación entre Medellín, Cali y Barranquilla. |
| 2–4 min | **2. Datos para tomar la decisión** | Mostrar demanda por ciudad, capacidad, costos y un vistazo a las 60 zonas y las rutas. Preguntar qué faltaba en la votación. Avisar que hay registros por depurar. |
| 4–6 min | **3. ¿Qué es la optimización multiobjetivo?** | Formular las dos metas: menor costo mensual y menor tiempo promedio de entrega. Explicar por qué una misma red puede mejorar una y empeorar la otra. |
| 6–8 min | **4. Dominancia y frente de Pareto** | Comparar tres *planes completos* de ejemplo, cada uno con costo y tiempo calculados. Mostrar cómo se descarta un plan dominado y qué significa que otro sea eficiente. Identificarlos como ilustrativos, no como resultados del dataset. |
| 8–11 min | **5. Formulación del modelo** | Explicar las decisiones de apertura y asignación de pedidos, más demanda, capacidad, abastecimiento y máximo dos bodegas nuevas. Mostrar el flujo puerto → bodega → zona. |
| 11–16 min | **6. Demostración computacional** | Enseñar dos incidencias de los CSV y las reglas con que se depuraron; cargar las tablas limpias ya preparadas, resolver varios límites de tiempo y graficar costo frente a tiempo. |
| 16–20 min | **7. Resultados y decisión final** | Mostrar bodegas abiertas, utilización y tiempos de dos o tres soluciones eficientes; comparar con la votación inicial. Preguntar cuánto pagaría la junta por acelerar las entregas. |

La explicación de dominancia se hace sobre **configuraciones completas de la red**, con asignaciones factibles y métricas comparables. No se puede afirmar que una ciudad o una bodega domina a otra solo por su arriendo y capacidad. En la sección de resultados se vuelve al frente de Pareto con los números calculados por el modelo.

**Pregunta final para la junta:** «¿Cuánto estamos dispuestos a pagar cada mes para reducir el tiempo promedio de entrega, y qué zonas reciben esa mejora?»

El optimizador entrega alternativas factibles y eficientes bajo los supuestos establecidos. La elección empresarial requiere además validar costos reales, disponibilidad de inmuebles, niveles de servicio y la precisión de la demanda prevista.
