# Módulo Restaurante — Guía de uso

Extensión de POS Prime para restaurantes y pensiones: consumo en mesa o para llevar por
línea, notas de cocina, modificadores gratuitos, combos de precio fijo, impresión de
comanda y recibo por ESC/POS, platos del día y reportes por combo.

Todo el módulo está detrás de un interruptor y viene **apagado**. Con `Enable Restaurant
Mode` en off, POS Prime se comporta exactamente como el POS normal: ni un botón de más.

> Las etiquetas entre comillas son las que verás en el Desk de ERPNext, que está en inglés.
> Los valores de los campos (Mesa, Para llevar, Margen alto…) sí están en español.

Para cómo se organiza el catálogo detrás de todo esto — grupos de artículos, variantes de
un plato, qué modelar como ítem, variante o modificador — ver
**[Cómo se modelan los productos](catalogo-productos-y-combos.md)**.

---

## 1. Activar el módulo

**Desk → Restaurant Settings** (buscador: `restaurant settings`) → marcar
`Enable Restaurant Mode` → Guardar.

Recarga el POS. A partir de ahí aparecen el selector de destino, las notas, los
modificadores y las tarjetas de combo.

---

## 2. Configuración

### 2.1 Restaurant Settings

Un solo formulario, dividido en secciones:

| Sección | Campo | Para qué sirve |
|---|---|---|
| — | `Enable Restaurant Mode` | Interruptor general del módulo. |
| — | `Default Destination` | Destino con el que nacen las líneas nuevas: Mesa o Para llevar. |
| — | `Combo Strip Label` | Nombre visible del grupo de combos. |
| Cart Options | `Disable Coupon Code` | Oculta el campo de cupón en el carrito. |
| Cart Options | `Disable More Options` | Oculta la sección "More Options" del carrito. |
| Cart Options | `Hide Category Search` | Oculta el buscador sobre la lista de categorías. Viene activado. |
| Combo Pricing | `Default Combo Pricing Method` | Método de reparto por defecto para todos los combos (§2.2). |
| Daily Menu | `Item Groups Requiring Daily Selection` | Grupos cuyos platos hay que habilitar cada día (§2.4). |
| Kitchen Ticket | `Print Kitchen Ticket on Payment` | Imprime la comanda apenas se cobra. |
| Kitchen Ticket | `Print in Background` | Encola la impresión (requiere worker RQ). Apágalo solo en benches de desarrollo sin worker. |
| Kitchen Ticket | `Never Block Checkout on a Printer Failure` | Si la impresora no responde, la venta se completa igual y el ticket queda en `Failed`. |
| Kitchen Ticket | `Dine-in Label` / `Takeaway Label` | Texto de los encabezados del ticket (MESA / PARA LLEVAR). También se usa en las etiquetas del carrito. |
| Kitchen Ticket Content | `Show Order Number` / `Show Time` / `Show Customer` / `Show Modifiers` | Qué aparece en la comanda. Las notas de cocina siempre se imprimen. |
| Recibo de Caja | `Print Receipt on Payment` | Imprime el recibo apenas se cobra. |
| Recibo de Caja | `Receipt Footer` | Última línea del recibo. |
| Receipt Content | `Show Invoice Number and Date` / `Show Customer` / `Show Tax Breakdown` / `Show Payments and Change` | Qué aparece en el recibo. El total siempre se imprime. |

### 2.2 Combos

**Desk → Restaurant Combo → New.**

| Campo | Notas |
|---|---|
| `Combo Name` | Identifica el combo, tiene que ser único. |
| `Company` / `Combo Price` | Precio fijo que paga el cliente por el combo completo. |
| `Pricing Method` | Vacío = hereda el default de Restaurant Settings. |
| `Allow a Negative Component Price` | Solo para Margen alto (ver abajo). |
| `Print Label` | Nombre corto para tickets y para la línea agrupada del recibo, ej. `COMPLETO`. |
| `Sort Order` / `Image` / `Description` | Orden y aspecto de la tarjeta en el POS. |
| `Slots` | Una fila por componente que el cajero debe elegir. |

Cada fila de `Slots`:

| Campo | Notas |
|---|---|
| `Slot Label` | Lo que ve el cajero: Sopa, Segundo, Refresco. |
| `Item Group` | De qué grupo puede elegir ese slot. |
| `Include Child Groups` | Incluye subgrupos del anterior. |
| `Default Item` | Preselección al abrir el armador. |
| `Allow Modifiers` | Permite modificadores en ese componente. |
| `Discount Order` | Quién absorbe el descuento y en qué orden (§2.2.1). |

#### 2.2.1 Métodos de reparto del precio

Un combo se vende a precio fijo, pero cada componente entra a la factura como su propia
línea. El método decide cuánto se le imputa a cada plato. **Siempre suma exactamente el
precio del combo**, al centavo.

Ejemplo con Sopa 6.00, Segundo 12.00, Refresco 2.00 (suma 20.00) y combo a 15.00:

| Método | Configuración | Sopa | Segundo | Refresco |
|---|---|---|---|---|
| **Proporcional** | ninguna | 4.50 | 9.00 | 1.50 |
| **Margen alto** | Refresco `Discount Order = 1`, `Allow Negative` ✔ | 6.00 | 12.00 | **-3.00** |
| **Margen alto** | Refresco `1`, Sopa `2`, sin negativos | 3.00 | 12.00 | 0.00 |
| **Mixto** | Sopa `1`, Refresco `2`, Segundo protegido (`0`) | 2.25 | 12.00 | 0.75 |

- **Proporcional**: baja todos los precios el mismo porcentaje (aquí ×0.75). Cada plato
  conserva su peso relativo en tus números de cocina.
- **Margen alto**: los platos mantienen su precio de lista y el descuento sale de los slots
  con `Discount Order`, en ese orden. Cada uno cede hasta llegar a 0.00 y el resto pasa al
  siguiente. Con `Allow a Negative Component Price` el último absorbedor se queda con todo
  el descuento aunque quede negativo, lo que contablemente registra la pérdida en esa
  bebida en vez de repartirla.
- **Mixto**: los slots con `Discount Order = 0` quedan protegidos en su precio de lista, y
  lo que resta del precio del combo se reparte proporcional entre los que sí absorben.

`Discount Order = 0` significa "protegido": ese slot solo cede algo si los absorbedores no
alcanzaron a cubrir todo el descuento.

Al guardar se rechaza la configuración incoherente: Margen alto o Mixto sin ningún slot
absorbedor, y dos slots con el mismo `Discount Order` (el orden de cascada sería ambiguo).

El cálculo es del servidor y es la autoridad: el POS solo pide una vista previa, y al
cobrar se recalcula desde cero ignorando cualquier tarifa que haya mandado el cliente.

### 2.3 Modificadores

Son variantes **sin costo** ("sin cebolla", "poco picante"), no ítems vendibles.

1. **Restaurant Modifier**: uno por variante. `Modifier Name` y, opcionalmente,
   `Print Label` (lo que sale en la comanda, normalmente en mayúsculas y corto).
2. **Restaurant Modifier Group**: agrupa modificadores y define a qué se aplican.
   - `Selection Type`: `Multiple` (varias a la vez) o `Single` (una sola).
   - `Modifiers`: las opciones del grupo, con `is_default` para las que vienen marcadas.
   - Alcance: `Apply to All Items`, o bien listas de `Item Groups` y/o `Items`.

En el POS el botón de modificadores solo aparece en las líneas que tengan al menos un
grupo aplicable.

### 2.4 Platos del día

Para cartas que cambian a diario: en vez de deshabilitar ítems a mano, se eligen al abrir
el turno.

1. En Restaurant Settings → Daily Menu, agrega los grupos que cambian todos los días
   (ej. Sopas, Segundos, Refrescos) en `Item Groups Requiring Daily Selection`.
2. Al abrir turno, el cajero ve un selector con los platos de esos grupos y marca los que
   hay hoy.
3. Durante el turno, los platos no marcados **no aparecen** en la grilla ni se pueden
   escanear ni vender desde el autoservicio.

Los grupos que no estén listados ahí no se ven afectados: siguen disponibles siempre. Si no
configuras ningún grupo, el selector no aparece y la apertura de turno es la de siempre.

### 2.5 Impresoras

**Desk → Restaurant Printer → New.** Sin al menos un registro aquí no hay impresión
automática: los tickets quedan en `Not Required` y solo queda el botón manual del POS.

| Campo | Notas |
|---|---|
| `Printer Name` | Identificador libre. |
| `POS Profile` | En blanco = sirve para todos los perfiles. |
| `Printer Role` | `Comanda (Cocina)` imprime desde el pedido; `Recibo (Caja)` imprime desde la factura. **Una impresora por rol**: si la misma máquina física hace ambas cosas, crea dos registros con el mismo host. |
| `Print Destinations` | Solo para cocina: `All`, `Mesa Only` o `Para llevar Only`. Permite una impresora por estación. |
| `Delivery Mode` | `TCP Directo`: Frappe abre el socket a la impresora (requiere estar en la misma red). `Puente Android`: el ticket se publica en tiempo real a un teléfono que lo retransmite en la red local, para cuando Frappe está en la nube. |
| `Bridge User` | Solo en modo puente: el usuario de Frappe con el que se loguea el teléfono. Uno por dispositivo. |
| `Host` / `Port` | Dirección de la impresora en su red local (puerto 9100 en la mayoría). |
| `Timeout (seconds)` / `Copies` | Espera de conexión y número de copias. |
| `Print Format (Raw)` | Opcional: plantilla del ticket (§2.6). Vacío = diseño interno. |
| `Codepage` / `ESC/POS Codepage ID Override` | CP850 funciona en casi todas. Si los acentos salen mal, prueba otra. |
| `Characters per Line` | 32 para papel de 58 mm, 48 para 80 mm. |
| `Cut Paper After Printing` / `Pulse Cash Drawer` | Corte y apertura de cajón. |

> **Ojo con Puente Android**: es de ida y sin confirmación. El estado `Printed` significa
> "el trabajo se envió al teléfono", no "salió el papel". Si la app puente no está
> corriendo con ese usuario, el ticket se pierde en silencio. Con `TCP Directo` al menos te
> enteras cuando no se pudo conectar con la impresora.

#### Qué prueba (y qué no) cada modo

Ninguno de los dos confirma que salió el papel. Una impresora térmica en el puerto 9100
nunca contesta: solo recibe. Con `TCP Directo`, que el envío no falle significa que la
impresora aceptó los bytes — sin papel, con la tapa abierta o atascada, el ticket igual
queda en `Printed`. Lo que sí detecta ese modo es el fallo de conexión: IP equivocada,
equipo apagado, puerto cerrado o timeout.

#### Seguridad de la conexión

**El puerto 9100 no tiene autenticación de ningún tipo**: ni usuario, ni contraseña, ni
cifrado. Es parte del protocolo RAW, no una omisión de esta app. Cualquiera que alcance esa
IP y ese puerto en la red puede imprimir en tu cocina. La protección es la red, no el
protocolo:

- **Nunca abras el 9100 a internet** ni le hagas port-forward en el router. Si Frappe está
  en la nube, usa `Puente Android` en vez de exponer la impresora: para eso existe.
- Ponle IP fija a la impresora (una IP que cambie por DHCP rompe la impresión) y, si
  puedes, déjala en una red separada de la de los clientes.

El tramo del puente sí va autenticado y cifrado: viaja por el canal de tiempo real de
Frappe (`wss://`), acotado a las sesiones del `Bridge User`. El tramo sin autenticar es el
último, teléfono → impresora, igual que en TCP Directo.

### 2.6 Formatos de ticket editables

El diseño de los tickets se puede sacar de Python y editar desde el Desk. La app siembra
dos formatos listos, no estándar (o sea, editables):

| Print Format | Doc Type | Rol de impresora |
|---|---|---|
| `POS Prime Comanda (ESC/POS)` | Restaurant Order | Comanda (Cocina) |
| `POS Prime Recibo (ESC/POS)` | POS Invoice | Recibo (Caja) |

Para usarlos: en la impresora, campo `Print Format (Raw)`, elige el que corresponde a su
rol. Reproducen el diseño interno, así que al conectarlos no cambia nada hasta que los
edites en **Print Format → (el formato) → Raw Commands**.

La plantilla manda el contenido; la impresora sigue mandando el marco: la inicialización y
el codepage se emiten antes, y el avance, corte, cajón y copias después. Variables y
ayudantes disponibles:

| | |
|---|---|
| Alineación | `{{ CENTER }}` `{{ LEFT }}` `{{ RIGHT }}` |
| Énfasis | `{{ BOLD }}…{{ NOBOLD }}`, `{{ BIG }}…{{ NOBIG }}` |
| Layout | `{{ sep() }}` línea completa, `{{ row('izq', 'der') }}` línea con importe a la derecha |
| Formato | `{{ money(valor) }}`, `{{ qty(cantidad) }}` |
| Ajustes | `{{ shows('receipt_show_taxes') }}` respeta los checks de Restaurant Settings |
| Datos (recibo) | `invoice`, `lines`, `posting_datetime`, `settings`, `printer` |
| Datos (comanda) | `order`, `blocks` (destino → combos → sueltos), `customer_name`, `now` |

`lines` es la lista del recibo con **cada combo colapsado en una sola fila** (`label`, `qty`,
`amount`, `is_combo`, `components`), que es lo que hace que el cliente vea "1x COMPLETO
15.00" en vez de los tres componentes con su precio repartido. Para facturar los
componentes por separado, recorre `invoice.items` en vez de `lines`.

Ejemplo de la sección de ítems del recibo:

```jinja
{% for line in lines %}{{ row(qty(line.qty) ~ 'x ' ~ line.label, money(line.amount)) }}
{% if line.is_combo %}{% for component in line.components %}   - {{ component.item_name }}
{% endfor %}{% endif %}{% endfor %}
```

Si una plantilla tiene un error, ese ticket queda en `Failed` y **la venta no se ve
afectada nunca**. Para volver al diseño de fábrica, borra el Print Format y corre
`bench --site TU-SITIO migrate`: se vuelve a sembrar.

---

## 3. Uso diario en el POS

### 3.1 Abrir el turno

Ruta normal de POS Prime. Si configuraste platos del día, aparece el selector: marca lo que
hay hoy y abre el turno. Esa elección queda guardada en el POS Opening Entry y rige todo el
turno.

### 3.2 Destino: Mesa o Para llevar

- **Global**: el interruptor MESA / PARA LLEVAR sobre el carrito (o **F7**) fija el destino
  con el que nacen las líneas nuevas. Al iniciar sesión arranca en el `Default Destination`
  de Restaurant Settings.
- **Por línea**: la etiqueta MESA / PARA LLEVAR de cada línea del carrito se toca para
  cambiar solo esa. Un pedido puede tener platos para mesa y otros para llevar.
- En un combo, el destino es de toda la instancia, no de cada componente.

El destino agrupa la comanda por estación y alimenta el reporte Ventas por Destino.

### 3.3 Notas y modificadores

- **Nota**: la etiqueta "Note" de la línea abre un cuadro de texto libre ("sin sal", "para
  llevar en dos bolsas"). Sale siempre en la comanda.
- **Modificadores**: botón de la línea, si hay algún grupo aplicable al ítem. No cambian el
  precio.
- Los combos tienen además una nota de instancia, que aplica al conjunto.

### 3.4 Vender un combo

1. Los combos aparecen como tarjetas al principio de la grilla, con borde ámbar y la
   etiqueta "Combo". Se buscan por nombre desde el mismo buscador de ítems.
2. Al tocar uno se abre el armador: eliges un ítem por slot y, si el slot lo permite, sus
   notas y modificadores.
3. Al confirmar entran al carrito los componentes agrupados bajo el nombre del combo, con
   el precio ya repartido por el servidor.
4. Si vuelves a armar un combo idéntico (mismo destino, mismas elecciones, misma nota), en
   vez de duplicar el grupo sube la cantidad del que ya está.
5. Las cantidades y tarifas de un componente no se editan a mano: las fija el reparto y se
   recalculan al cobrar.

Las tarjetas de combo solo se muestran con el filtro de categorías en "All Item Groups": un
combo no pertenece a ningún grupo de ítems.

### 3.5 Cobrar

Al cobrar, en una sola operación se crean y envían la POS Invoice y su Restaurant Order
enlazado. Si algo falla, no queda ni media venta grabada.

Ya cobrado y confirmado, se lanza la impresión: comanda a las impresoras de cocina que
correspondan al destino, y recibo a las de caja. La impresión ocurre **después** de que la
venta se guardó, así que una impresora caída jamás revierte ni bloquea un cobro.

### 3.6 Atajos de teclado

| Tecla | Acción |
|---|---|
| F1 | Buscar ítems |
| F2 | Pedidos en espera |
| F3 / F9 | Cobrar |
| F4 | Mantener pedido |
| F5 | Ver pedidos |
| F7 | Alternar destino Mesa / Para llevar |
| F8 | Pedido nuevo |
| F10 | Devolución |
| Esc | Cerrar el cuadro abierto |

---

## 4. Reportes

Todos en **Desk → buscador del reporte**, y todos leen Restaurant Order confirmados
(no Sales Invoice: la consolidación del cierre de caja no arrastra los campos por línea que
necesita un combo).

| Reporte | Responde |
|---|---|
| **Combos Vendidos** | Cuántos combos se vendieron y por cuánto. |
| **Componentes de Combos** | Qué platos salieron dentro de combos. |
| **Combinaciones de Completos** | Qué combinaciones de slots elige la gente. |
| **Ventas Suelto vs Combo** | Cuánto se vende cada plato suelto y cuánto dentro de un combo. |
| **Ventas por Destino** | Mesa contra para llevar. |

---

## 5. Impresión: estados y reimpresión

En cada Restaurant Order, `Comanda Status`:

| Estado | Significa |
|---|---|
| `Not Printed` | Todavía no se intentó. |
| `Printed` | Enviado sin error. En modo puente significa "entregado al teléfono", no confirmación de papel. |
| `Failed` | Alguna impresora falló. El detalle queda en `Comanda Error`. |
| `Not Required` | Ninguna impresora habilitada correspondía. Casi siempre: falta crear el registro de la impresora, o su `Print Destinations` excluía los destinos del pedido. |

La factura tiene su equivalente en `pos_prime_receipt_status`.

Para reimprimir sin volver a cobrar:

```bash
bench --site TU-SITIO execute pos_prime.api.restaurant.reprint_comanda --kwargs "{'restaurant_order': 'RO-2026-00023'}"
bench --site TU-SITIO execute pos_prime.api.restaurant.reprint_receipt --kwargs "{'pos_invoice': 'ACC-PSINV-2026-00029'}"
```

Para probar una impresora recién configurada existe `pos_prime.api.restaurant.test_printer`,
que imprime una hoja de prueba y **sí levanta el error en pantalla** si no conecta.

---

## 6. Problemas frecuentes

| Síntoma | Causa habitual |
|---|---|
| No aparece nada del módulo en el POS | `Enable Restaurant Mode` apagado, o falta recargar el POS. |
| El ticket queda en `Not Required` | No hay `Restaurant Printer` habilitada con ese rol y ese POS Profile. |
| Dice `Printed` pero no sale papel | Modo `Puente Android` sin la app corriendo con el `Bridge User`; o la impresora recibió el trabajo pero está sin papel, atascada o con la tapa abierta (eso no lo reporta ninguno de los dos modos). |
| Los acentos salen como símbolos | Codepage equivocado en la impresora. Empieza por CP850. |
| El ticket sale cortado a lo ancho | `Characters per Line` mal: 32 para 58 mm, 48 para 80 mm. |
| Un plato no aparece en la grilla | Está en un grupo de menú del día y no se marcó al abrir el turno. |
| El combo no se deja guardar | Margen alto o Mixto sin ningún slot con `Discount Order`, o dos slots con el mismo número. |
| El combo no aparece en la grilla | Hay un filtro de categoría activo: los combos solo se listan en "All Item Groups". |

---

## 7. Datos de demostración

Para probar el módulo con una carta chica ya armada (sopas, segundos, refrescos, un combo
"Completo" y sus grupos registrados como menú del día):

```bash
bench --site TU-SITIO execute pos_prime.restaurant.setup.setup_demo_menu \
  --kwargs "{'company': 'Tu Empresa', 'pos_profile': 'Tu Perfil'}"
```

Es idempotente: se puede correr varias veces sin duplicar nada.
