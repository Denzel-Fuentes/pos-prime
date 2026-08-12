# Cómo se modelan los productos: grupos, variantes y combos

Guía de cómo está organizado el catálogo y por qué. Complementa la
[guía de uso del módulo restaurante](restaurant-module.md), que cubre la operación diaria;
esto es el "dónde va cada cosa" cuando das de alta un plato nuevo.

---

## 1. El Item Group es la pieza central

En ERPNext un Item Group es sobre todo una categoría contable. En este módulo hace mucho
más: es **la unidad de selección** de la que dependen cuatro cosas distintas.

| Qué | Cómo usa el Item Group |
|---|---|
| Filtro de categorías del POS | Una pestaña por grupo. **Solo lista grupos hoja** (los que no son padres de otros). |
| Slots de combo | Cada slot dice "de este grupo se elige", con la opción de incluir subgrupos. |
| Menú del día | Los grupos listados en Restaurant Settings exigen marcar sus platos al abrir turno. |
| Alcance de modificadores | Un grupo de modificadores puede aplicarse a grupos de ítems enteros. |

De ahí la regla práctica: **un plato va en el grupo por el que lo vas a querer elegir**, no
en el que suena más lógico en un plan de cuentas.

---

## 2. Cómo está armado tu catálogo hoy

Árbol real de Item Groups del sitio:

```
Todos los grupos de artículos
├── Productos          ← abarrotes / tienda (con inventario)
├── Materia prima
├── Servicios
├── Sub-Ensamblajes
├── Consumible
├── Sopas              ← menú del día
├── Segundos           ← menú del día
├── Refrescos          ← menú del día
└── Pollo a la Brasa   ← grupo padre (no aparece como pestaña)
    ├── Pollo 1/4
    ├── Pollo 1/2
    └── Pollo Entero
```

Los ítems de comida:

| Ítem | Grupo | Tipo | Precio | Stock |
|---|---|---|---|---|
| Sopa de Maní / Sopa de Quinua | Sopas | simple | 6.00 | no |
| Milanesa de Pollo / Silpancho | Segundos | simple | 10.00 / 9.00 | no |
| Mocochinchi / Refresco de Maracuyá | Refrescos | simple | 2.00 / 4.00 | sí |
| **Pollo a la Brasa 1/4** | Pollo 1/4 | **plantilla** | — | no |
| ├ Pecho | Pollo 1/4 | variante (Corte = Pecho) | 12.00 | no |
| └ Pierna | Pollo 1/4 | variante (Corte = Pierna) | 12.00 | no |
| **Pollo a la Brasa 1/2** | Pollo 1/2 | **plantilla** | — | no |
| ├ Contra+Ala | Pollo 1/2 | variante (Corte = Contra+Ala) | 22.00 | no |
| └ Pierna+Pecho | Pollo 1/2 | variante (Corte = Pierna+Pecho) | 22.00 | no |
| Pollo a la Brasa Entero | Pollo Entero | simple | 40.00 | no |

Los abarrotes (Aceite, Arroz, Leche, Huevos…) viven en `Productos` y sí llevan inventario.

---

## 3. Los tres patrones, y cuándo usar cada uno

El pollo a la brasa usa los tres a la vez, y esa es justamente la parte que conviene
entender.

### 3.1 Ítem simple

Un plato, un precio, sin opciones: **Sopa de Maní**, **Pollo a la Brasa Entero**.

Sale como una tarjeta en la grilla y se agrega al carrito de un toque.

### 3.2 Plantilla + variantes → para elegir *sin cambiar el precio*

**Pollo a la Brasa 1/4** es una plantilla (`Has Variants`) con dos variantes que se
distinguen por el atributo **Corte**: Pecho y Pierna. Las dos cuestan 12.00.

Por qué así y no dos ítems sueltos: en la grilla aparece **una sola tarjeta** ("Pollo a la
Brasa 1/4", con la etiqueta *Options*), y al tocarla se abre el selector de variante. Una
carta con veinte platos no se llena de tarjetas casi idénticas, y el cajero elige la presa
en el mismo gesto con el que elige el plato. Además cada presa queda registrada como su
propio ítem en la factura, así que sabes cuántas piernas y cuántos pechos vendiste.

**Regla que no se puede saltar: el precio va en la variante, no en la plantilla.** Las
plantillas no se venden, se resuelven. Si le pones precio a la plantilla y no a las
variantes, la tarjeta muestra "Select" y la línea entra en 0.00. Hoy tienes bien:
`DEMO-POLLO-14` sin Item Price, y `-PECHO` / `-PIERNA` a 12.00 cada una.

Consecuencia útil: **las variantes sueltas nunca aparecen en la grilla**. El POS lista
plantillas y las variantes solo se alcanzan por el selector — no hay riesgo de que el
cajero vea "Pollo 1/4 - Pecho" flotando por su cuenta.

### 3.3 Subgrupo → para separar *lo que sí cambia de precio*

1/4, 1/2 y entero no son variantes: cuestan 12, 22 y 40. Ahí sí conviene un ítem propio…
y un **subgrupo propio** debajo de `Pollo a la Brasa`. Eso te da:

- Una pestaña por porción en el POS, para llegar a la porción en un toque.
- Un grupo padre (`Pollo a la Brasa`) que sirve para pedir "cualquier pollo" de una sola
  referencia, sobre todo en un slot de combo con *Include Child Groups*.

**Ojo con esto**: el filtro de categorías solo muestra grupos hoja, así que
`Pollo a la Brasa` **no aparece como pestaña** — solo sus tres hijos. El grupo padre existe
para agrupar, no para navegar.

### 3.4 Resumen de la decisión

| La diferencia entre dos platos… | Modelar como |
|---|---|
| …cambia el precio | Ítems distintos (y subgrupo propio si quieres pestaña) |
| …no cambia el precio pero hay que registrarla | Variantes de una plantilla |
| …no cambia el precio ni hace falta registrarla como venta | Modificador (§6) |

Pierna vs pecho: mismo precio, pero quieres saber cuánto sale de cada una → **variante**.
"Sin cebolla": mismo precio y no es una venta distinta → **modificador**.

---

## 4. Dar de alta un plato nuevo

### Plato simple

1. **Item → New**: `Item Code`, `Item Name`, `Item Group` (el que corresponda).
2. `Maintain Stock` **desmarcado** si es un plato preparado. Con stock marcado, el plato
   desaparece de la grilla cuando el inventario llega a cero, si el POS Profile valida
   existencias. Para una cocina eso es un dolor de cabeza: los platos preparados no se
   inventarían, se controlan con el menú del día.
3. **Item Price**: en la lista de precios del POS Profile — en tu sitio, `Venta estándar`.
   Sin precio ahí, el ítem entra en 0.00.

### Plato con presas / opciones sin costo (plantilla + variantes)

1. **Item Attribute**: crea el atributo si no existe con sus valores (ya tienes `Corte`
   con Pecho, Pierna, Contra+Ala, Pierna+Pecho).
2. **Item plantilla**: marca `Has Variants` y agrega el atributo en la tabla de atributos.
   No le pongas precio.
3. **Variantes**: desde la plantilla, *Create → Variant*, una por valor del atributo.
4. **Item Price a cada variante**. Si todas cuestan igual, igual hay que cargarlo en cada
   una.

Todas las variantes heredan el `Item Group` de la plantilla, así que la porción queda
definida por dónde pusiste la plantilla.

### Porción nueva (ej. Pollo 3/4)

1. **Item Group → New**: nombre `Pollo 3/4`, padre `Pollo a la Brasa`, `Is Group`
   desmarcado.
2. El ítem (simple o plantilla) dentro de ese grupo.
3. Aparece sola la pestaña nueva en el POS; los combos que apunten a `Pollo a la Brasa` con
   subgrupos incluidos la aceptan sin tocar nada.

---

## 5. Combos

Un combo **no es un ítem**: es una plantilla de armado. No se le crea Item ni Item Price, y
no aparece en ningún Item Group. Vive en su propio doctype (`Restaurant Combo`) y en el POS
se muestra como tarjeta ámbar al principio de la grilla.

Lo que se factura son **los componentes**, uno por slot, cada uno con su parte del precio
del combo (ver el detalle de los tres métodos de reparto en la
[guía del módulo](restaurant-module.md#221-métodos-de-reparto-del-precio)).

### Cómo se conecta un slot con el catálogo

Cada slot apunta a un Item Group. Eso es todo el vínculo: **lo que esté en ese grupo es
elegible**, y lo que agregues mañana al grupo se vuelve elegible solo.

Tu combo **Completo** (15.00):

| Slot | Item Group | Incluye subgrupos | Por defecto |
|---|---|---|---|
| Sopa | Sopas | sí | Sopa de Maní |
| Segundo | Segundos | sí | Milanesa de Pollo |
| Refresco | Refrescos | sí | Mocochinchi |

### Un combo con pollo

Aquí se ve para qué sirve el grupo padre. Si quisieras un "Combo Pollo" que incluya
cualquier porción:

| Slot | Item Group | Incluye subgrupos |
|---|---|---|
| Pollo | `Pollo a la Brasa` | **sí** |
| Refresco | `Refrescos` | sí |

Con *Include Child Groups* activado, ese único slot acepta 1/4, 1/2 y entero. Si en cambio
quieres un combo solo de cuartos, apuntas el slot a `Pollo 1/4` sin subgrupos.

Las plantillas dentro de un slot funcionan igual que en la grilla: el armador te deja
elegir la variante concreta.

> **Cuidado con los precios dispares dentro de un slot.** Si un slot acepta 1/4 (12.00) y
> entero (40.00) al mismo precio de combo, el reparto le imputará valores muy distintos a
> cada componente según lo que elija el cliente, y el margen del combo cambia por completo.
> Si la porción cambia el precio de venta, casi siempre conviene un combo por porción en
> vez de un slot que las mezcle.

---

## 6. Modificadores: la tercera capa

Para diferencias que **no cambian el precio ni hace falta contarlas como venta**: "sin
cebolla", "sin sal", "sin picante". No son ítems ni variantes; son etiquetas que viajan a
la comanda.

Tu grupo **Sin ingredientes** está en `Apply to All Items`, así que el botón aparece en
toda línea. También se puede acotar por Item Groups o por ítems concretos: por ejemplo un
grupo "Término de cocción" aplicado solo al grupo `Segundos`.

---

## 7. Menú del día y grupos

Los grupos marcados en Restaurant Settings → Daily Menu obligan a elegir sus platos al
abrir el turno. Hoy son **Sopas, Segundos y Refrescos**.

`Pollo a la Brasa` y sus subgrupos **no** están ahí, o sea que el pollo está siempre
disponible sin marcar nada — que es lo correcto para un producto de carta fija. Es
exactamente la decisión que hay que tomar por cada grupo nuevo: ¿cambia todos los días o
está siempre?

---

## 8. Checklist y errores comunes

Al crear un plato:

- [ ] `Item Group` correcto (el grupo por el que lo vas a *elegir*)
- [ ] `Item Price` en `Venta estándar` — en la **variante** si es plantilla
- [ ] `Maintain Stock` desmarcado si es preparado
- [ ] ¿Va en algún slot de combo? Entonces tiene que estar en el grupo de ese slot
- [ ] ¿Su grupo está en el menú del día? Entonces hay que marcarlo cada mañana

| Síntoma | Causa |
|---|---|
| El plato entra al carrito en 0.00 | Falta Item Price en la lista del POS Profile, o el precio está en la plantilla en vez de la variante |
| La tarjeta dice "Select" y no agrega nada | Es una plantilla: es el comportamiento esperado, abre el selector de variante |
| El plato no aparece en la grilla | Está en un grupo de menú del día sin marcar; o tiene stock en 0 con validación de existencias activa; o es una variante (solo se ve la plantilla) |
| El grupo no aparece como pestaña | Es un grupo padre (`Is Group` marcado). Solo se listan grupos hoja |
| El plato no aparece en el armador del combo | No está en el Item Group del slot, o el slot no incluye subgrupos |
| Las presas no se distinguen en los reportes | Se modelaron como modificador en vez de variante |

---

## 9. Pendiente de limpieza en tu sitio

Detectado al revisar el catálogo, para que no te sorprenda:

- **Combo "Completo TEST"**: sus tres slots apuntan al grupo `Productos` (abarrotes), o sea
  que el armador ofrece aceite y arroz como sopa. Quedó de las pruebas automatizadas.
- **Grupo de modificadores "Sin ingredientes TEST"**: aplicado a todos los ítems, duplica
  el botón de modificadores.

Ambos aparecen hoy en el POS de producción. Si no los usas, márcalos como `Disabled` en vez
de borrarlos: los pedidos viejos que los referencian se quedan sin su nombre si desaparecen.
