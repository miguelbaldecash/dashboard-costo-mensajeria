# Dashboard de Drivers de Gasto — Mensajeria y Voz

**BaldeCash** | Periodo: Enero - Mayo 2026 | USD + PEN

> [Ver Dashboard](https://miguelbaldecash.github.io/dashboard-costo-mensajeria/) | [Ver Manual](https://miguelbaldecash.github.io/dashboard-costo-mensajeria/manual.html)

---

## Que es este reporte

Analiza el gasto en comunicaciones de BaldeCash desglosado por proveedor, uso de negocio y destinatario. Responde a preguntas como:

- Cuanto cuesta cobrar a un cliente en mora?
- Cuanto cuesta cada solicitud aprobada?
- Cuanto cuesta cada firma de retargeting?
- Estamos pagando de mas?

## Plataformas incluidas

| Plataforma | Canal | Moneda |
|---|---|---|
| **Blip** | WhatsApp + chatbot | USD |
| **Botmaker** | WhatsApp (pausada desde mar 2026) | USD |
| **Voximplant** | Llamadas PSTN + WhatsApp HSM | USD |
| **GoHighLevel** | Email cobranzas | USD |
| **Mailgun** | Email transaccional | USD |
| **Kontactus** | Llamadas dialer predictivo | PEN |
| **Labs Mobile** | SMS cobranzas | PEN |

## Secciones del reporte

### Tablas resumen
- **Volumen por plataforma** — mensajes/llamadas/emails por mes
- **Gasto por plataforma** — costo facturado por mes de actividad
- **Graficos de barras** — volumen y gasto visual

### Seccion 1: Facturado por concepto
Desglose exacto de cada linea de factura por proveedor. Incluye:
- Blip: 5 lineas (MAUS, Automated Conv, WA MKT, WA UTIL, WA AUTH)
- Tabla de conversaciones vs mensajes (ratio msgs/conv)
- Tabla de costo por tipo Meta (MARKETING vs UTILITY vs AUTH)
- Botmaker: desglose completo de factura (plan, usuarios, WA fees, AI tokens)
- Voximplant: consumo real vs recargas

### Seccion 2: Costo por uso de negocio
**La seccion clave.** Reclasifica el gasto por funcion:
- **FIJOS** — MAUS $600, planes, suscripciones
- **Cobranza mora** — costo plataforma + fee Meta + Botmaker + Voximplant + GHL
  - Driver: **costo / moroso gestionado** (moroso_historico)
- **Cobranza preventiva** — preventivos + recordatorios
- **Comercial** — retargeting + entrega + otros
  - Driver: **costo / firma retargeting**
- **Preadmision** — confirmaciones + firma contrato + verificacion
  - Driver: **costo / solicitud**
- **Inbound** — costos plataforma (fee Meta = $0)
- **Reconciliacion** — verifica que todo suma = factura

### Seccion 3: Volumen global
Tabla consolidada por area de negocio y por plataforma con graficos stacked bar.

### Seccion 4: Desglose por grupo de campanas
Cada plantilla/campana con volumen Y costo por mes. Verificacion contra factura incluida.

### Seccion 5: Intensidad de envio por numero
Distribucion de mensajes por telefono. Muestra concentracion: ~15% de los telefonos generan ~55% de los mensajes.

### Seccion 6: Detalle por numero de celular (interactiva)
34,955 numeros con mensajes y costo por mes. Filtro por mes, busqueda por numero. Marca numeros de prueba en rojo.

### Seccion 7: Detalle por plantilla WhatsApp (interactiva)
207 plantillas de 3 proveedores. Filtros: mes, area, tipo Meta, proveedor. Click en una fila expande los numeros destino. Boton "Ver" muestra el contenido del mensaje.

### Seccion 8: Llamadas Voximplant por numero (interactiva)
Llamadas salientes PSTN por numero destino con costo estimado.

### Seccion 9: Ficha por plantilla
Tabla resumen con filtros (area, tipo Meta, proveedor) mostrando mensajes y porcentajes por periodo. Incluye detalle por plantilla individual.

### Seccion 10: Cobranza por dias de atraso
Mensajes por tramo de mora (-4 a 30 dpd) con filtro de mes. Dias negativos = preventivos.

## Metodologia

### Asignacion de costos
- Las facturas se asignan al **mes de actividad**, no al de emision (1 mes de desfase para Blip y Botmaker)
- **MAUS $600** queda en FIJOS, no se distribuye a los grupos
- **Automated Conv** se distribuye proporcionalmente por `phone x day` de cada area
- **Conversaciones MKT** de la factura se distribuyen proporcionalmente por `phone x day`
- **UTIL y AUTH** se asignan directo a preadmision
- Suma de todos los grupos + MAUS = factura Blip exacta (diff < $2)

### Tarifas Meta Peru
| Tipo | Tarifa/conversacion | Uso |
|---|---|---|
| MARKETING | $0.0803 | Cobranza, campanas, retargeting (95% de plantillas) |
| UTILITY | $0.03 | Locker truck, school rental, baldeverify |
| AUTHENTICATION | $0.03 | whatsapp_code_validation |
| SERVICE | $0 (gratis) | Respuestas inbound dentro de 24hrs |

### Denominadores
| Denominador | Fuente | Para que |
|---|---|---|
| Morosos gestionados | `moroso_historico` solicitudes unicas | Costo / moroso (cobranza) |
| Solicitudes | `solicitud` por created_at | Costo / solicitud (preadmision) |
| Firmas retargeting | `solicitud.status='aprobado'` con source retargeting | Costo / firma (comercial) |

### Verificaciones
- Lineas de factura suman = total factura (**diff = $0**)
- MAUS + grupos Seccion 2 = factura Blip (**diff < $2**)
- Msgs por area = total DB (**diff = 0**)
- Campanas x costo blended = factura (**diff < $7**)
- Phone data = DB (**diff = 0**)
- Template data = DB (**diff = 0**)

## Archivos

| Archivo | Descripcion | Tamano |
|---|---|---|
| `index.html` | Dashboard principal (drivers-de-costo) | 179 KB |
| `manual.html` | Manual de interpretacion | 37 KB |
| `phone_inline.js` | 34,955 numeros con msgs/costo por mes | 1.6 MB |
| `template_data.js` | 207 plantillas con volumen y categoria Meta | 18 KB |
| `template_phones.js` | Plantilla x telefono x mes | 5.3 MB |
| `template_contents.js` | Contenido de 480 plantillas | 188 KB |
| `template_totals.js` | Totales mensuales por area/meta | 1 KB |
| `calls_data.js` | Llamadas Voximplant por numero | 644 KB |
| `dias_atraso_data.js` | Cobranza por tramo de mora | 2 KB |

## Fuentes de datos

- **Blip API** — plantillas, categorias Meta, contenido
- **Blip DB** (`blip_whatsapp_logs`) — templates enviados por telefono
- **Voximplant Kit API** — campanas, llamadas por numero
- **Voximplant DB** (`voximplant_whatsapp_logs`) — WA HSM enviados
- **Botmaker DB** (`botmaker_logs`) — logs de cobranza
- **Botmaker Dashboard** — sesiones, usuarios
- **GoHighLevel Dashboard** — emails, open rate
- **Mailgun Dashboard** — emails enviados
- **Kontactus PDFs** — CDR de llamadas
- **Labs Mobile PDFs** — SMS enviados
- **Facturas** — Blip (INV/2026), Botmaker (DCINC), Voximplant (receipts), GHL, Mailgun, Kontactus, Labs Mobile
- **DB** (`moroso_historico`, `cartera_historico`, `solicitud`) — denominadores

## Como usar

1. Abrir `index.html` en un navegador (o visitar GitHub Pages)
2. Las secciones 1-5 son tablas estaticas — hacer scroll
3. Las secciones 6-10 son interactivas — usar filtros, dropdown y busqueda
4. En Seccion 7, click en una plantilla expande los numeros destino
5. En Seccion 7, boton "Ver" muestra el contenido del mensaje WA

## Limitaciones

- Mayo sin factura Blip (costo = $0)
- Voximplant ene/feb = recargas, no consumo real
- Kontactus ene/feb = estimados
- Clasificacion de templates es automatica por nombre (5-9% sin clasificar)
- Botmaker ene/feb: diferencia entre dashboard (28,302) y DB (28,090) por sesiones sin template HSM
- Llamadas Voximplant pueden tener ~10% faltante por rate limiting de API
- Seccion 10 (dias atraso): ene/feb faltan ~212/~4,803 msgs de gestores Botmaker sin tramo identificable

---

*Generado: Junio 2026 | Balde K S.A.C.*
