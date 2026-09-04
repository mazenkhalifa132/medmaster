(function () {
    function filterOptions(select, attribute, value) {
        let selectedIsValid = false;
        Array.from(select.options).forEach((option) => {
            const visible = !option.value || (Boolean(value) && option.dataset[attribute] === value);
            option.hidden = !visible;
            option.disabled = !visible;
            if (option.selected && visible) selectedIsValid = true;
        });
        if (!selectedIsValid && select.value) select.value = '';
    }

    function setupTargeting(yearId, moduleId, examId) {
        const year = document.getElementById(yearId);
        const module = document.getElementById(moduleId);
        const exam = examId ? document.getElementById(examId) : null;
        if (!year || !module) return;
        function updateExams() {
            if (!exam) return;
            filterOptions(exam, 'module', module.value);
            exam.disabled = !module.value;
        }
        function updateModules() {
            filterOptions(module, 'year', year.value);
            module.disabled = !year.value;
            updateExams();
        }
        updateModules();
        year.addEventListener('change', updateModules);
        module.addEventListener('change', updateExams);
    }

    document.addEventListener('DOMContentLoaded', () => {
        setupTargeting('id_exam_year', 'id_exam_module', 'id_exam');
        setupTargeting('id_module_year', 'id_target_module');
    });
})();
