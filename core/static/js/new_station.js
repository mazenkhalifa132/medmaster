/*
 * Testing shell. Change only ACTIVE_STATION to load another registered station.
 * A station module must register itself with window.Testing.registerStation(...).
 */
const ACTIVE_STATION = 'ecg-station'; // Change this to the id of the station you want to load
const INITIAL_STATION_ID = window.OSCE_INITIAL_STATION || ACTIVE_STATION;

const Testing = {
    stations: new Map(),
    activeStation: null,
    registerStation(station) {
        if (!station || !station.id || typeof station.init !== 'function') {
            throw new Error('A station needs an id and an init() function.');
        }
        this.stations.set(station.id, station);
    },
    startMCQ() {
        window.startMCQ?.();
        return;

        const station = this.activeStation;
        document.getElementById('phase-practical').classList.add('d-none');
        document.getElementById('phase-mcq').classList.remove('d-none');
        if (!station || !station.questions?.length) {
            document.getElementById('mcqQuestionsWrap').innerHTML = '<p class="text-muted mb-0">No MCQ questions are configured for this station.</p>';
            return;
        }
        let index = 0;
        let score = 0;
        const render = () => {
            const question = station.questions[index];
            const wrap = document.getElementById('mcqQuestionsWrap');
            if (!question) {
                wrap.innerHTML = '';
                document.getElementById('mcq-result').innerHTML = `<h5 class="fw-bold">OSCE Assessment Complete!</h5><p class="text-muted mb-0">Practical station: <strong>${window.oscePracticalResult ? 'Passed' : 'Needs improvement'}</strong> · MCQ score: <strong>${score} / ${station.questions.length}</strong></p>`;
                document.getElementById('mcq-result').classList.remove('d-none');
                return;
            }
            document.getElementById('mcqQuestionNumber').textContent = `Question ${index + 1} of ${station.questions.length}`;
            document.getElementById('mcqQuestionText').textContent = question.q;
            document.getElementById('mcqOptions').innerHTML = question.options.map((option, optionIndex) => `<label class="form-check mb-2"><input class="form-check-input" type="radio" name="station-question" value="${optionIndex}"> ${option}</label>`).join('');
            document.getElementById('confirmStationQuestion').onclick = () => {
                const selected = wrap.querySelector('input:checked');
                if (!selected) return alert('Please select an answer first.');
                if (Number(selected.value) === question.correct) score++;
                index++;
                render();
            };
        };
        render();
    },
    loadStation(id = ACTIVE_STATION) {
        const station = this.stations.get(id);
        if (!station) throw new Error(`Station "${id}" is not registered. Load its script and set ACTIVE_STATION to its id.`);
        this.activeStation = station;
        document.getElementById('stationTitle').textContent = station.title;
        document.getElementById('stationInstructions').textContent = station.instructions;
        station.renderControls(document.getElementById('canvas-container'), document.getElementById('station-control-panel'));
        station.init();
    }
};
window.Testing = Testing;

document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.getElementById('menuToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const toggleSidebar = () => { sidebar.classList.toggle('open'); overlay.classList.toggle('show'); };
    menuToggle?.addEventListener('click', toggleSidebar);
    overlay?.addEventListener('click', toggleSidebar);
    Testing.loadStation(INITIAL_STATION_ID);
});
