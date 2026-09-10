(function () {
    function updateExamSettingsVisibility() {
        const enabled = document.getElementById('id_has_exams');
        if (!enabled) return;
        ['exam_subjects-group', 'exam_weeks-group'].forEach((id) => {
            const group = document.getElementById(id);
            if (group) group.hidden = !enabled.checked;
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        const enabled = document.getElementById('id_has_exams');
        if (!enabled) return;
        updateExamSettingsVisibility();
        enabled.addEventListener('change', updateExamSettingsVisibility);
    });
})();
