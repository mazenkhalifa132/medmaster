(function () {
    function filterModules() {
        const yearSelect = document.getElementById('id_year');
        const moduleSelect = document.getElementById('id_module');
        if (!yearSelect || !moduleSelect) return;

        const selectedYear = yearSelect.value;
        let selectedOptionIsValid = false;
        Array.from(moduleSelect.options).forEach((option) => {
            const visible = !option.value || !selectedYear || option.dataset.year === selectedYear;
            option.hidden = !visible;
            option.disabled = !visible;
            if (option.selected && visible) selectedOptionIsValid = true;
        });
        if (!selectedOptionIsValid && moduleSelect.value) moduleSelect.value = '';
    }

    document.addEventListener('DOMContentLoaded', () => {
        const yearSelect = document.getElementById('id_year');
        if (!yearSelect) return;
        filterModules();
        yearSelect.addEventListener('change', filterModules);
    });
})();
