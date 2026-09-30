# Resultados: expansión logística de la importadora

Mes base: **octubre de 2026** (100.000 pedidos; 60.000 por Cartagena y 40.000 por Buenaventura). La bodega B001 de Bogotá sigue abierta en todos los planes. Los costos están en millones de COP por mes (M) y los tiempos son el promedio de días de entrega al cliente, ponderado por pedidos.

Todas las cifras salen de `python src/limpieza.py` y `python src/pareto.py`. Los archivos de detalle están en [`reports/pareto/`](pareto/).

## Resumen

- **Recomendación: abrir B012 (Medellín, Parque logístico 3) y B013 (Cali, Parque logístico 1).** Cuesta 1.575,5 M al mes, apenas **0,29 M más** que la opción más barata (abrir solo B012), y baja el tiempo promedio de entrega de **1,334 a 1,091 días** (−18 %).
- La mejora viene casi toda de **Cali**, donde el tiempo promedio pasa de 2,21 a 0,77 días.
- Más allá de ese punto, acelerar sale muy caro: bajar el tiempo 0,010 días adicionales cuesta hasta **147 M más al mes**.
- **Ninguna de las tres opciones de la votación inicial es eficiente.** Solo Medellín (B002) cuesta 11,8 M más y es más lenta que el plan de mínimo costo. Solo Cali (B003) y solo Barranquilla (B004) cuestan unos 150 M más al mes y son más lentas que cualquier plan del frente.
- **B012 + B013 también resiste los otros 11 meses del pronóstico.** Abrir solo B012 no alcanza en diciembre (123.667 pedidos contra 115.000 de capacidad). B012 + B013 es la opción más barata o está a menos de 8,2 M de ella en todos los meses.

## 1. Soluciones eficientes (frente de Pareto)

![Frente de Pareto](pareto/frente_pareto.png)

| Punto | Bodegas nuevas | Costo (M/mes) | Tiempo promedio (días) | Fijo | Operación | Abastecimiento | Distribución |
|---|---|---:|---:|---:|---:|---:|---:|
| P1 | B012 Medellín | 1.575,2 | 1,334 | 195,0 | 112,2 | 606,6 | 661,4 |
| **P2** | **B012 Medellín + B013 Cali** | **1.575,5** | **1,091** | 356,0 | 110,4 | 595,9 | 513,3 |
| P3 | B012 Medellín + B013 Cali | 1.576,2 | 1,089 | 356,0 | 110,5 | 596,1 | 513,6 |
| P4 | B012 Medellín + B013 Cali | 1.577,5 | 1,088 | 356,0 | 110,5 | 597,9 | 513,1 |
| P5 | B012 Medellín + B015 Cali | 1.625,8 | 1,084 | 391,0 | 118,8 | 601,4 | 514,5 |
| P6 | B012 Medellín + B015 Cali | 1.626,1 | 1,083 | 391,0 | 119,1 | 601,6 | 514,4 |
| P7 | B012 Medellín + B015 Cali | 1.627,0 | 1,082 | 391,0 | 119,0 | 603,3 | 513,6 |
| P8 | B010 Medellín + B015 Cali | 1.713,0 | 1,082 | 478,0 | 102,9 | 603,0 | 529,2 |
| P9 | B010 Medellín + B015 Cali | 1.722,9 | 1,081 | 478,0 | 103,5 | 611,2 | 530,1 |

**Cómo se obtuvo el frente.**
- **Extremos:** se minimizó primero el costo (P1) y después el tiempo (P9). Cada extremo se desempató con el otro objetivo. Minimizar solo el tiempo daba 1.903 M para el mismo tiempo que P9, es decir, 180 M de más.
- **Puntos intermedios:** 10 límites de tiempo τ repartidos uniformemente, más un refinamiento que prueba un límite intermedio en cada hueco de más de 0,0015 días y 1 M. En total se resolvieron 19 modelos, que dieron 9 puntos eficientes distintos.
- **Puntos con las mismas bodegas:** algunos puntos comparten bodegas (P2–P4, P5–P7, P8–P9). Entre ellos solo cambia cómo se reparten los pedidos entre bodegas: se paga un poco más por mandar pedidos a la bodega más rápida.

## 2. Costo adicional por día ahorrado

| Paso | Cambio | Costo adicional (M/mes) | Tiempo ahorrado (días) | Costo por centésima de día (M) |
|---|---|---:|---:|---:|
| P1 → P2 | Se abre B013 Cali | 0,29 | 0,243 | **0,01** |
| P2 → P4 | Se reasignan pedidos | 2,04 | 0,003 | 0,8 |
| P4 → P5 | B013 se cambia por B015 Cali | 48,20 | 0,004 | 12,5 |
| P5 → P7 | Se reasignan pedidos | 1,21 | 0,002 | 0,6 |
| P7 → P8 | B012 se cambia por B010 Medellín | 86,02 | 0,001 | 92,7 |
| P8 → P9 | Se reasignan pedidos | 9,89 | 0,001 | 106,6 |

El frente tiene un **codo muy marcado en P2**. Frente a P1, la mejora de tiempo de P2 es casi gratis: unos **1,2 M por día** de reducción del promedio. De P2 a P9 se pagan **147 M más al mes** por 0,010 días menos, unos **14.700 M por día**.

Para la junta, la pregunta relevante no es cuánto pagar por acelerar más allá de P2. Es si vale la pena pagar 0,29 M al mes para que Cali reciba en 0,8 días en lugar de 2,2. Todo lo que viene después de P2 compra mejoras de horas o minutos a un costo muy alto.

## 3. Qué zonas mejoran

Tiempo promedio de entrega por ciudad (días). El detalle por zona está en [`tiempo_por_zona.csv`](pareto/tiempo_por_zona.csv).

| Ciudad | Pedidos | P1 | P2 | P5 | P9 |
|---|---:|---:|---:|---:|---:|
| Bogotá | 40.000 | 0,77 | 0,77 | 0,77 | 0,77 |
| Medellín | 22.000 | 0,78 | 0,78 | 0,78 | 0,76 |
| Cali | 17.000 | **2,21** | **0,77** | 0,75 | 0,75 |
| Barranquilla | 9.000 | 2,86 | 2,86 | 2,86 | 2,88 |
| Bucaramanga | 7.000 | 2,02 | 2,02 | 2,02 | 2,02 |
| Pereira | 5.000 | 1,59 | 1,61 | 1,57 | 1,54 |

- **De P1 a P2:**
  - **Las 10 zonas de Cali** (17.000 pedidos) bajan entre 1,23 y 1,62 días; en P1 las atendían desde Medellín y Bogotá.
  - Pereira queda casi igual: 2 zonas mejoran unos 0,1 días y 5 empeoran entre 0,02 y 0,11 días. En P2, B013 atiende 4.096 de sus 5.000 pedidos.
  - Bogotá, Medellín, Barranquilla y Bucaramanga no cambian.
- **De P2 a P9:** los cambios por zona son de ±0,1–0,25 días en Medellín, Cali, Pereira, Barranquilla y Bucaramanga, y en parte se compensan entre sí. En el promedio general el cambio es de solo 0,010 días.
- **Barranquilla (9.000 pedidos) es la ciudad peor atendida en todo el frente,** con unos 2,9 días. En todas las soluciones eficientes se atiende desde Medellín. Abrir una bodega allí no resulta eficiente con el promedio general como medida. Si la empresa quisiera un tiempo máximo por ciudad, habría que añadirlo como restricción (ver limitaciones).

**Utilización y flujos portuarios del plan recomendado (P2).**
- **Utilización:** B001 Bogotá 73 % (40.000 de 55.000); B012 Medellín 65 % (38.904 de 60.000); B013 Cali 39 % (21.096 de 54.000). Queda holgura para crecer.
- **Flujos por puerto:** Cartagena abastece B012 (38.904) y B001 (21.096); Buenaventura abastece B013 (21.096) y B001 (18.904).

En P1, B012 trabaja al 95 % y B001 recibe los 40.000 pedidos de Buenaventura. Esto pasa porque el modelo obliga a usar toda la oferta de cada puerto, y sin bodega en Cali el destino más barato para Buenaventura es Bogotá.

## 4. La votación inicial frente al modelo

| Plan votado | Bodega | Costo (M/mes) | Tiempo (días) | ¿Eficiente? | Lo superan | Sobrecosto frente al plan eficiente más barato que lo supera | Mejor única apertura en esa ciudad |
|---|---|---:|---:|---|---|---:|---|
| Solo Medellín | B002 | 1.587,0 | 1,349 | No | P1–P4 | 11,8 M | B012: 1.575,2 M · 1,334 d |
| Solo Cali | B003 | 1.727,6 | 1,488 | No | P1–P9 | 152,4 M | B013: 1.658,9 M · 1,477 d |
| Solo Barranquilla | B004 | 1.733,1 | 1,795 | No | P1–P9 | 157,9 M | B018: 1.700,3 M · 1,783 d |

- **Medellín era la intuición correcta, pero con el sitio equivocado.** B002 sale 44 M más barata que B012 en operación y abastecimiento. Aun así, su costo fijo es 45 M mayor y su distribución 11 M más cara, así que en total cuesta 11,8 M más al mes y además es más lenta. Nada de esto se veía en la tabla de la votación, que solo mostraba capacidad y costo fijo.
- **Cali y Barranquilla no funcionan como única bodega nueva.** Con una sola apertura, la bodega nueva debe cubrir el déficit y atender Medellín desde lejos. Con solo B003, Cali despacha 15.896 pedidos a Medellín y 6.410 a Barranquilla. Cali sí vale la pena, pero **como segunda bodega junto a Medellín**, no en lugar de ella.
- **La pregunta "¿qué ciudad escogerían?" estaba mal planteada.** La mejor respuesta es un plan con dos bodegas, que no estaba entre las opciones, y cuesta prácticamente lo mismo que la mejor bodega única.

## 5. Robustez

**Otros meses del pronóstico.** Se evaluó cada configuración del frente con la demanda y la oferta de los 12 meses, manteniendo la misma red y los mismos costos ([`escenarios_mensuales.csv`](pareto/escenarios_mensuales.csv)):

| Configuración | Costo total en 12 meses (M) | Tiempo mensual (días) | Comentario |
|---|---:|---:|---|
| Óptimo de cada mes (cambia la red cada mes) | 19.615,4 | — | Referencia teórica, no es un plan operable |
| **B012 + B013** | **19.639,3** | 1,083 – 1,106 | La más barata en 7 de 12 meses; nunca más de 8,2 M por encima del óptimo del mes |
| B012 sola | infactible | 1,324 – 1,343 | En diciembre (123.667 pedidos) le falta capacidad; en los otros 11 meses cuesta 64,7 M más que B012 + B013 |
| B012 + B015 | 20.251,2 | 1,077 – 1,100 | |
| B010 + B015 | 21.285,0 | 1,076 – 1,099 | |

Abrir solo B012 es lo más barato en octubre, pero es una red frágil: deja a B012 al 95 % y no aguanta el pico de diciembre. B012 + B013 cuesta 24 M más al año que cambiar de red cada mes, algo que en la práctica no es posible.

**Dato imputado con influencia.** La única ruta imputada que usan las soluciones eficientes es **Buenaventura → B013** (P2–P4). Su costo original era −120 COP por pedido y se imputó con 2.395, la mediana de 5 rutas comparables; una regresión sobre la distancia da 2.476. Si ese costo varía ±15 %, el plan P2 cambia ±7,5 M y sigue siendo B012 + B013. Con −15 %, B012 + B013 pasa a ser directamente la opción de mínimo costo. Conviene confirmar esa tarifa con el operador.

**Bodegas excluidas por falta de datos** ([`sensibilidad_bodegas_excluidas.csv`](pareto/sensibilidad_bodegas_excluidas.csv)):
- **B027 (Cartagena), B068 (Yumbo) y B092 (Sincelejo)** no tienen dato de capacidad. No entrarían al frente ni suponiendo la capacidad máxima del dataset (68.000), así que excluirlas no cambia el resultado.
- **B080 (Armenia)** no tiene dato de costo fijo. Solo desplazaría a P1 si su costo fijo real fuera menor de **108 M al mes**; el menor costo fijo del dataset es 145 M. Conviene pedir su ficha, pero es poco probable que cambie la decisión.

## 6. Supuestos y limitaciones

- **Datos sintéticos.** El caso es didáctico: costos, capacidades, tiempos, demanda y tarifas no representan datos comerciales reales. Las cifras sirven para ilustrar el método, no para decidir una inversión real sin validarlas.
- **El abastecimiento portuario no se suma al tiempo de entrega.** T mide solo el tramo bodega → cliente; se supone que hay inventario disponible en las bodegas. Los tiempos de puerto a bodega (entre 0,6 y 2,9 días) afectarían la reposición y el inventario de seguridad, no la promesa al cliente.
- **Productos intercambiables.** No se modelan referencias de producto (SKU), inventario, ventanas horarias ni pedidos urgentes. La proporción de pedidos urgentes (entre 12 % y 42 % según la zona) no interviene en el modelo.
- **Flujos continuos.** Se planea en agregado mensual, así que puede asignar pedidos fraccionarios. El efecto en costo y tiempo es despreciable.
- **Un solo mes, sin horizonte de inversión.** El costo fijo es mensual y se decide mes a mes. No hay costo de apertura o cierre, contratos mínimos ni horizonte plurianual. La sección 5 muestra que la red recomendada funciona en los 12 meses, pero no es una optimización multiperíodo.
- **Reparto portuario fijo en 60/40.** La oferta de cada puerto debe usarse completa. Esto obliga a enviar pedidos de Buenaventura a Bogotá cuando no hay bodega en Cali. Con un reparto flexible entre puertos, el costo de P1 bajaría y el codo del frente podría moverse.
- **El promedio esconde la equidad entre zonas.** T es un promedio nacional. Barranquilla (unos 2,9 días) y Bucaramanga (unos 2,0 días) quedan lejos de las demás ciudades en todo el frente. Si la empresa necesita un tiempo máximo por ciudad o por zona, hay que añadirlo como restricción y el resultado cambiaría.
- **Pronóstico posiblemente conservador.** El histórico de septiembre de 2026 supera la referencia de octubre en las 60 zonas (+18 % en la mediana). Si la demanda real se parece más al histórico, el caso a favor de B012 + B013 se fortalece: B012 sola quedaría sin capacidad.
- **La confiabilidad del transportista no se usa.** El dato está en los CSV, pero no interviene en el modelo; se podría usar como tercer objetivo o como restricción mínima.
- **Decisiones de limpieza que afectan el alcance.** Se excluyeron 4 candidatas y se imputaron 20 valores de rutas; el detalle está en [`bitacora_limpieza.md`](bitacora_limpieza.md). La sección 5 muestra que ninguna de esas decisiones cambia la recomendación.

## 7. Reproducibilidad

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python src/limpieza.py   # data/raw → data/clean + bitácora (≈ 5 s)
.venv/bin/python src/pareto.py     # frente, votación, sensibilidad y escenarios (≈ 5 min)
```

El solver es HiGHS, a través de PuLP 4.0 y `highspy`. `src/modelo.py` contiene el MILP reutilizable, y `python src/modelo.py` resuelve y valida la solución de mínimo costo.
