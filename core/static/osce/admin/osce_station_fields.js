(function () {
    const bpFields = ['systolic_pressure', 'diastolic_pressure'];
    const ecgFields = ['ecg_v1', 'ecg_v2', 'ecg_v3', 'ecg_v4', 'ecg_v5', 'ecg_v6'];

    function fieldRow(fieldName) {
        const input = document.getElementById(`id_${fieldName}`);
        if (!input) return null;
        return input.closest('.form-row') || input.closest('.fieldBox');
    }

    function toggleFields(fieldNames, visible) {
        fieldNames.forEach((fieldName) => {
            const row = fieldRow(fieldName);
            if (!row) return;
            row.style.display = visible ? '' : 'none';
        });
    }

    function updateStationFields() {
        const station = document.getElementById('id_osce_station');
        if (!station) return;
        toggleFields(bpFields, station.value === 'bp');
        toggleFields(ecgFields, station.value === 'ecg');
    }

    document.addEventListener('DOMContentLoaded', () => {
        const station = document.getElementById('id_osce_station');
        if (!station) return;
        station.addEventListener('change', updateStationFields);
        updateStationFields();
    });
})();
