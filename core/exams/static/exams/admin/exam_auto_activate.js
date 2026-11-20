(function () {
    function toggleActivationDate() {
        const enabled = document.getElementById('id_auto_activate');
        const row = document.querySelector('.field-activation_date');
        if (enabled && row) {
            row.hidden = !enabled.checked;
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const enabled = document.getElementById('id_auto_activate');
        if (!enabled) return;
        toggleActivationDate();
        enabled.addEventListener('change', toggleActivationDate);
    });
})();
