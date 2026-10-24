# Proteger main manteniendo la actualización horaria

## Arquitectura y límites

El código, fuentes, helpers, plantilla y variables de generación se usan desde
`main`. El workflow abre un segundo checkout con sparse checkout de
`news-data:data/historial.json` en `.news-data/`; sólo lee ese blob regular mediante
Git. No ejecuta, importa ni instala archivos de la rama de datos. El historial se
copia a `data/historial.json` del checkout de código para generar el sitio.

La generación conserva sus pruebas y auditorías antes de persistir y desplegar
Pages. El helper crea un commit cuyo único cambio es `data/historial.json` sobre el
último árbol remoto de `news-data` y hace push normal explícito a esa rama. No usa
force, rebase ni excepción de protección. Si otro escritor cambió el historial,
la ejecución falla antes de publicar para no perder noticias; volver a ejecutar
carga la última versión. Si falla Pages después de persistir, los datos quedan
conservados y puede repetirse la ejecución. El grupo de concurrencia existente
serializa las ejecuciones del publicador.

`quality.yml` sólo lee: prueba el historial versionado y código en los PR y cada
push de `main`; no deduplica ni hace commits. Se conservan los IDs `verify-pr` y
`normalize-push` para evitar cambiar identidades de checks existentes; el segundo
nombre es heredado y ya no normaliza. Se elimina el filtro de rutas de push para
no omitir la validación por cambios fuera de la lista anterior.

`contents: write` del publicador sigue siendo un permiso a nivel repositorio;
GitHub no permite restringir el GITHUB_TOKEN a un único archivo o rama mediante
ese permiso. La protección de `main` debe aplicar también a administradores y no
contener bypass para el bot. El checkout de código no conserva credenciales; sólo
el checkout de datos las conserva para el push. Las protecciones son el límite de
autorización de GitHub; el helper añade una restricción explícita de destino.

## Bootstrap y orden de activación

1. Registrar el SHA actual de `main`, el blob del historial y el último despliegue
   correcto. Pausar temporalmente el workflow horario durante el cambio para no
   perder una actualización entre la copia inicial y la nueva versión.
2. Crear `news-data` con el último `data/historial.json` validado. Puede nacer del
   SHA registrado de `main`; los demás archivos heredados no se usan. Una rama
   inicial con sólo el historial también sirve. No crear workflows propios allí.
3. Abrir el PR del cambio de pipeline, ejecutar CI del SHA final y revisar permisos
   y diff. Los workflows y protecciones están excluidos de la fusión asistida
   rutinaria por `docs/agent-workflow.md`; requieren autorización específica.
4. Tras integrar, ejecutar manualmente el publicador desde `main`. Comprobar:
   carga del SHA de datos esperado, pruebas/auditorías aprobadas, commit de datos
   cuyo diff sólo contiene el historial, push normal a `news-data` y Pages sano.
   Registrar URLs de run/despliegue y ambos SHA. Confirmar que `main` no cambia
   durante la persistencia. Reactivar la programación si se había pausado.
5. Sólo después activar la protección de `main` descrita abajo. Repetir una
   ejecución real del publicador y comprobar que actualiza datos y despliega sin
   cambiar `main`. Confirmar con un PR controlado que los checks se exigen y un
   intento de push directo que GitHub lo rechaza, sin desactivar ninguna regla.

Si `news-data` no existe o no contiene JSON válido, el publicador falla antes de
consultar fuentes y publicar. No hay fallback silencioso al historial de `main`.
La copia en `main` sigue siendo fixture/bootstrap de pruebas; el historial vivo
es el de `news-data`, por lo que un desarrollo local debe cargarlo explícitamente
si necesita reproducir la edición más reciente.

La QA visual usa `scripts/render_visual_fixture.py`: toma como reloj la fecha
editorial máxima del fixture, copia sus bytes a un directorio temporal y ejecuta
el CLI real con `--solo-render --ahora`. No consulta fuentes ni modifica la copia
versionada; un fixture vacío o sin fechas falla. Así el check sigue siendo útil
cuando transcurren más de 24 horas sin cambios del código. El publicador conserva
el reloj real y la caducidad de 24 horas; este helper se usa sólo para QA.

## Configuración administrativa revisable

Objetivo exacto: rama `main`, sin patrón que capture `news-data`. En Settings →
Branches crear una protección de rama (o ruleset equivalente activo) con:

| Control | Configuración propuesta |
| --- | --- |
| Require a pull request before merging | Activado; 0 aprobaciones obligatorias inicialmente permite revisión y PR en repositorio de un solo responsable. Subir a 1 cuando exista otro revisor habilitado. |
| Require status checks to pass | Activado: `verify-pr` y `visual-qa`, origen GitHub Actions. Confirmar nombre/origen en el PR final aprobado antes de seleccionarlo. |
| Require branches to be up to date | Activado. |
| Require conversation resolution | Activado. |
| Do not allow bypassing the above settings | Activado, incluyendo administradores; sin usuarios/apps con bypass. |
| Allow force pushes / deletions | Desactivado. |
| Lock branch / restrict all updates | Desactivado: deben permitirse fusiones válidas por PR. |

No exigir `actualizar`, Pages ni `normalize-push` como sustituto de `verify-pr`:
la validación del PR corre en `verify-pr`; el job heredado de push se omite en PR.
Antes de aplicar, preservar otros checks requeridos vigentes que sigan siendo
pertinentes, y comprobar que sus nombres son únicos. Si se usa REST, obtener
`app.id` del check-run de GitHub Actions para fijar el origen del check en
`required_status_checks.checks`; no usar `app_id: -1` ni adivinar el identificador.
La administración debe revisar la regla resultante y sus destinatarios reales.

La herramienta GitHub conectada de esta sesión no expone un mutador de branch
protection/rulesets y no se dispone de credenciales administrativas locales.
Preparar archivos no activa ninguna protección: aplicarla necesita un
administrador en la interfaz de GitHub o un token autorizado con permiso de
administración del repositorio. No se debe solicitar un PAT para este cambio si
el responsable puede aplicarlo desde Settings.

## Recuperación

- Fallo de `news-data`: suspender el publicador, preservar el commit fallido y
  logs; restaurar el historial bueno mediante un **nuevo commit normal** en
  `news-data`. Validar y ejecutar de nuevo desde `main`; no force/reset remoto.
- Fallo del cambio de código: corregir o revertir por PR con los checks exigidos.
  Mantener la separación de datos durante la recuperación. Revertir ciegamente
  el workflow antiguo reintroduciría un push a `main` que la protección rechazará.
  Si hay que revertirlo, mantener pausado el publicador hasta corregir ese push.
- Una protección que bloquea datos probablemente abarca `news-data`: corregir
  únicamente su objetivo; no dar bypass al bot ni desproteger `main`.
- Para recuperar publicación, puede volver a desplegarse un artefacto Pages
  conocido mediante las herramientas autorizadas de GitHub. No afirmar que se
  recuperó hasta verificar la URL publicada y el run correspondiente.

## Evidencia y responsabilidades

Las pruebas `tests/test_news_data.py` usan repositorios Git bare temporales,
rechazo real de destinos por hook, dos escritores concurrentes y comparación de
refs/diffs. No necesitan credenciales ni red. La evidencia de CI, bootstrap,
protección efectiva y despliegue se registra en el Issue/PR con SHA y URLs; esta
página define el procedimiento, no afirma su ejecución.

Datos y licencias: se mueve el mismo historial público de noticias entre ramas
del mismo proveedor/repositorio. No se añaden campos personales, fuentes,
licencias ni un proveedor nuevo. El historial Git conserva versiones anteriores;
esta separación no implica borrado ni una política nueva de retención. Las
jurisdicciones y derechos de las fuentes siguen los controles editoriales
existentes; no se declara cumplimiento legal por proteger una rama.

Referencias oficiales consultadas el 2026-10-23: confirman alcance por rama,
exigencia de PR/checks, selección de app de origen, aplicación a administradores
y permiso `Administration: write` para modificar protección mediante REST.
El acceso HTTP directo del entorno está bloqueado; se consultaron mediante la
herramienta web conectada. El permiso del conector y la protección aplicada deben
verificarse por separado; esta documentación no afirma que estén activos.

Referencias:

- [GitHub: about protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
- [GitHub REST: update branch protection](https://docs.github.com/en/rest/branches/branch-protection#update-branch-protection).
