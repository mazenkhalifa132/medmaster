(function () {
    function updateExamTargeting() {
        const ruleType = document.getElementById('id_rule_type');
        const examSection = document.querySelector('.exam-targeting');
        const moduleSection = document.querySelector('.module-targeting');
        const thresholdSection = document.querySelector('.threshold-targeting');
        if (!ruleType) return;
        if (examSection) examSection.hidden = ruleType.value !== 'exam_score';
        if (moduleSection) moduleSection.hidden = ruleType.value !== 'module_progress';
        if (thresholdSection) {
            thresholdSection.hidden = !['exam_score', 'login_streak'].includes(ruleType.value);
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        const ruleType = document.getElementById('id_rule_type');
        if (!ruleType) return;
        updateExamTargeting();
        ruleType.addEventListener('change', updateExamTargeting);
    });
})();
