# Entregable 3 — Historias de Usuario

Formato: `Como [Rol] / Quiero [Acción] / Para [Beneficio]`, con criterios de
aceptación verificables en formato **Dado / Cuando / Entonces**.

Prioridad: **A** (imprescindible) · **M** (media) · **B** (deseable).

---

# ÉPICA 1 — GESTIÓN DE INCAPACIDADES

## HU-I-01 · Registrar una incapacidad — **A**

> **Como** acudiente de un estudiante
> **Quiero** registrar la incapacidad médica de mi hijo y adjuntar el certificado
> **Para** que sus ausencias queden justificadas sin tener que ir al colegio

**Criterios de aceptación**

1. **Dado** que tengo sesión iniciada, **cuando** abro *Incapacidades → Nueva*,
   **entonces** veo el formulario con estudiante, tipo, fechas, entidad emisora y soportes.
2. **Dado** que diligencio los campos obligatorios y adjunto un PDF válido,
   **cuando** guardo, **entonces** la incapacidad queda en `PENDIENTE` y recibo confirmación.
3. **Dado** que la fecha final es anterior a la inicial, **cuando** guardo,
   **entonces** el sistema **no** guarda y señala el campo `end_date`.
4. **Dado** que el tipo exige soporte y no adjunto ninguno, **cuando** guardo,
   **entonces** se indica que el soporte es obligatorio.
5. **Dado** que adjunto un archivo `.exe` o mayor a 10 MB, **cuando** guardo,
   **entonces** se rechaza indicando extensión o tamaño no permitidos.
6. **Dado** que el estudiante ya tiene una incapacidad vigente traslapada,
   **cuando** guardo, **entonces** se muestra la existente y se ofrece prorrogarla.
7. La operación queda registrada en la bitácora con mi usuario, fecha e IP.

## HU-I-02 · Verificar el soporte — **A**

> **Como** secretaria
> **Quiero** verificar el soporte médico antes de que se apruebe
> **Para** evitar que se justifiquen ausencias con documentos inválidos

1. **Dado** un registro `PENDIENTE`, **cuando** lo abro, **entonces** puedo
   descargar y previsualizar cada soporte.
2. **Cuando** marco *soporte verificado* y paso a revisión, **entonces** el
   estado cambia a `EN_REVISION` y el aprobador recibe notificación.
3. **Dado** un soporte ilegible, **cuando** solicito corrección con observación,
   **entonces** vuelve a `PENDIENTE` y el solicitante es notificado con el motivo.
4. Cada descarga de soporte queda auditada.

## HU-I-03 · Aprobar y justificar automáticamente — **A**

> **Como** coordinador
> **Quiero** que al aprobar una incapacidad las ausencias se justifiquen solas
> **Para** no tener que corregir la asistencia registro por registro

1. **Dado** un registro `EN_REVISION` y permiso de aprobación, **cuando** apruebo,
   **entonces** pasa a `APROBADA` con mi usuario y fecha.
2. **Entonces** todos los registros de asistencia `AUSENTE` del rango pasan a `EXCUSA`.
3. **Entonces** los registros `PRESENTE`, `TARDE` o `EXCUSA` **no se modifican**.
4. **Entonces** `attendance_summary` se recalcula y el porcentaje refleja las justificadas.
5. **Entonces** los docentes del grupo y el acudiente principal reciben notificación.
6. **Dado** que no tengo permiso de aprobación, **cuando** intento aprobar,
   **entonces** recibo **403** y el estado no cambia.
7. **Dado** que no hay sesiones en el rango, **cuando** apruebo, **entonces** se
   aprueba igual y se informa que no hubo ausencias que justificar.
8. **Dado** un fallo al notificar, **entonces** la aprobación se conserva y el
   fallo queda en el log.
9. Todo ocurre en **una sola transacción**: si algo falla, nada queda a medias.

## HU-I-04 · Rechazar con motivo — **A**

> **Como** coordinador
> **Quiero** rechazar una incapacidad indicando la razón
> **Para** que el solicitante sepa qué corregir

1. **Cuando** rechazo sin escribir motivo, **entonces** el sistema no lo permite.
2. **Cuando** rechazo con motivo, **entonces** pasa a `RECHAZADA` y se notifica.
3. **Entonces** la asistencia **no** se modifica.
4. El motivo queda visible en el historial.

## HU-I-05 · Anular y revertir — **A**

> **Como** coordinador
> **Quiero** anular una incapacidad aprobada por error
> **Para** que la asistencia vuelva a su estado real

1. **Dado** un registro `APROBADA` y permiso `delete`, **cuando** anulo con motivo,
   **entonces** pasa a `ANULADA`.
2. **Entonces** **solo** los registros que esta incapacidad justificó vuelven a `AUSENTE`.
3. **Entonces** el consolidado se recalcula.
4. **Dado** un periodo académico cerrado, **entonces** se advierte que la
   asistencia no se revierte y queda constancia.
5. Anular sin motivo no es posible.

## HU-I-06 · Registrar mi propia incapacidad — **A**

> **Como** docente
> **Quiero** registrar mi incapacidad
> **Para** que se gestione mi reemplazo a tiempo

1. **Cuando** registro mi incapacidad, **entonces** queda asociada a mi ficha docente.
2. **Dado** que se aprueba, **entonces** se crea **una** novedad docente vinculada.
3. **Entonces** coordinación puede asignar suplente con el flujo actual, sin cambios.
4. **Dado** que ya existe una novedad para esas fechas, **entonces** se vincula
   la existente en vez de crear otra.

## HU-I-07 · Proteger el dato de salud — **A**

> **Como** responsable de datos personales
> **Quiero** que el diagnóstico solo sea visible para quien deba verlo
> **Para** cumplir la Ley 1581 de 2012

1. **Dado** un usuario **sin** `incapacities.confidencial`, **cuando** consulta la
   API, **entonces** la respuesta **no incluye** `diagnosis` ni `cie10_code`.
2. **Dado** un usuario **con** ese permiso, **entonces** sí los incluye.
3. El filtrado ocurre en el **backend**: no basta con ocultar el campo en pantalla.
4. Toda descarga de soporte médico queda auditada con usuario, fecha e IP.

## HU-I-08 · Consultar el historial — **M**

> **Como** coordinador
> **Quiero** consultar el historial de incapacidades con filtros
> **Para** identificar ausentismo recurrente

1. Puedo filtrar por sujeto, tipo, estado, rango de fechas y sede.
2. Veo días acumulados y número de incapacidades por persona.
3. Puedo exportar a Excel y CSV; la exportación queda auditada.
4. **Dado** que soy coordinador de sede, **entonces** solo veo mi sede.

## HU-I-09 · Constancia imprimible — **M**

> **Como** secretaria
> **Quiero** imprimir la constancia de una incapacidad aprobada
> **Para** entregarla cuando la soliciten

1. La constancia usa el encabezado institucional configurado.
2. Incluye persona, tipo, fechas, días, estado y aprobador.
3. **No** incluye el diagnóstico si quien imprime no tiene el permiso confidencial.

## HU-I-10 · Tablero de ausentismo — **B**

> **Como** rector
> **Quiero** ver un tablero de ausentismo por incapacidad
> **Para** tomar decisiones sobre bienestar y salud ocupacional

1. Veo tarjetas de incapacidades activas, días acumulados y pendientes de aprobación.
2. Veo gráficas por tipo, por sede y por mes, con las **gráficas SVG del sistema**.
3. Puedo filtrar por año lectivo, sede y tipo de sujeto.

## HU-I-11 · Importación masiva — **B**

> **Como** secretaria
> **Quiero** cargar incapacidades desde un archivo
> **Para** registrar en bloque las de un periodo

1. Descargo la plantilla desde la misma pantalla.
2. Si una fila falla, **no se guarda ninguna** y veo fila y columna del error.
3. Volver a cargar el mismo archivo **actualiza**, no duplica.

---

# ÉPICA 2 — CONVIVENCIA ESCOLAR

## HU-C-01 · Adjuntar varias evidencias — **A**

> **Como** docente
> **Quiero** adjuntar varias evidencias a un caso
> **Para** sustentar lo ocurrido con más de un documento

1. **Dado** un caso existente, **cuando** adjunto varios archivos, **entonces**
   todos quedan asociados con descripción y fecha.
2. Se valida extensión, tipo y tamaño de cada archivo.
3. **Dado** que marco una evidencia como reservada, **entonces** solo la ven los
   perfiles con `coexistence.confidencial`.
4. El adjunto actual de `observer_entry` **sigue funcionando** sin cambios.

## HU-C-02 · Programar citación — **A**

> **Como** director de grupo
> **Quiero** programar la citación del acudiente desde el caso
> **Para** dejar constancia del debido proceso

1. **Cuando** programo la citación, **entonces** queda en `PROGRAMADA` y el
   acudiente y el estudiante reciben notificación.
2. Puedo imprimir la citación con el encabezado institucional.
3. **Cuando** registro la asistencia, **entonces** queda `ATENDIDA` con
   observaciones y firmantes.
4. **Dado** que el acudiente no asiste, **entonces** queda `NO_ASISTIO` y puedo
   reprogramar; **ambas** citaciones quedan en el historial.
5. **Dado** que el estudiante no tiene acudiente registrado, **entonces** se
   advierte y se remite al módulo de Estudiantes.

## HU-C-03 · Compromisos con seguimiento — **A**

> **Como** coordinador de convivencia
> **Quiero** registrar compromisos con responsable y plazo
> **Para** poder verificar después si se cumplieron

1. Registro descripción, responsable, fecha límite e indicador → estado `VIGENTE`.
2. **Cuando** verifico el cumplimiento, **entonces** queda `CUMPLIDO` con la
   evidencia de verificación.
3. **Dado** que la fecha límite pasó sin verificación, **entonces** el sistema lo
   marca `INCUMPLIDO` y genera alerta.
4. **Dado** un caso con compromisos sin verificar, **cuando** intento cerrarlo,
   **entonces** el sistema **no** lo permite y me indica cuáles faltan.

## HU-C-04 · Escalar al comité — **A**

> **Como** coordinador de convivencia
> **Quiero** escalar un caso al comité
> **Para** que se resuelva en la instancia que corresponde

1. **Cuando** escalo con justificación, **entonces** el caso pasa a `ESCALADO_COMITE`
   y los miembros del comité son notificados.
2. **Dado** que no hay comité conformado en el año lectivo, **entonces** se exige
   conformarlo primero.
3. **Dado** un caso tipo I, **entonces** se advierte que el manual no lo contempla
   y se exige justificación reforzada.
4. La transición queda en el historial con usuario, fecha y motivo.

## HU-C-05 · Sesión con quórum y acta — **A**

> **Como** miembro del comité
> **Quiero** que el acta valide el quórum
> **Para** que las decisiones no queden viciadas

1. Registro fecha, lugar, asistentes y orden del día.
2. **Dado** que los asistentes no alcanzan el quórum configurado, **entonces**
   el sistema **no** permite registrar decisiones y la sesión queda `SIN_QUORUM`.
3. **Dado** que hay quórum, **entonces** puedo registrar desarrollo, decisiones y compromisos.
4. El acta se numera automáticamente y es imprimible con el formato institucional.

## HU-C-06 · Registrar decisión sustentada — **A**

> **Como** rector
> **Quiero** registrar la decisión citando el artículo del manual
> **Para** que quede jurídicamente sustentada

1. **Cuando** registro la decisión sin artículo del manual, **entonces** no se permite.
2. Tipifico la decisión (formativa, correctiva, remisión, absolución) y su vigencia.
3. **Entonces** el estudiante y el acudiente son notificados.
4. Puedo registrar un recurso de reposición y su resolución sobre la misma decisión.

## HU-C-07 · Alertas tempranas parametrizables — **M**

> **Como** orientadora escolar
> **Quiero** que el sistema me avise de estudiantes en riesgo
> **Para** intervenir antes de que el problema crezca

1. Configuro umbrales (reincidencia, inasistencia, bajo rendimiento) **sin tocar código**.
2. **Dado** que un estudiante supera un umbral activo, **entonces** se genera la
   alerta con su nivel y destinatario.
3. **Cuando** atiendo la alerta y registro la acción, **entonces** no se vuelve a
   generar por el mismo hecho.
4. **Dado** que las ausencias están cubiertas por una incapacidad **aprobada**,
   **entonces** **no** se genera alerta por inasistencia.

## HU-C-08 · Consultar mi historial — **A**

> **Como** acudiente
> **Quiero** consultar el historial de convivencia de mi hijo
> **Para** acompañar su proceso

1. Veo únicamente los casos de **mi** estudiante.
2. **Cuando** intento acceder al caso de otro estudiante, **entonces** recibo 403 o 404.
3. **No** veo las evidencias marcadas como reservadas.
4. Veo los compromisos vigentes y su estado.

## HU-C-09 · Reconocimiento positivo — **M**

> **Como** director de grupo
> **Quiero** registrar reconocimientos positivos
> **Para** que el observador no sea solo sancionatorio

1. Uso la categoría `POSITIVA` existente, con la misma trazabilidad.
2. El acudiente es notificado.
3. Los reconocimientos alimentan el indicador de clima escolar.

## HU-C-10 · Reportes y actas exportables — **M**

> **Como** coordinador
> **Quiero** exportar los reportes de convivencia
> **Para** presentarlos al consejo directivo

1. Exporto a Excel y CSV con `ExportMixin`; la exportación queda auditada.
2. Imprimo actas y citaciones con el encabezado institucional.
3. Los reportes respetan el alcance por sede del usuario.

## HU-C-11 · No romper lo que ya funciona — **A**

> **Como** docente que usa el observador hoy
> **Quiero** seguir trabajando exactamente igual
> **Para** no tener que reaprender el sistema

1. **Dado** el flujo actual de registro de observaciones, **cuando** se despliega
   la extensión, **entonces** funciona **sin ningún cambio**.
2. Los estados y categorías actuales se conservan.
3. `smoke_test.py` responde correctamente en todas las rutas previas.
4. La suite de pruebas existente pasa completa.

---

# ÉPICA 3 — TRANSVERSALES

## HU-T-01 · Permisos coherentes — **A**

> **Como** administrador
> **Quiero** administrar los permisos de los módulos nuevos igual que los actuales
> **Para** no aprender un mecanismo distinto

1. Los módulos nuevos aparecen en *Configuración → Acceso de Perfiles*.
2. Admiten las **seis** acciones estándar.
3. **Dado** un perfil sin `view`, **entonces** el módulo no aparece en el menú
   **y** la ruta responde 403.
4. Las excepciones individuales por usuario funcionan igual que hoy.

## HU-T-02 · Auditoría completa — **A**

> **Como** auditor
> **Quiero** que toda operación quede registrada
> **Para** poder reconstruir qué pasó

1. Creación, modificación, borrado, aprobación, exportación e importación se registran.
2. Cada entrada guarda usuario, perfil, fecha, IP, ruta y objeto.
3. **Dado** un usuario normal, **cuando** intenta modificar o borrar la bitácora,
   **entonces** recibe 403/405.
4. Puedo filtrar la bitácora por dominio con `?module_prefix=`.

## HU-T-03 · Consistencia visual — **A**

> **Como** usuario final
> **Quiero** que los módulos nuevos se vean como el resto
> **Para** que parezca que siempre estuvieron

1. Usan el mismo layout, menú, tipografía y componentes.
2. **No** introducen ningún color fuera de `variables.css`.
3. Funcionan en tema claro y oscuro.
4. Son responsive a 375 px sin desbordamiento horizontal.

---

## Resumen de priorización

| Épica | A | M | B | Total |
|---|---|---|---|---|
| Incapacidades | 7 | 2 | 2 | 11 |
| Convivencia | 7 | 4 | 0 | 11 |
| Transversales | 3 | 0 | 0 | 3 |
| **Total** | **17** | **6** | **2** | **25** |
