# Verificación técnica de RSS · 24 de octubre de 2026

Entre **01:23:23 y 01:23:29 UTC** se hizo una GET por cada una de las 16 URLs
del catálogo o candidatas ya registradas. Máximo dos peticiones simultáneas,
15 segundos por petición, sin reintentos ni redirecciones seguidas; TLS validado,
sin cookies, credenciales ni mecanismos para eludir restricciones. Se leyó como
máximo 450.001 bytes para detectar el límite de 450.000 del adaptador.

Resultado: **5 XML completos, 4 feeds compatibles con el adaptador; 16 fuentes
desactivadas, 0 permisos aprobados**. La revisión no cambia las condiciones ni
los permisos: siguen 11 restringidos y 5 pendientes. Un XML accesible o un título
aceptado no autoriza su publicación ni su uso comercial.

| Fuente | HTTP observado | XML completo | Compatibilidad del adaptador |
| --- | ---: | --- | --- |
| El Nacional | 200 | RSS 2.0, 100 entradas | 4 aceptadas; título/origen en las 60 examinadas |
| El Universal Venezuela | 404 | No validado | No ejecutado |
| El Pitazo | 200 | RSS 2.0, 10 entradas | 4 aceptadas; título/origen en las 10 examinadas |
| Efecto Cocuyo | 403 | No validado | No ejecutado |
| TalCual | 403 | No validado | No ejecutado |
| Runrun.es | 200 | RSS, 8 entradas | 4 aceptadas; título/origen en las 8 examinadas |
| La Nación | 200 | No validado: supera límite | No ejecutado |
| Infobae | 200 | No validado: supera límite | No ejecutado |
| El Tiempo | 200 | RSS, 10 entradas | 2 aceptadas; título/origen en las 10 examinadas |
| El Espectador | 301 | No validado | Redirección no seguida |
| El Comercio Perú | 200 | No validado: supera límite | No ejecutado |
| La República | 301 | No validado | Redirección no seguida |
| El Universal México | 404 | No validado: supera límite | No ejecutado |
| Milenio | 404 | No validado | No ejecutado |
| El País Uruguay | 302 | No validado | Redirección no seguida |
| Folha de S.Paulo | 200 | RSS 0.91, 100 entradas | 0 aceptadas: ninguna de 60 URLs pasa HTTPS/dominio |

Se marca `technical_status: verified` para El Nacional, El Pitazo, Runrun.es y
El Tiempo, con la URL efectivamente consultada. Las cuatro siguen desactivadas
y sin evidencia de autorización. El adaptador examina como máximo 60 entradas
y acepta hasta cuatro; los contadores no representan la cobertura completa del
medio. Las fechas se evaluaron a 01:23:23 UTC, con sus reglas de 24 horas y
tolerancia futura de 15 minutos.

Los códigos HTTP son respuestas observadas a través del transporte del entorno;
no se atribuyen de forma independiente al editor o a un intermediario. No se
conservaron Server/Via. Los 403 no demuestran una prohibición permanente y los
404 no prueban que no exista un feed alternativo. Un cuerpo cortado por tamaño
no se declara XML mal formado.

Folha entregó XML y fechas vigentes, pero ninguna URL examinada cumplió el
control editorial. No se conservaron URLs de artículos para distinguir esquema,
dominio u otra causa; su adaptador no se declara verificado.

Se registraron estas redirecciones sin comprobar el destino: El Espectador a
`https://www.elespectador.com/arc/outboundfeeds/feed/`, La República a
`https://larepublica.pe/rss` y El País a
`https://www.elpais.com.uy/rss/latest`. No son nuevos feeds validados.

La última observación por fuente, URL, MIME, tamaño, hash del cuerpo, conteos y
fecha UTC queda en `config/regional_sources.json`. No se publican cuerpos RSS,
titulares, imágenes, extractos ni artículos de esta auditoría. Las condiciones
oficiales y la evidencia anterior siguen en
[la revisión del 23 de octubre](EVIDENCIA_FUENTES_2026-10-23.md).

Validación: 18 pruebas existentes del adaptador aprobadas; invariantes del
catálogo conservan permisos, `permission_evidence: null` y `enabled: false`.
Las jurisdicciones de los editores siguen siendo VE, AR, CO, PE, MX, UY y BR;
no se revisó normativa nacional ni se certifica cumplimiento legal.
