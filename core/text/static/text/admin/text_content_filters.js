(function () {
    function filterSubcategories() {
        const moduleSelect = document.getElementById('id_module');
        const subcategorySelect = document.getElementById('id_subcategory');
        if (!moduleSelect || !subcategorySelect) return;

        const selectedModule = moduleSelect.value;
        let selectedOptionIsValid = false;
        Array.from(subcategorySelect.options).forEach((option) => {
            const visible = !option.value || (selectedModule && option.dataset.module === selectedModule);
            option.hidden = !visible;
            option.disabled = !visible;
            if (option.selected && visible) selectedOptionIsValid = true;
        });
        if (!selectedOptionIsValid && subcategorySelect.value) subcategorySelect.value = '';
    }

    document.addEventListener('DOMContentLoaded', () => {
        const moduleSelect = document.getElementById('id_module');
        if (!moduleSelect) return;
        filterSubcategories();
        moduleSelect.addEventListener('change', filterSubcategories);
    });
})();
