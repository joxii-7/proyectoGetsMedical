/**
 * tipo_otro_equipo.js
 * Muestra u oculta el campo "tipo_otro" en el admin de Equipo
 * según si el select "tipo" tiene el valor "otro".
 *
 * Colocar en:  <tu_app>/static/admin/js/tipo_otro_equipo.js
 * (o en STATICFILES_DIRS si usas una carpeta global de estáticos)
 */
(function () {
    'use strict';

    function toggleTipoOtro() {
        const tipoSelect = document.getElementById('id_tipo');
        const tipoOtroRow = document.querySelector('.field-tipo_otro');

        if (!tipoSelect || !tipoOtroRow) return;

        const mostrar = tipoSelect.value === 'otro';
        tipoOtroRow.style.display = mostrar ? '' : 'none';

        // Si se oculta, limpiar el valor para no guardar texto huérfano
        if (!mostrar) {
            const input = document.getElementById('id_tipo_otro');
            if (input) input.value = '';
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const tipoSelect = document.getElementById('id_tipo');
        if (!tipoSelect) return;

        toggleTipoOtro();                              // estado inicial
        tipoSelect.addEventListener('change', toggleTipoOtro);
    });
})();