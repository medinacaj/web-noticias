# Cabecera, carrusel automático y pie compacto

El usuario pide devolver la fecha de actualización a la derecha, movimiento automático en «Lo último», recuperar el contador de noticias y reducir el pie siguiendo su captura (sin datos de edición, copyright ni fecha repetida). Se conserva la paleta clara/grafito ya publicada y el resto de la interfaz.

- Cabecera: fecha a la derecha y contador general junto a ella. En pantallas pequeñas, segunda fila compacta con contador a la izquierda y fecha a la derecha. Contar URLs publicadas en portada/secciones, no registros del historial; mantener contadores por sección. No contar eventos como noticias.
- Carrusel: avance automático cada 6 segundos, bucle de hasta seis titulares, manteniendo una línea y las flechas manuales. Botón visible pausa/reanudar. Suspender al pasar el puntero, entrar con teclado o quedar la pestaña oculta; movimiento reducido desactiva el autoarranque y evita animaciones. Una sola noticia no inicia temporizadores ni muestra controles innecesarios. No anunciar automáticamente cada titular al lector de pantalla.
- Pie: una fila flexible con marca, enlaces útiles y firma LinkedIn; atribución breve debajo. Quitar copyright, segunda fecha y bloque de datos de edición. Conservar Sobre el portal, RSS, boletín y enlaces de privacidad configurados; no cambiar configuraciones comerciales ni fuentes.

Validación: contador coherente con tarjetas, fecha a la derecha en 320/390/768/1024/1440, altura del pie, autoplay real y pausa/reanudación, movimiento reducido, teclado y lectura sin JS. Suite, SEO, QA visual, revisión, CI y publicación bajo el flujo autorizado de esta sesión.
