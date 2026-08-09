// ECG precordial lead placement station.
(() => {
    const VIEWBOX = { width: 1536, height: 1024 };
    const LEADS = [
        { id: 'v1', label: 'V1', target: { x: 733, y: 305 } },
        { id: 'v2', label: 'V2', target: { x: 802, y: 305 } },
        { id: 'v3', label: 'V3', target: { x: 814, y: 386 } },
        { id: 'v4', label: 'V4', target: { x: 877, y: 424 } },
        { id: 'v5', label: 'V5', target: { x: 935, y: 439 } },
        { id: 'v6', label: 'V6', target: { x: 983, y: 429 } },
    ];
    const LEAD_SIZE = 56;
    const TARGET_RADIUS = 30;
    const ACCEPTANCE_DISTANCE = 44;
    // Capture this while the script is loading; `document.currentScript` is null
    // later, when the station is rendered after DOMContentLoaded.
    const ASSET_BASE = new URL('.', document.currentScript.src);
    const asset = (file) => new URL(`imgs/${file}`, ASSET_BASE).href;

    const ALL_LEAD_IDS = LEADS.map((lead) => lead.id);
    const configuredLeadIds = Array.isArray(window.OSCE_ECG_LEADS)
        ? window.OSCE_ECG_LEADS.filter((leadId) => ALL_LEAD_IDS.includes(leadId))
        : [];
    let activeLeadSelectionMode = configuredLeadIds.length && configuredLeadIds.length < ALL_LEAD_IDS.length ? 'group' : 'all';
    let selectedLeadIds = configuredLeadIds.length ? configuredLeadIds : [...ALL_LEAD_IDS];
    let leadPositions = {};
    let latestCheck = null;

    function getConfiguredLeadIds() {
        if (activeLeadSelectionMode === 'single') {
            return selectedLeadIds.length ? [selectedLeadIds[0]] : [ALL_LEAD_IDS[0]];
        }
        if (activeLeadSelectionMode === 'group') {
            return selectedLeadIds.filter((leadId) => ALL_LEAD_IDS.includes(leadId));
        }
        return [...ALL_LEAD_IDS];
    }

    function getConfiguredLeads() {
        return LEADS.filter((lead) => getConfiguredLeadIds().includes(lead.id));
    }

    function defaultPositions() {
        const activeLeads = getConfiguredLeads();
        return Object.fromEntries(activeLeads.map((lead, index) => [lead.id, {
            x: 130 + (index % 3) * 95,
            y: 150 + Math.floor(index / 3) * 95,
        }]));
    }

    function renderLeadSelectionControls() {
        const container = document.getElementById('ecgLeadSelectionControls');
        if (!container) return;

        if (activeLeadSelectionMode === 'all') {
            container.innerHTML = '';
            return;
        }

        if (activeLeadSelectionMode === 'single') {
            container.innerHTML = `
                <label class="form-label small mb-1" for="ecgSingleLeadSelect">Choose one lead</label>
                <select id="ecgSingleLeadSelect" class="form-select form-select-sm">
                    ${LEADS.map((lead) => `<option value="${lead.id}" ${selectedLeadIds.includes(lead.id) ? 'selected' : ''}>${lead.label}</option>`).join('')}
                </select>`;
            document.getElementById('ecgSingleLeadSelect')?.addEventListener('change', (event) => {
                selectedLeadIds = [event.target.value];
                refreshStation();
            });
            return;
        }

        container.innerHTML = `
            <label class="form-label small mb-1">Choose the leads to include</label>
            <div class="d-flex flex-wrap gap-2">
                ${LEADS.map((lead) => `<label class="form-check form-check-inline mb-2">
                    <input class="form-check-input" type="checkbox" value="${lead.id}" ${selectedLeadIds.includes(lead.id) ? 'checked' : ''}>
                    <span class="form-check-label">${lead.label}</span>
                </label>`).join('')}
            </div>`;

        container.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
            checkbox.addEventListener('change', () => {
                const checkedIds = Array.from(container.querySelectorAll('input[type="checkbox"]:checked')).map((item) => item.value);
                selectedLeadIds = checkedIds.length ? checkedIds : [...ALL_LEAD_IDS];
                refreshStation();
            });
        });
    }

    function renderEcgStation(canvasContainer, panel) {
        leadPositions = defaultPositions();
        latestCheck = null;
        canvasContainer.classList.add('ecg-sim-area');
        const activeLeads = getConfiguredLeads();
        canvasContainer.innerHTML = `
            <div class="ecg-scene" id="ecgScene">
                <img class="ecg-trunk" src="${asset('trunk2.png')}" alt="Patient torso for ECG lead placement">
                <svg id="ecgSvg" viewBox="0 0 ${VIEWBOX.width} ${VIEWBOX.height}" aria-label="ECG lead placement area">
                    <g class="ecg-targets" aria-hidden="true">
                        ${activeLeads.map((lead) => `<circle id="target-${lead.id}" cx="${lead.target.x}" cy="${lead.target.y}" r="${TARGET_RADIUS}"></circle>`).join('')}
                    </g>
                    <g id="ecgLeads">
                        ${activeLeads.map((lead) => `<g id="lead-${lead.id}" class="ecg-lead" data-lead="${lead.id}" transform="translate(${leadPositions[lead.id].x} ${leadPositions[lead.id].y})" tabindex="0" role="button" aria-label="Drag ${lead.label} lead"><image href="${asset(`${lead.id}.png`)}" x="${-LEAD_SIZE / 2}" y="${-LEAD_SIZE / 2}" width="${LEAD_SIZE}" height="${LEAD_SIZE}"></image><text class="ecg-lead-label" x="0" y="${LEAD_SIZE / 2 + 18}">${lead.label}</text></g>`).join('')}
                    </g>
                </svg>
                <div class="ecg-hint">Drag each selected V lead onto its right location.</div>
            </div>`;

        panel.innerHTML = `
            <div class="card p-3 h-100 ecg-control-panel">
                <h3 class="h5 mb-2">ECG Lead Placement</h3>
                <p class="small text-muted">Choose which leads to include, then place them on the correct chest landmarks.</p>
                <div class="mb-3">
                    <label class="form-label small mb-1" for="ecgLeadSetMode">Lead set</label>
                    <select id="ecgLeadSetMode" class="form-select form-select-sm">
                        <option value="all" ${activeLeadSelectionMode === 'all' ? 'selected' : ''}>All leads</option>
                        <option value="single" ${activeLeadSelectionMode === 'single' ? 'selected' : ''}>One specific lead</option>
                        <option value="group" ${activeLeadSelectionMode === 'group' ? 'selected' : ''}>Custom group</option>
                    </select>
                </div>
                <div id="ecgLeadSelectionControls"></div>
                <div id="ecgChecklist" class="ecg-checklist mb-3 mt-3">${activeLeads.map((lead) => `<div id="ecg-status-${lead.id}" class="ecg-checklist-item"><span>•</span> ${lead.label}</div>`).join('')}</div>
                <button id="checkEcgPlacement" class="btn btn-outline-primary w-100 mb-2" type="button">Check Places</button>
                <button id="submitEcgPlacement" class="btn btn-success w-100" type="button">Submit</button>
                <button id="resetEcgPlacement" class="btn btn-link btn-sm w-100 mt-2" type="button">Reset leads</button>
                <div id="ecgResult" class="small mt-3" aria-live="polite"></div>
            </div>`;
        renderLeadSelectionControls();
    }

    function setLeadPosition(id, position) {
        leadPositions[id] = position;
        const lead = document.getElementById(`lead-${id}`);
        if (!lead) return;
        lead.setAttribute('transform', `translate(${position.x} ${position.y})`);
    }

    function getPlacement() {
        return getConfiguredLeads().map((lead) => {
            const position = leadPositions[lead.id];
            const distance = Math.hypot(position.x - lead.target.x, position.y - lead.target.y);
            return { ...lead, correct: distance <= ACCEPTANCE_DISTANCE, distance };
        });
    }

    function checkPlacement(showMessage = true) {
        latestCheck = getPlacement();
        latestCheck.forEach((lead) => {
            const target = document.getElementById(`target-${lead.id}`);
            const status = document.getElementById(`ecg-status-${lead.id}`);
            target?.classList.toggle('correct', lead.correct);
            if (status) {
                status.classList.toggle('correct', lead.correct);
                status.classList.toggle('incorrect', !lead.correct);
                status.querySelector('span').textContent = lead.correct ? '✓' : '✕';
            }
        });
        const activeLeads = getConfiguredLeads();
        const correctCount = latestCheck.filter((lead) => lead.correct).length;
        if (showMessage) {
            const result = document.getElementById('ecgResult');
            result.className = `small mt-3 ${correctCount === activeLeads.length ? 'text-success' : 'text-danger'}`;
            result.textContent = correctCount === activeLeads.length
                ? `${activeLeads.length} ${activeLeads.length === 1 ? 'lead' : 'leads'} are correctly placed.`
                : `${correctCount} of ${activeLeads.length} ${activeLeads.length === 1 ? 'lead' : 'leads'} are correctly placed.`;
        }
        return correctCount === activeLeads.length;
    }

    function bindDragEvents() {
        const svg = document.getElementById('ecgSvg');
        if (!svg) return;
        let activeLead = null;

        const move = (event) => {
            if (!activeLead) return;
            const point = svg.createSVGPoint();
            point.x = event.clientX;
            point.y = event.clientY;
            const local = point.matrixTransform(svg.getScreenCTM().inverse());
            setLeadPosition(activeLead, {
                x: Math.max(LEAD_SIZE / 2, Math.min(VIEWBOX.width - LEAD_SIZE / 2, local.x)),
                y: Math.max(LEAD_SIZE / 2, Math.min(VIEWBOX.height - LEAD_SIZE / 2, local.y)),
            });
            checkPlacement(false);
        };
        const stop = (event) => {
            if (!activeLead) return;
            document.getElementById(`lead-${activeLead}`)?.classList.remove('dragging');
            activeLead = null;
            if (event?.pointerId !== undefined && svg.hasPointerCapture?.(event.pointerId)) {
                svg.releasePointerCapture(event.pointerId);
            }
            checkPlacement(false);
        };

        svg.querySelectorAll('.ecg-lead').forEach((lead) => {
            lead.addEventListener('pointerdown', (event) => {
                activeLead = lead.dataset.lead;
                lead.classList.add('dragging');
                svg.setPointerCapture?.(event.pointerId);
                event.preventDefault();
            });
        });
        svg.addEventListener('pointermove', move);
        svg.addEventListener('pointerup', stop);
        svg.addEventListener('pointercancel', stop);
    }

    function refreshStation() {
        const canvasContainer = document.getElementById('canvas-container');
        const panel = document.getElementById('station-control-panel');
        if (!canvasContainer || !panel) return;
        renderEcgStation(canvasContainer, panel);
        initialiseEcgStation();
    }

    function initialiseEcgStation() {
        bindDragEvents();
        document.getElementById('checkEcgPlacement')?.addEventListener('click', () => checkPlacement(true));
        document.getElementById('resetEcgPlacement')?.addEventListener('click', () => {
            leadPositions = defaultPositions();
            getConfiguredLeads().forEach((lead) => setLeadPosition(lead.id, leadPositions[lead.id]));
            document.querySelectorAll('.ecg-targets circle').forEach((target) => target.classList.remove('correct'));
            document.getElementById('ecgResult').textContent = '';
            document.querySelectorAll('.ecg-checklist-item').forEach((item) => {
                item.className = 'ecg-checklist-item';
                item.querySelector('span').textContent = '•';
            });
            latestCheck = null;
        });
        document.getElementById('submitEcgPlacement')?.addEventListener('click', () => {
            const isCorrect = checkPlacement(true);
            window.oscePracticalResult = isCorrect;
            if (isCorrect) setTimeout(() => window.Testing?.startMCQ(), 700);
        });
        document.getElementById('ecgLeadSetMode')?.addEventListener('change', (event) => {
            activeLeadSelectionMode = event.target.value;
            if (activeLeadSelectionMode !== 'group') {
                selectedLeadIds = getConfiguredLeadIds();
            }
            refreshStation();
        });
    }

    function getEcgResultDetails() {
        const placements = latestCheck || getPlacement();
        const correctCount = placements.filter((lead) => lead.correct).length;
        const activeLeads = getConfiguredLeads();
        return `<small class="text-muted d-block">ECG precordial lead placement</small><strong>${correctCount} / ${activeLeads.length} ${activeLeads.length === 1 ? 'lead' : 'leads'} correctly placed</strong>`;
    }

    function getEcgGrade() {
        const placements = latestCheck || getPlacement();
        // The complete station is worth one mark, awarded only when every
        // configured lead is placed correctly.
        const allCorrect = placements.length > 0 && placements.every((lead) => lead.correct);
        return { score: allCorrect ? 1 : 0, total: 1 };
    }

    const style = document.createElement('style');
    style.textContent = `
        #osce-station #canvas-container.ecg-sim-area { height: auto !important; min-height: 0 !important; padding: 0 !important; overflow: hidden; }
        .ecg-scene { position: relative; width: 100%; max-width: 900px; margin: auto; line-height: 0; }
        .ecg-trunk { display: block; width: 100%; height: auto; }
        .ecg-scene svg { position: absolute; inset: 0; width: 100%; height: 100%; }
        /* Keep the placement targets available to the checker, but do not show them. */
        .ecg-targets { display: none; }
        .ecg-targets circle { fill: rgba(255, 0, 0, .35); stroke: #dc2626; stroke-width: 2; transition: fill .15s, stroke .15s; }
        .ecg-targets circle.correct { fill: rgba(22, 163, 74, .36); stroke: #15803d; }
        .ecg-lead { cursor: grab; touch-action: none; filter: drop-shadow(0 2px 2px rgba(0,0,0,.28)); }
        .ecg-lead.dragging { cursor: grabbing; filter: drop-shadow(0 5px 4px rgba(0,0,0,.35)); }
        .ecg-lead-label { fill: #fff; font-family: Inter, sans-serif; font-size: 25px; font-weight: 700; text-anchor: middle; paint-order: stroke; stroke: rgba(0,0,0,.45); stroke-width: 3px; }
        .ecg-hint { position: absolute; left: 12px; bottom: 10px; padding: 7px 10px; border-radius: 6px; background: rgba(255,255,255,.9); color: #334155; font-size: 12px; line-height: 1.25; }
        .ecg-checklist-item { display: inline-flex; width: 50%; align-items: center; gap: 5px; font-size: 14px; padding: 3px 0; }
        .ecg-checklist-item.correct { color: #15803d; }.ecg-checklist-item.incorrect { color: #dc2626; }
        @media (max-width: 991.98px) { #osce-station .ecg-sim-area { height: auto !important; min-height: 0 !important; } }
    `;
    document.head.appendChild(style);

    window.Testing?.registerStation({
        id: 'ecg-station',
        title: 'ECG Precordial Lead Placement',
        instructions: 'Drag V1–V6 to their correct positions on the chest, check the placements, then submit.',
        renderControls: renderEcgStation,
        init: initialiseEcgStation,
        getPracticalResultDetails: getEcgResultDetails,
        getPracticalGrade: getEcgGrade,
    });
})();
