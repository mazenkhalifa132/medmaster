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

    function filterModuleSettings() {
        const moduleSelect = document.getElementById('id_module');
        if (!moduleSelect) return;

        ['id_subject', 'id_week'].forEach((id) => {
            const select = document.getElementById(id);
            if (!select) return;
            const selectedModule = moduleSelect.value;
            let selectedOptionIsValid = false;
            Array.from(select.options).forEach((option) => {
                // Until a module is chosen, only retain the blank option. This prevents
                // settings from another module appearing in the dropdown.
                const visible = !option.value || (selectedModule && option.dataset.module === selectedModule);
                option.hidden = !visible;
                option.disabled = !visible;
                if (option.selected && visible) selectedOptionIsValid = true;
            });
            if (!selectedOptionIsValid && select.value) select.value = '';
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        const yearSelect = document.getElementById('id_year');
        if (!yearSelect) return;
        filterModules();
        filterModuleSettings();
        yearSelect.addEventListener('change', () => {
            filterModules();
            filterModuleSettings();
        });
        document.getElementById('id_module').addEventListener('change', filterModuleSettings);
    });
})();
