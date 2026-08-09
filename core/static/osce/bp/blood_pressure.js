// ============================================
// OSCE BLOOD PRESSURE SIMULATOR (Konva)
// ============================================

// change reading numbers on line 856

// Resolve media relative to this script so the embedded OSCE page always finds it.
const OSCE_ASSET_BASE = new URL('.', document.currentScript.src);
const osceAsset = (filename) => new URL(filename, OSCE_ASSET_BASE).href;

// Every station object is laid out in this single, fixed coordinate system.
const SCENE_WIDTH = 1200;
const SCENE_HEIGHT = 800;
const MOBILE_IMAGE_MULTIPLIER = 2;

const CONFIG = {
    PRESSURE_MIN: 0,
    PRESSURE_MAX: 310,
    PUMP_INCREMENT: 10,
    VALVE_LEAK_RATE: 1.5,
    TOLERANCE: 5,
    CUFF_POSITION_TOLERANCE: 40,
    STETH_POSITION_TOLERANCE: 70,
    // Anchor ratios define the target point on the arm for placing items.
    // Values are fractions measured from the arm bounding box's top-left corner.
    // For example CUFF_ANCHOR_Y: 0.8 means 80% down from the top of the arm bounding box.
    CUFF_ANCHOR_X: 0.5, // center of arm by default
    CUFF_ANCHOR_Y: 0.8,
    STETH_ANCHOR_X: 0.3, // slightly left of center for brachial artery
    STETH_ANCHOR_Y: 0.65,
    // Per-axis placement margins (pixels). Define the anchor "zone" rectangle
    // around the anchor point that the item's bounding box must overlap.
    // Adjust these to change how large the acceptable placement area is.
    CUFF_TOLERANCE_X: 80,
    CUFF_TOLERANCE_Y: 40,
    STETH_TOLERANCE_X: 5,
    STETH_TOLERANCE_Y: 10,
    // Hand placement and sizing match the interactive station on the dashboard.
    HAND_SCALE: 4,
    HAND_ANCHOR_X: 0.5,
    HAND_ANCHOR_Y: 0.3,
    HAND_TOLERANCE_X: 1,
    HAND_TOLERANCE_Y: 0.1,
    HAND_OFFSET_X: 48,
    HAND_OFFSET_Y: 8,
};

const state = {
    pressure: 0,
    maxPressure: 0,
    systolic: 120,
    diastolic: 80,
    cuffPlaced: false,
    stethPlaced: false,
    handPlaced: false,
    stethoscopeVisible: false,
    handVisible: false,
    uiHandlersBound: false,
    soundPhase: 'silence',
    answerSubmitted: false,
    isCorrect: false,
    submittedSystolic: null,
    submittedDiastolic: null,
    korotkoffPlaying: false,
    handPlacementEarned: false,
    cuffPlacementEarned: false,
    stethoscopePlacementEarned: false,
    readingResultEarned: false,
};

let stage, layer, scene, cuffShape, stethoscopeShape, handShape, pumpShape, armPlaceholderShape, mercuryShape;
let korotkoffAudio = null;
let normalAudio = null;
let armImageNode = null;
let cuffImageNode = null;
let stethImageNode = null;
let handImageNode = null;
let handPulseImageNode = null;
let handPulseInterval = null;
let handPulseShowsRed = false;
const HAND_PULSE_BPM = 80;
const HAND_PULSE_CYCLE_MS = 60000 / HAND_PULSE_BPM;
let mercuryImageNode = null;
let pumpImageNode = null;
let pressureBarTrack = null;
let pressureBarBase = null;
let pressureBarFill = null;

function initScene() {
    return new Promise((resolve) => {
    const container = document.getElementById('canvas-container');
    const existingToolbar = container.querySelector('.canvas-toolbar');
    container.innerHTML = '';
    if (existingToolbar) container.appendChild(existingToolbar);

    const width = Math.max(container.clientWidth, 100);
    const height = Math.max(container.clientHeight, 100);

    stage = new Konva.Stage({
        container: 'canvas-container',
        width,
        height,
    });
    if (existingToolbar && !container.querySelector('.canvas-toolbar')) container.appendChild(existingToolbar);

    layer = new Konva.Layer();
    stage.add(layer);
    scene = new Konva.Group();
    layer.add(scene);
    updateSceneViewport();

    const background = new Konva.Rect({
        x: 0,
        y: 0,
        width,
        height,
        fill: 'rgba(249,250,251,0)',
        cornerRadius: 20,
    });
    scene.add(background);

    // helper to load images
    function loadImage(src) {
        return new Promise((resolve, reject) => {
            const img = new window.Image();
            img.onload = () => resolve(img);
            img.onerror = (e) => reject(e);
            img.src = src;
        });
    }

    // Try to load `arm.png`, `cuff.png`, `stethoscope.png`, and `murcry.png`.
    // If loading fails, fall back to vector placeholders.
    Promise.all([loadImage(osceAsset('imgs/arm.png')), loadImage(osceAsset('imgs/cuff.png')), loadImage(osceAsset('imgs/stethoscope.png')), loadImage(osceAsset('imgs/murcry.png')), loadImage(osceAsset('imgs/hand.png')), loadImage(osceAsset('imgs/hand_pulse.png')), loadImage(osceAsset('imgs/pump.png'))])
        .then(([armImg, cuffImg, stethImg, murImg, handImg, handPulseImg, pumpImg]) => {
            armPlaceholderShape = new Konva.Group({
                    x: width * 0.38,
                y: height * 0.5,
                draggable: false,
            });
            const armImage = new Konva.Image({
                image: armImg,
                x: 0,
                y: 0,
                width: 100,
                height: 100,
                shadowColor: 'rgba(0,0,0,0.32)',
                shadowBlur: 28,
                shadowOffset: { x: 0, y: 12 },
                shadowOpacity: 0.5,
            });
            armImageNode = armImage;
            armPlaceholderShape.add(armImage);
            scene.add(armPlaceholderShape);

            cuffShape = new Konva.Group({
                    x: width * 0.38,
                y: height * 0.32,
                draggable: true,
                name: 'cuff',
                dragBoundFunc: boundScenePosition
            });
            const cuffImage = new Konva.Image({
                image: cuffImg,
                x: 0,
                y: 0,
                width: 80,
                height: 40,
                shadowColor: 'rgba(0,0,0,0.2)',
                shadowBlur: 12,
                shadowOffset: { x: 0, y: 6 },
                shadowOpacity: 0.35,
            });
            cuffImageNode = cuffImage;
            cuffShape.add(cuffImage);
            scene.add(cuffShape);
            // attach cuff event handlers after creation
            cuffShape.on('dragmove', checkPlacement);
            cuffShape.on('dragstart', () => { setCursor('grabbing'); updateStethZOrder(); });
            cuffShape.on('dragend', () => { setCursor('default'); updateStethZOrder(); });
            makeItemInteractive(cuffShape);
            // create stethoscope as image
            stethoscopeShape = new Konva.Group({
                    x: width * 0.38,
                y: height * 0.62,
                draggable: true,
                name: 'stethoscope',
                visible: false,
                dragBoundFunc: boundScenePosition
            });
            const STETH_SCALE = 0.3; // scale down stethoscope image
            const stethImage = new Konva.Image({
                image: stethImg,
                x: 0,
                y: 0,
                width: 60,
                height: 60,
                shadowColor: 'rgba(0,0,0,0.2)',
                shadowBlur: 10,
                shadowOffset: { x: 0, y: 5 },
                shadowOpacity: 0.35,
            });
            stethImageNode = stethImage;
            stethoscopeShape.add(stethImage);
            scene.add(stethoscopeShape);
            // attach stethoscope handlers
            stethoscopeShape.on('dragmove', () => { checkPlacement(); updateStethZOrder(); });
            stethoscopeShape.on('dragstart', () => setCursor('grabbing'));
            stethoscopeShape.on('dragend', () => { setCursor('default'); updateStethZOrder(); });
            makeItemInteractive(stethoscopeShape);
                // ensure correct stacking order after creation
                updateStethZOrder();
            handShape = new Konva.Group({
                x: cuffShape.x() + CONFIG.HAND_OFFSET_X,
                y: cuffShape.y() + CONFIG.HAND_OFFSET_Y,
                draggable: true,
                name: 'hand',
                visible: false,
                dragBoundFunc: boundScenePosition,
            });
            handImageNode = new Konva.Image({
                image: handImg,
                x: 0,
                y: 0,
                width: 100,
                height: 100,
                shadowColor: 'rgba(0,0,0,0.2)',
                shadowBlur: 12,
                shadowOffset: { x: 0, y: 6 },
                shadowOpacity: 0.35,
            });
            handShape.add(handImageNode);
            handPulseImageNode = new Konva.Image({ image: handPulseImg, visible: false, listening: false });
            handShape.add(handPulseImageNode);
            handShape.on('dragmove', checkPlacement);
            handShape.on('dragstart', () => setCursor('grabbing'));
            handShape.on('dragend', () => setCursor('default'));
            makeItemInteractive(handShape);
            scene.add(handShape);
            pumpShape = new Konva.Group({ x: width * 0.14, y: height * 0.78, draggable: false, name: 'pump' });
            pumpImageNode = new Konva.Image({ image: pumpImg, x: 0, y: 0, width: 70, height: 70 });
            pumpShape.add(pumpImageNode);
            pumpShape.on('click tap', pumpPressure);
            pumpShape.on('mouseenter', () => setCursor('pointer'));
            pumpShape.on('mouseleave', () => setCursor('default'));
            makeItemInteractive(pumpShape);
            scene.add(pumpShape);
            // add non-draggable mercury image on the right (scaled 1.5x)
            mercuryShape = new Konva.Group({ x: width * 0.86, y: height * 0.5, draggable: false, name: 'mercury' });
            const mercuryImage = new Konva.Image({
                image: murImg,
                x: 0,
                y: 0,
                width: 120, // 80 * 1.5
                height: 240, // 160 * 1.5
                shadowColor: 'rgba(0,0,0,0.3)',
                shadowBlur: 16,
                shadowOffset: { x: 0, y: 8 },
                shadowOpacity: 0.45,
            });
            mercuryImageNode = mercuryImage;
            mercuryShape.add(mercuryImage);
            scene.add(mercuryShape);
            pressureBarTrack = new Konva.Rect({
                x: mercuryShape.x() - 10,
                y: height * 0.18 - 8,
                width: 20,
                height: height * 0.60 + 16,
                fill: '#ccc',
                stroke: '#999',
                strokeWidth: 1,
                cornerRadius: 0,
                listening: false,
            });
            const baseYOffset = 1;
            pressureBarBase = new Konva.Rect({
                x: mercuryShape.x() - 10,
                y: height * 0.18 + height * 0.60 - (height * 0.60 / (CONFIG.PRESSURE_MAX / CONFIG.PUMP_INCREMENT)) - baseYOffset,
                width: 20,
                height: height * 0.60 / (CONFIG.PRESSURE_MAX / CONFIG.PUMP_INCREMENT),
                fill: '#999',
                cornerRadius: 0,
                listening: false,
            });
            pressureBarFill = new Konva.Rect({
                x: mercuryShape.x() - 10,
                y: height * 0.18 + height * 0.60 - (height * 0.60 / (CONFIG.PRESSURE_MAX / CONFIG.PUMP_INCREMENT)) - baseYOffset,
                width: 20,
                height: 0,
                fill: '#555',
                cornerRadius: 0,
                listening: false,
            });
            scene.add(pressureBarTrack, pressureBarFill);
            // layout shapes responsively once images are ready
            layoutShapes();
            layer.draw();
            resolve();
        })
        .catch(() => {
            // fallback placeholders if images fail to load
            armPlaceholderShape = new Konva.Group({
                    x: width * 0.38,
                y: height * 0.5,
                draggable: false,
            });
            const armRect = new Konva.Rect({
                x: -90,
                y: -120,
                width: 180,
                height: 280,
                fill: '#f1c27d',
                cornerRadius: 90,
                shadowColor: 'rgba(0,0,0,0.18)',
                shadowBlur: 20,
                shadowOffset: { x: 0, y: 10 },
                shadowOpacity: 0.35,
            });
            const armLabel = new Konva.Text({
                x: -80,
                y: 110,
                width: 160,
                text: 'Arm Placeholder',
                fontSize: 18,
                fill: '#555',
                align: 'center',
            });
            armPlaceholderShape.add(armRect, armLabel);
            scene.add(armPlaceholderShape);

            cuffShape = new Konva.Group({
                    x: width * 0.38,
                y: height * 0.32,
                draggable: true,
                name: 'cuff',
                dragBoundFunc: boundScenePosition
            });
            cuffShape.add(
                new Konva.Rect({
                    x: -80,
                    y: -30,
                    width: 160,
                    height: 60,
                    fill: '#1e88e5',
                    cornerRadius: 28,
                    shadowColor: 'rgba(0,0,0,0.2)',
                    shadowBlur: 12,
                    shadowOffset: { x: 0, y: 6 },
                    shadowOpacity: 0.35,
                }),
                new Konva.Text({
                    x: -78,
                    y: -22,
                    width: 156,
                    text: 'Cuff',
                    fontSize: 18,
                    fill: '#fff',
                    align: 'center',
                })
            );
            scene.add(cuffShape);
            // attach cuff event handlers after creation (fallback)
            cuffShape.on('dragmove', checkPlacement);
            cuffShape.on('dragstart', () => { setCursor('grabbing'); updateStethZOrder(); });
            cuffShape.on('dragend', () => { setCursor('default'); updateStethZOrder(); });
            makeItemInteractive(cuffShape);
            // fallback stethoscope as vector shapes
            stethoscopeShape = new Konva.Group({
                    x: width * 0.38,
                y: height * 0.3,
                draggable: true,
                name: 'stethoscope',
                visible: false,
                dragBoundFunc: boundScenePosition
            });
            stethoscopeShape.add(
                new Konva.Circle({
                    x: 0,
                    y: 0,
                    radius: 36,
                    fill: '#333',
                    shadowColor: 'rgba(0,0,0,0.2)',
                    shadowBlur: 10,
                    shadowOffset: { x: 0, y: 5 },
                    shadowOpacity: 0.35,
                }),
                new Konva.Rect({
                    x: -24,
                    y: -10,
                    width: 48,
                    height: 20,
                    fill: '#1a1a1a',
                    cornerRadius: 8,
                }),
                new Konva.Text({
                    x: -44,
                    y: 36,
                    width: 88,
                    text: 'Stethoscope',
                    fontSize: 14,
                    fill: '#fff',
                    align: 'center',
                })
            );
            scene.add(stethoscopeShape);
            stethoscopeShape.on('dragmove', () => { checkPlacement(); updateStethZOrder(); });
            stethoscopeShape.on('dragstart', () => setCursor('grabbing'));
            stethoscopeShape.on('dragend', () => { setCursor('default'); updateStethZOrder(); });
            makeItemInteractive(stethoscopeShape);
                // ensure correct stacking order after creation (fallback)
                // layout fallback shapes responsively
                // add fallback mercury placeholder on right
                // fallback mercury placeholder (scaled 1.5x)
                mercuryShape = new Konva.Group({ x: width * 0.86, y: height * 0.5, draggable: false, name: 'mercury' });
                mercuryShape.add(
                    new Konva.Rect({ x: -42, y: -112, width: 84, height: 224, fill: '#bbb', cornerRadius: 14, shadowColor: 'rgba(0,0,0,0.12)', shadowBlur: 8, shadowOffset: { x: 0, y: 4 }, shadowOpacity: 0.2 }),
                    new Konva.Text({ x: -48, y: 126, width: 96, text: 'Mercury', fontSize: 12, fill: '#333', align: 'center' })
                );
                scene.add(mercuryShape);
                pressureBarTrack = new Konva.Rect({
                    x: mercuryShape.x() - 10,
                    y: height * 0.18 - 8,
                    width: 20,
                    height: height * 0.60 + 16,
                    fill: '#ccc',
                    stroke: '#999',
                    strokeWidth: 1,
                    cornerRadius: 0,
                    listening: false,
                });
                pressureBarBase = new Konva.Rect({
                    x: mercuryShape.x() - 10,
                    y: height * 0.18 + height * 0.60 - (height * 0.60 / (CONFIG.PRESSURE_MAX / CONFIG.PUMP_INCREMENT)),
                    width: 20,
                    height: height * 0.60 / (CONFIG.PRESSURE_MAX / CONFIG.PUMP_INCREMENT),
                    fill: '#999',
                    cornerRadius: 0,
                    listening: false,
                });
                pressureBarFill = new Konva.Rect({
                    x: mercuryShape.x() - 10,
                    y: height * 0.18 + height * 0.60 - (height * 0.60 / (CONFIG.PRESSURE_MAX / CONFIG.PUMP_INCREMENT)),
                    width: 20,
                    height: 0,
                    fill: '#555',
                    cornerRadius: 0,
                    listening: false,
                });
                scene.add(pressureBarTrack, pressureBarFill);
                layoutShapes();
                updateStethZOrder();
                resolve();
        });

            // in case image loading hangs, ensure resolve after a timeout
            setTimeout(() => { try { resolve(); } catch (e) {} }, 1000);
        });

    window.addEventListener('resize', onWindowResize);
    checkPlacement();
    layer.draw();
}

function setCursor(value) {
    stage.container().style.cursor = value;
}

function boundScenePosition(pos) {
    const scale = scene ? scene.scaleX() : 1;
    const sceneX = scene ? scene.x() : 0;
    const padX = SCENE_WIDTH * 0.05;
    const localX = Math.min(Math.max((pos.x - sceneX) / scale, padX), SCENE_WIDTH - padX);
    const stagePad = 12;
    return {
        x: sceneX + localX * scale,
        // The mobile viewport is taller than the 3:2 scene. Bound vertical
        // dragging to the actual stage so the full visible area stays usable.
        y: Math.min(Math.max(pos.y, stagePad), stage.height() - stagePad),
    };
}

function makeItemInteractive(shape) {
    shape.setAttr('selected', false);
    shape.on('mouseenter', () => {
        setCursor('pointer');
        shape.setAttr('hovered', true);
        updateItemShadow(shape);
        layer.batchDraw();
    });
    shape.on('mouseleave', () => {
        setCursor('default');
        shape.setAttr('hovered', false);
        updateItemShadow(shape);
        layer.batchDraw();
    });
    shape.on('click tap', () => {
        shape.setAttr('selected', !shape.getAttr('selected'));
        updateItemShadow(shape);
        layer.batchDraw();
    });
}

function updateItemShadow(shape) {
    const highlighted = shape.getAttr('hovered') || shape.getAttr('selected');
    const selected = shape.getAttr('selected');
    shape.getChildren().forEach((child) => {
        if (child.getAttr('baseShadowBlur') === undefined) {
            child.setAttr('baseShadowBlur', child.shadowBlur() || 0);
            child.setAttr('baseShadowOpacity', child.shadowOpacity() || 0);
            child.setAttr('baseShadowOffsetY', (child.shadowOffset() || { y: 0 }).y || 0);
        }
        child.shadowColor(highlighted ? (selected ? 'rgba(13, 110, 253, 0.75)' : 'rgba(0, 0, 0, 0.55)') : 'rgba(0, 0, 0, 0)');
        child.shadowBlur(highlighted ? 20 : child.getAttr('baseShadowBlur'));
        child.shadowOpacity(highlighted ? 0.9 : child.getAttr('baseShadowOpacity'));
        child.shadowOffset({ x: 0, y: highlighted ? 8 : child.getAttr('baseShadowOffsetY') });
    });
}

function onWindowResize() {
    const container = document.getElementById('canvas-container');
    const width = Math.max(container.clientWidth, 100);
    const height = Math.max(container.clientHeight, 100);
    stage.width(width);
    stage.height(height);
    updateSceneViewport();
    layer.batchDraw();
}

function updateSceneViewport() {
    if (!stage || !scene) return;
    const scale = Math.min(stage.width() / SCENE_WIDTH, stage.height() / SCENE_HEIGHT);
    scene.scale({ x: scale, y: scale });
    scene.position({
        x: (stage.width() - SCENE_WIDTH * scale) / 2,
        y: (stage.height() - SCENE_HEIGHT * scale) / 2,
    });
}

function layoutPressureBar() {
    if (!pressureBarTrack || !pressureBarBase || !pressureBarFill || !mercuryShape) return;

    // Keep the mercury column locked to the gauge image, rather than to the
    // canvas height. This makes both shrink and grow by exactly the same ratio.
    const mercuryWidth = (mercuryImageNode && mercuryImageNode.width()) || 84;
    const mercuryHeight = (mercuryImageNode && mercuryImageNode.height()) || 224;
    const barWidth = mercuryWidth * (20 / 120);
    // Keep the taller range proportional to the gauge image at every viewport.
    // A fixed pixel addition looks correct on desktop but becomes oversized on mobile.
    const barHeight = mercuryHeight * 0.76;
    const barX = mercuryShape.x() - barWidth / 2;
    const barY = mercuryShape.y() - barHeight / 2 - mercuryHeight * 0.024;

    pressureBarTrack.position({ x: barX, y: barY });
    pressureBarTrack.size({ width: barWidth, height: barHeight });
    pressureBarBase.x(barX);
    pressureBarBase.width(barWidth);
    pressureBarFill.x(barX);
    pressureBarFill.width(barWidth);
    updatePressureBar();
}

function layoutShapes() {
    if (!stage || !layer) return;
    const w = SCENE_WIDTH;
    const h = SCENE_HEIGHT;

    // Arm image / placeholder
    if (armPlaceholderShape) {
        if (armImageNode && armImageNode.image()) {
            const img = armImageNode.image();
            const isMobile = window.matchMedia(
                '(max-width: 760px), (min-width: 1000px) and (max-width: 1050px)'
            ).matches;
            // Make the arm more compact on desktop while giving it more presence on mobile.
            // The scene itself always uses 1200×800 coordinates, so use the
            // actual viewport width to select the larger mobile artwork size.
            
            const armRatio = isMobile ? 0.50 : (w > 1200 ? 0.30 : 0.33);
            const armW = Math.min(w * armRatio, img.width * 0.9);
            const armH = armW * (img.height / img.width);
            const armScale = isMobile ? 0.6 * MOBILE_IMAGE_MULTIPLIER : 0.65;
            const scaledArmW = armW * armScale;
            const scaledArmH = armH * armScale;
            armImageNode.width(scaledArmW);
            armImageNode.height(scaledArmH);
            armImageNode.x(-scaledArmW / 2);
            armImageNode.y(-scaledArmH / 2);
        }
        armPlaceholderShape.x(w * 0.38);
        // center the arm vertically
        armPlaceholderShape.y(h * 0.5);
    }

    // Cuff image / fallback — size proportionally to the arm width
    if (cuffShape) {
        const armWRef = (armImageNode && armImageNode.width()) ? armImageNode.width() : Math.max(80, w * 0.35);
        // desired ratio of cuff width relative to arm width
        const CUFF_TO_ARM_RATIO = 0.9; // cuff ≈90% of arm width (increased)
        if (cuffImageNode && cuffImageNode.image()) {
            const img = cuffImageNode.image();
            const cuffW = Math.max(36, armWRef * CUFF_TO_ARM_RATIO);
            const cuffH = cuffW * (img.height / img.width);
            cuffImageNode.width(cuffW);
            cuffImageNode.height(cuffH);
            cuffImageNode.x(-cuffW / 2);
            cuffImageNode.y(-cuffH / 2);
        } else {
            const rect = cuffShape.findOne('Rect');
            const txt = cuffShape.findOne('Text');
            if (rect) {
                const rectW = Math.max(60, armWRef * CUFF_TO_ARM_RATIO);
                const rectH = Math.max(24, rectW * 0.35);
                rect.width(rectW);
                rect.height(rectH);
                rect.x(-rectW / 2);
                rect.y(-rectH / 2);
                if (txt) {
                    txt.width(rectW - 4);
                    txt.x(-(rectW - 4) / 2);
                    txt.y(-rectH / 2 + Math.max(6, rectH * 0.2));
                }
            }
        }
        // Keep vertical positioning here; horizontal (x) is set on reset or by user drag
        cuffShape.y(h * 0.33);
    }

    // Stethoscope image / fallback — size proportionally to the arm width
    if (stethoscopeShape) {
        const armWRef = (armImageNode && armImageNode.width()) ? armImageNode.width() : Math.max(60, w * 0.35);
        // desired ratio of steth width relative to arm width
        const STETH_TO_ARM_RATIO = 0.30; // steth ≈30% of arm width (increased)
        if (stethImageNode && stethImageNode.image()) {
            const img = stethImageNode.image();
            const stethW = Math.max(20, armWRef * STETH_TO_ARM_RATIO);
            const stethH = stethW * (img.height / img.width);
            stethImageNode.width(stethW);
            stethImageNode.height(stethH);
            stethImageNode.x(-stethW / 2);
            stethImageNode.y(-stethH / 2);
        } else {
            const circ = stethoscopeShape.findOne('Circle');
            const rect = stethoscopeShape.findOne('Rect');
            const txt = stethoscopeShape.findOne('Text');
            if (circ) {
                const r = Math.max(12, Math.min(armWRef * STETH_TO_ARM_RATIO * 0.5, 60));
                circ.radius(r);
                // center circle
                circ.x(0);
                circ.y(0);
            }
            if (rect) {
                rect.x(- (rect.width() || 48) / 2);
                rect.y(-10);
            }
            if (txt) {
                txt.x(- (txt.width() || 80) / 2);
                txt.y((circ ? circ.radius() : 36) + 6);
            }
        }
        // Keep vertical positioning here; horizontal (x) is set on reset or by user drag
        stethoscopeShape.y(h * 0.62);
    }

    // Mercury image / placeholder — keep it anchored to the right
    // Keep the hand proportionate to the arm and initially aligned beside the cuff.
    if (handShape && cuffShape) {
        const armWRef = (armImageNode && armImageNode.width()) ? armImageNode.width() : Math.max(60, w * 0.35);
        const HAND_TO_ARM_RATIO = 0.35;
        if (handImageNode && handImageNode.image()) {
            const img = handImageNode.image();
            const handW = Math.max(26, armWRef * HAND_TO_ARM_RATIO * CONFIG.HAND_SCALE);
            const handH = handW * (img.height / img.width);
            handImageNode.width(handW);
            handImageNode.height(handH);
            handImageNode.x(-handW / 2);
            handImageNode.y(-handH / 2);
            // hand_pulse.png is a tightly cropped version of hand.png with a red contour.
            if (handPulseImageNode) {
                handPulseImageNode.position({
                    x: -handW / 2 + handW * (69 / 1890),
                    y: -handH / 2 + handH * (368 / 1417),
                });
                handPulseImageNode.width(handW * (1747 / 1890));
                handPulseImageNode.height(handH * (674 / 1417));
            }
        }
        // Keep the hand where the user placed it; its starting position is set
        // at the lower edge of the simulation by resetSession().

    }

    if (mercuryShape) {
        const armWRef = (armImageNode && armImageNode.width()) ? armImageNode.width() : Math.max(80, w * 0.35);
        if (mercuryImageNode && mercuryImageNode.image()) {
            const img = mercuryImageNode.image();
            const scaleMul = 1.8;
            const merW = Math.min(armWRef * 0.35 * scaleMul, img.width * 0.8);
            const merH = merW * (img.height / img.width);
            mercuryImageNode.width(merW);
            mercuryImageNode.height(merH);
            mercuryImageNode.x(-merW / 2);
            mercuryImageNode.y(-merH / 2);
        }
        // anchor near right edge and center vertically
        mercuryShape.x(w * 0.86);
        mercuryShape.y(h * 0.5);
    }

    // Size and position the pump relative to the mercury gauge, as in index.html.
    if (pumpShape) {
        const armWRef = (armImageNode && armImageNode.width()) ? armImageNode.width() : Math.max(80, w * 0.35);
        const mercuryRefWidth = (mercuryImageNode && mercuryImageNode.width())
            ? mercuryImageNode.width()
            : armWRef * 0.35 * 1.8;
        const mercuryRefHeight = (mercuryImageNode && mercuryImageNode.height())
            ? mercuryImageNode.height()
            : mercuryRefWidth * (1757 / 369);
        // The pump is a fixed fraction of the gauge, so it scales cleanly on mobile.
        const pumpW = mercuryRefWidth * 0.64;
        const pumpAspect = (pumpImageNode && pumpImageNode.image())
            ? pumpImageNode.image().naturalHeight / Math.max(1, pumpImageNode.image().naturalWidth)
            : 1;
        const pumpH = pumpW * pumpAspect;
        if (pumpImageNode && pumpImageNode.image()) {
            pumpImageNode.width(pumpW);
            pumpImageNode.height(pumpH);
            pumpImageNode.x(-pumpW / 2);
            pumpImageNode.y(-pumpH / 2);
        }
        const mercuryCenterX = mercuryShape ? mercuryShape.x() : w * 0.86;
        pumpShape.x(mercuryCenterX - mercuryRefWidth / 2 - pumpW - mercuryRefWidth * 0.13);
        pumpShape.y((mercuryShape ? mercuryShape.y() : h * 0.5) + mercuryRefHeight * 0.28);
    }

    layoutPressureBar();
    layer.batchDraw();
}

function checkPlacement() {
    // shapes may be created asynchronously (image load); ensure they exist
    if (!armPlaceholderShape || !cuffShape || !stethoscopeShape) return;

    // Client rectangles are measured after the scene-group scale is applied,
    // so scale the placement tolerances by that same value.
    const sceneScale = scene ? scene.scaleX() : 1;

    const armPos = armPlaceholderShape.getClientRect();
    const cuffPos = cuffShape.getClientRect();
    const stethPos = stethoscopeShape.getClientRect();

    // compute target anchor point on the arm (lower margin by default)
    const cuffTargetX = armPos.x + armPos.width * CONFIG.CUFF_ANCHOR_X;
    const cuffTargetY = armPos.y + armPos.height * CONFIG.CUFF_ANCHOR_Y;

    // Determine an anchor "zone" rectangle around the cuff target point.
    // The cuff is considered correctly placed if its bounding box overlaps this zone.
    const cuffZone = {
        x: cuffTargetX - (CONFIG.CUFF_TOLERANCE_X * sceneScale) / 2,
        y: cuffTargetY - (CONFIG.CUFF_TOLERANCE_Y * sceneScale) / 2,
        width: CONFIG.CUFF_TOLERANCE_X * sceneScale,
        height: CONFIG.CUFF_TOLERANCE_Y * sceneScale,
    };
    // Check rectangle overlap between cuff bounding box and cuffZone
    const cuffOverlap = !(cuffPos.x + cuffPos.width < cuffZone.x ||
                            cuffPos.x > cuffZone.x + cuffZone.width ||
                            cuffPos.y + cuffPos.height < cuffZone.y ||
                            cuffPos.y > cuffZone.y + cuffZone.height);
    state.cuffPlaced = !!cuffOverlap;
    state.cuffPlacementEarned = state.cuffPlacementEarned || state.cuffPlaced;

    // compute stethoscope anchor on the arm (configurable)
    const stethTargetX = armPos.x + armPos.width * CONFIG.STETH_ANCHOR_X;
    const stethTargetY = armPos.y + armPos.height * CONFIG.STETH_ANCHOR_Y;
    // Stethoscope: use a similar anchor zone rectangle for placement checks
    const stethZone = {
        x: stethTargetX - (CONFIG.STETH_TOLERANCE_X * sceneScale) / 2,
        y: stethTargetY - (CONFIG.STETH_TOLERANCE_Y * sceneScale) / 2,
        width: CONFIG.STETH_TOLERANCE_X * sceneScale,
        height: CONFIG.STETH_TOLERANCE_Y * sceneScale,
    };
    const stethOverlap = !(stethPos.x + stethPos.width < stethZone.x ||
                            stethPos.x > stethZone.x + stethZone.width ||
                            stethPos.y + stethPos.height < stethZone.y ||
                            stethPos.y > stethZone.y + stethZone.height);
    state.stethPlaced = !!stethOverlap && stethoscopeShape.visible();
    state.stethoscopePlacementEarned = state.stethoscopePlacementEarned || state.stethPlaced;

    if (handShape) {
        const handPos = handShape.getClientRect();
        const handTargetX = armPos.x + armPos.width * CONFIG.HAND_ANCHOR_X;
        const handTargetY = armPos.y + armPos.height * CONFIG.HAND_ANCHOR_Y;
        const handZone = {
            x: handTargetX - (CONFIG.HAND_TOLERANCE_X * sceneScale) / 2,
            y: handTargetY - (CONFIG.HAND_TOLERANCE_Y * sceneScale) / 2,
            width: CONFIG.HAND_TOLERANCE_X * sceneScale,
            height: CONFIG.HAND_TOLERANCE_Y * sceneScale,
        };
        // Only the fingertips need to touch the pulse point, rather than the whole hand image.
        const handPlacementRect = {
            x: handPos.x,
            y: handPos.y + handPos.height * 0.25,
            width: Math.max(1, handPos.width * 0.1),
            height: Math.max(1, handPos.height * 0.5),
        };
        const handOverlap = !(handPlacementRect.x + handPlacementRect.width < handZone.x || handPlacementRect.x > handZone.x + handZone.width || handPlacementRect.y + handPlacementRect.height < handZone.y || handPlacementRect.y > handZone.y + handZone.height);
        state.handPlaced = !!handOverlap && handShape.visible();
        state.handPlacementEarned = state.handPlacementEarned || state.handPlaced;
    }

    // update checklist UI only; do not change canvas visuals (exam must not reveal placement)
    updatePlacementUI();
    updateHandPulseEffect();
    // update korotkoff playback in case placement changed
    handleKorotkoffPlayback();
    layer.batchDraw();
}

function snapCuffToArm() {
    if (!armPlaceholderShape || !cuffShape) return;
    const armRect = armPlaceholderShape.getClientRect();
    const targetX = armRect.x + armRect.width * CONFIG.CUFF_ANCHOR_X;
    const targetY = armRect.y + armRect.height * CONFIG.CUFF_ANCHOR_Y;
    const cuffRect = cuffShape.getClientRect();
    const cuffCenterX = cuffRect.x + cuffRect.width / 2;
    const cuffCenterY = cuffRect.y + cuffRect.height / 2;
    const dx = targetX - cuffCenterX;
    const dy = targetY - cuffCenterY;
    const dist = Math.hypot(dx, dy);
    if (dist < CONFIG.CUFF_POSITION_TOLERANCE * 1.5) {
        const absPos = cuffShape.getAbsolutePosition();
        cuffShape.setAbsolutePosition({ x: absPos.x + dx, y: absPos.y + dy });
        layer.batchDraw();
        checkPlacement();
    }
}

function updateStethZOrder() {
    // Ensure the stethoscope is stacked above the arm but below the cuff.
    // We enforce this by moving the stethoscope to top, then moving the cuff to top.
    if (!armPlaceholderShape || !stethoscopeShape || !cuffShape) return;
    try {
        // move stethoscope above arm
        stethoscopeShape.moveToTop();
        // ensure cuff remains above stethoscope
        cuffShape.moveToTop();
        layer.batchDraw();
    } catch (e) {
        // shapes may not be ready; ignore
    }
}

function resetSession() {
    const randomMultipleOfFive = (min, max) => {
        const steps = Math.floor((max - min) / 5) + 1;
        return min + Math.floor(Math.random() * steps) * 5;
    };
    const configuredPressure = window.OSCE_BLOOD_PRESSURE || {};
    state.systolic = Number.isFinite(configuredPressure.systolic)
        ? configuredPressure.systolic
        : randomMultipleOfFive(110, 150);
    state.diastolic = Number.isFinite(configuredPressure.diastolic)
        ? configuredPressure.diastolic
        : state.systolic - 40;
    state.pressure = 0;
    state.maxPressure = 0;
    state.soundPhase = 'silence';
    state.answerSubmitted = false;
    state.isCorrect = false;
    state.submittedSystolic = null;
    state.submittedDiastolic = null;
    state.handPlaced = false;
    state.stethoscopeVisible = false;
    state.handVisible = false;
    state.handPlacementEarned = false;
    state.cuffPlacementEarned = false;
    state.stethoscopePlacementEarned = false;
    state.readingResultEarned = false;

    document.getElementById('pressureDisplay').textContent = '0 mmHg';
    document.getElementById('pressureBar').style.width = '0%';
    document.getElementById('valveSlider').value = 0;
    document.getElementById('valveValue').textContent = '0%';
    document.getElementById('systolicInput').value = '';
    document.getElementById('diastolicInput').value = '';
    document.getElementById('systolicValue').textContent = state.systolic;
    document.getElementById('diastolicValue').textContent = state.diastolic;
    document.getElementById('statusBox').className = 'status-box status-pending';
    document.getElementById('statusBox').textContent = 'Waiting for input...';

    // Position cuff and stethoscope to the left of the arm by default.
    // If arm and images are available, compute left edge and offset accordingly.
    if (cuffShape) {
        let cuffX = SCENE_WIDTH * 0.2;
        const cuffY = SCENE_HEIGHT * 0.33;
        if (armPlaceholderShape && armImageNode && armImageNode.width()) {
            const armCenterX = armPlaceholderShape.x();
            const armLeft = armCenterX + (armImageNode.x() || 0);
            const armWref = armImageNode.width();
            const cuffW = (cuffImageNode && cuffImageNode.width()) ? cuffImageNode.width() : Math.max(36, armWref * 0.9);
            const margin = Math.max(20, armWref * 0.12);
            cuffX = armLeft - cuffW / 2 - margin;
            // nudge cuff slightly to the right relative to this computed left position
            const cuffRightNudge = Math.max(12, Math.round(armWref * 0.04));
            cuffX += cuffRightNudge;
        } else {
            // fallback nudge when arm metrics are not available
            cuffX += 30;
        }
        cuffShape.position({ x: cuffX, y: cuffY });
    }
    if (stethoscopeShape) {
        let stethX = SCENE_WIDTH * 0.2 + 40;
        const stethY = SCENE_HEIGHT * 0.62;
        if (armPlaceholderShape && armImageNode && armImageNode.width()) {
            const armCenterX = armPlaceholderShape.x();
            const armLeft = armCenterX + (armImageNode.x() || 0);
            const armWref = armImageNode.width();
            const stethW = (stethImageNode && stethImageNode.width()) ? stethImageNode.width() : Math.max(20, armWref * 0.3);
            const margin = Math.max(14, armWref * 0.08);
            stethX = armLeft - stethW / 2 - margin - Math.max(6, stethW * 0.2);
        }
        stethoscopeShape.position({ x: stethX, y: stethY });
        stethoscopeShape.visible(false);
    }
    if (handShape) {
        positionHandAboveStethoscope();
        setHandVisible(false);
    }
    document.getElementById('toggleStethoscopeButton').classList.remove('active');
    document.getElementById('toggleHandButton').classList.remove('active');
    layer.batchDraw();
    updatePressureBar();
    checkPlacement();
    updateSoundIndicator();
}

function positionHandAboveStethoscope() {
    if (!handShape || !stage) return;
    const handHeight = (handImageNode && handImageNode.height()) || 80;
    const stethoscopeY = SCENE_HEIGHT * 0.62;
    const gap = 30;
    handShape.position({
        x: SCENE_WIDTH * 0.5,
        y: Math.max(handHeight / 2 + 20, stethoscopeY - handHeight / 2 - gap),
    });
}

function updatePressure(deltaTime) {
    const valveLevel = parseInt(document.getElementById('valveSlider').value, 10);
    if (valveLevel > 0) {
        const leakAmount = (valveLevel / 100) * CONFIG.VALVE_LEAK_RATE;
        state.pressure = Math.max(CONFIG.PRESSURE_MIN, state.pressure - leakAmount);
        updateSoundPhase();
    }
    updatePressureDisplay();
}

function updatePressureDisplay() {
    const display = document.getElementById('pressureDisplay');
    const bar = document.getElementById('pressureBar');
    const percent = (state.pressure / CONFIG.PRESSURE_MAX) * 100;
    display.textContent = Math.round(state.pressure) + ' mmHg';
    bar.style.width = percent + '%';
    updatePressureBar();
    updateSoundPhase();
}

function updatePressureBar() {
    if (!pressureBarFill || !pressureBarTrack || !pressureBarTrack.height() || !pressureBarBase) return;
    const totalHeight = pressureBarTrack.height();
    const steps = CONFIG.PRESSURE_MAX / CONFIG.PUMP_INCREMENT;
    const heightPerStep = totalHeight / steps;
    const baseHeight = heightPerStep;
    const fillSteps = state.pressure / CONFIG.PUMP_INCREMENT;
    const fillHeight = Math.min(totalHeight - baseHeight, Math.round(fillSteps * heightPerStep));
    const baseYOffset = 1;
    pressureBarFill.height(fillHeight);
    pressureBarFill.y(pressureBarTrack.y() + totalHeight - baseHeight - fillHeight - baseYOffset);
    pressureBarFill.x(pressureBarTrack.x());
    pressureBarBase.height(baseHeight);
    pressureBarBase.y(pressureBarTrack.y() + totalHeight - baseHeight - baseYOffset);
    layer.batchDraw();
}

function updateSoundPhase() {
    let newPhase = 'silence';
    if (state.pressure >= state.systolic && state.pressure < state.diastolic) {
        if (state.pressure < state.systolic + 10) {
            newPhase = 'tapping';
        } else if (state.pressure >= state.diastolic - 5) {
            newPhase = 'fading';
        } else {
            newPhase = 'continuous';
        }
    }
    if (newPhase !== state.soundPhase) {
        state.soundPhase = newPhase;
        playSoundPhase();
    }
    updateSoundIndicator();
    // pressure changed; update korotkoff playback
    handleKorotkoffPlayback();
}

function handleKorotkoffPlayback() {
    const inKorotkoffRange = (state.pressure <= state.systolic && state.pressure >= state.diastolic);
    const shouldPlayNormalSound = state.stethoscopeVisible;
    const shouldPlayKorotkoffSound = state.stethoscopeVisible && state.stethPlaced && inKorotkoffRange;

    if (normalAudio) {
        try {
            if (shouldPlayNormalSound) {
                if (normalAudio.paused) {
                    normalAudio.currentTime = 0;
                    const p = normalAudio.play();
                    if (p && p.then) {
                        p.catch(() => {});
                    }
                }
            } else {
                normalAudio.pause();
                normalAudio.currentTime = 0;
            }
        } catch (e) {}
    }

    if (!korotkoffAudio) return;
    if (shouldPlayKorotkoffSound) {
        if (!state.korotkoffPlaying) {
            // try to play; some browsers require user interaction
            korotkoffAudio.currentTime = 0;
            const p = korotkoffAudio.play();
            if (p && p.then) {
                p.then(() => { state.korotkoffPlaying = true; }).catch(() => { state.korotkoffPlaying = false; });
            } else {
                state.korotkoffPlaying = true;
            }
        }
    } else {
        if (state.korotkoffPlaying) {
            try { korotkoffAudio.pause(); korotkoffAudio.currentTime = 0; } catch (e) {}
            state.korotkoffPlaying = false;
        }
    }
}

function playSoundPhase() {
    try {
        const context = new (window.AudioContext || window.webkitAudioContext)();
        if (state.soundPhase === 'tapping') {
            playTone(context, 200, 0.1, 0.2);
        } else if (state.soundPhase === 'continuous') {
            playTone(context, 250, 0.15, 0.2);
            playTone(context, 300, 0.15, 0.2, 0.15);
        } else if (state.soundPhase === 'fading') {
            playTone(context, 150, 0.08, 0.15);
        }
    } catch (e) {
        // ignore unavailable audio
    }
}

function playTone(context, frequency, duration, volume, delay = 0) {
    const osc = context.createOscillator();
    const gain = context.createGain();
    osc.connect(gain);
    gain.connect(context.destination);
    osc.frequency.value = frequency;
    gain.gain.setValueAtTime(volume, context.currentTime + delay);
    gain.gain.exponentialRampToValueAtTime(0.01, context.currentTime + delay + duration);
    osc.start(context.currentTime + delay);
    osc.stop(context.currentTime + delay + duration);
}

function updateSoundIndicator() {
    const indicator = document.getElementById('soundIndicator');
    const labels = {
        silence: '🔇 No Sound',
        tapping: '🔊 Tapping (Systolic)',
        continuous: '🔊 Thumping (Flowing)',
        fading: '🔊 Fading (Diastolic)',
    };
    indicator.textContent = labels[state.soundPhase];
    indicator.className = 'sound-indicator';
    if (state.soundPhase !== 'silence') indicator.classList.add('playing');
}

function updateHandPulseEffect() {
    if (!handImageNode || !handPulseImageNode || !layer) return;
    // A correctly placed cuff occludes the pulse above systolic pressure.
    // If the cuff is misplaced, the pulse remains detectable regardless of pressure.
    const shouldPulse = state.handVisible && state.handPlaced &&
        (!state.cuffPlaced || state.pressure < state.systolic);
    if (shouldPulse) {
        if (handPulseInterval === null) {
            handPulseShowsRed = false;
            handImageNode.visible(true);
            handPulseImageNode.visible(false);
            // Swap outlines every half beat: one white → red → white cycle is 750 ms (80 BPM).
            handPulseInterval = window.setInterval(() => {
                handPulseShowsRed = !handPulseShowsRed;
                handImageNode.visible(!handPulseShowsRed);
                handPulseImageNode.visible(handPulseShowsRed);
                layer.batchDraw();
            }, HAND_PULSE_CYCLE_MS / 2);
        }
    } else {
        if (handPulseInterval !== null) {
            window.clearInterval(handPulseInterval);
            handPulseInterval = null;
        }
        handPulseShowsRed = false;
        handImageNode.visible(true);
        handPulseImageNode.visible(false);
    }
}

function updatePlacementUI() {
    const cuffIcon = document.getElementById('cuffIcon');
    const stethIcon = document.getElementById('stethIcon');

    if (state.cuffPlaced) {
        cuffIcon.textContent = '✓';
        cuffIcon.className = 'checklist-icon correct';
    } else {
        cuffIcon.textContent = '✗';
        cuffIcon.className = 'checklist-icon incorrect';
    }

    if (state.stethPlaced) {
        stethIcon.textContent = '✓';
        stethIcon.className = 'checklist-icon correct';
    } else {
        stethIcon.textContent = '✗';
        stethIcon.className = 'checklist-icon incorrect';
    }
}

function getScoringSummary() {
    const criteria = [
        { label: 'Hand placed on the arm', achieved: state.handPlacementEarned },
        { label: 'Cuff placed correctly', achieved: state.cuffPlacementEarned },
        { label: 'Stethoscope placed correctly', achieved: state.stethoscopePlacementEarned },
        { label: 'Systolic and diastolic result correct', achieved: state.readingResultEarned },
    ];
    const totalDegree = criteria.filter((criterion) => criterion.achieved).length;
    return { criteria, totalDegree };
}

function submitAnswer() {
    const systolicInput = parseInt(document.getElementById('systolicInput').value, 10);
    const diastolicInput = parseInt(document.getElementById('diastolicInput').value, 10);
    if (isNaN(systolicInput) || isNaN(diastolicInput)) {
        window.oscePracticalResult = false;
        setTimeout(() => window.Testing?.startMCQ(), 0);
        return;
    }
    state.answerSubmitted = true;
    state.submittedSystolic = systolicInput;
    state.submittedDiastolic = diastolicInput;
    const systolicCorrect = Math.abs(systolicInput - state.systolic) <= 5;
    const diastolicCorrect = Math.abs(diastolicInput - state.diastolic) <= 5;
    const placementCorrect = state.cuffPlaced && state.stethPlaced && state.handPlaced;
    state.isCorrect = systolicCorrect && diastolicCorrect;
    state.readingResultEarned = state.readingResultEarned || state.isCorrect;
    const statusBox = document.getElementById('statusBox');
    const { criteria, totalDegree } = getScoringSummary();
    const rightItems = criteria.filter((criterion) => criterion.achieved).map((criterion) => `• ${criterion.label}`).join('<br>');
    const wrongItems = criteria.filter((criterion) => !criterion.achieved).map((criterion) => `• ${criterion.label}`).join('<br>');
    const allCorrect = totalDegree === criteria.length;

    statusBox.className = `status-box ${allCorrect ? 'status-correct' : 'status-incorrect'}`;
    statusBox.innerHTML = `
        <strong>${totalDegree}/4 degree</strong><br><br>
        <span style="color:${allCorrect ? '#198754' : '#dc3545'}">Right:</span><br>${rightItems || '• None'}<br><br>
        <span style="color:${allCorrect ? '#198754' : '#dc3545'}">Wrong:</span><br>${wrongItems || '• None'}
    `;
    window.oscePracticalResult = allCorrect;
    setTimeout(() => window.Testing?.startMCQ(), 700);
}

function setupUIHandlers() {
    if (state.uiHandlersBound) return;
    state.uiHandlersBound = true;
    document.getElementById('pumpButton').addEventListener('click', pumpPressure);
    document.getElementById('resetButton').addEventListener('click', resetSession);
    document.getElementById('submitButton').addEventListener('click', submitAnswer);
    document.getElementById('valveSlider').addEventListener('input', (e) => {
        document.getElementById('valveValue').textContent = e.target.value + '%';
    });
    document.getElementById('toggleStethoscopeButton').addEventListener('click', () => {
        if (!stethoscopeShape) return;
        stethoscopeShape.visible(!stethoscopeShape.visible());
        state.stethoscopeVisible = stethoscopeShape.visible();
        document.getElementById('toggleStethoscopeButton').classList.toggle('active', state.stethoscopeVisible);
        checkPlacement();
        layer.draw();
    });
    document.getElementById('toggleHandButton').addEventListener('click', toggleHandVisibility);
}

function setHandVisible(visible) {
    if (!handShape) return;
    state.handVisible = visible;
    handShape.visible(visible);
    handShape.listening(visible);
    if (!visible) {
        state.handPlaced = false;
        updatePlacementUI();
        updateHandPulseEffect();
    } else {
        checkPlacement();
    }
    const toggleButton = document.getElementById('toggleHandButton');
    if (toggleButton) toggleButton.classList.toggle('active', visible);
    if (layer) layer.batchDraw();
}

function toggleHandVisibility() {
    if (handShape) setHandVisible(!state.handVisible);
}

function pumpPressure() {
    if (state.pressure < CONFIG.PRESSURE_MAX) {
        state.pressure += CONFIG.PUMP_INCREMENT;
        state.maxPressure = Math.max(state.maxPressure, state.pressure);
        updatePressureDisplay();
        updateSoundPhase();
    }
}

function animate() {
    requestAnimationFrame(animate);
    updatePressure(1);
    updateHandPulseEffect();
}

function initializeBloodPressureStation() {
    setTimeout(() => {
        try {
            initScene().then(() => {
                // initScene finished layout; now wire UI and start session
                setupUIHandlers();
                resetSession();
                animate();
                console.log('Konva OSCE Simulator initialized successfully');
            }).catch((e) => {
                console.error('initScene error:', e);
                // fallback to still initializing UI so user can interact
                setupUIHandlers();
                resetSession();
                animate();
            });
            // prepare normal ambient audio and korotkoff audio (files should be in workspace root)
            try {
                normalAudio = new Audio(osceAsset('sounds/normalSound.m4a'));
                normalAudio.preload = 'auto';
                normalAudio.loop = true;
                normalAudio.volume = 1;
            } catch (e) {
                normalAudio = null;
            }
            try {
                korotkoffAudio = new Audio(osceAsset('sounds/krotokoff.m4a'));
                korotkoffAudio.preload = 'auto';
                korotkoffAudio.loop = false;
                korotkoffAudio.volume = 1.0;
                korotkoffAudio.onended = () => {
                    if (state.stethoscopeVisible && state.stethPlaced && state.pressure <= state.systolic && state.pressure >= state.diastolic) {
                        korotkoffAudio.currentTime = 0;
                        const p = korotkoffAudio.play();
                        if (p && p.then) {
                            p.then(() => { state.korotkoffPlaying = true; }).catch(() => { state.korotkoffPlaying = false; });
                        } else {
                            state.korotkoffPlaying = true;
                        }
                    } else {
                        state.korotkoffPlaying = false;
                    }
                };
            } catch (e) {
                korotkoffAudio = null;
            }
        } catch (e) {
            console.error('Initialization error:', e);
            alert('Error initializing simulator: ' + e.message);
        }
    }, 100);
}

function renderBloodPressureControls(canvasContainer, panel) {
    canvasContainer.innerHTML = `<div class="canvas-toolbar">
        <button id="toggleStethoscopeButton" class="btn btn-light" type="button" title="Show/Hide stethoscope">&#129658;</button>
        <button id="toggleHandButton" class="btn btn-light" type="button" title="Show/Hide hand">&#9995;</button>
    </div>`;
    panel.innerHTML = `<div class="panel-section card p-3 mb-3"><h3 class="h5">Valve Release</h3><div class="d-flex justify-content-between small mb-1"><span>Release</span><span id="valveValue">0%</span></div><input type="range" id="valveSlider" class="form-range" min="0" max="100" value="0"></div>
        <div class="panel-section card p-3"><h3 class="h5">Your Answer</h3><div class="d-flex flex-column gap-2 mb-3"><input type="number" id="systolicInput" class="form-control" placeholder="Systolic" min="0" max="200"><input type="number" id="diastolicInput" class="form-control" placeholder="Diastolic" min="0" max="200"></div><button class="btn btn-success w-100" id="submitButton">Submit Answer</button><div id="statusBox" class="small mt-3"></div></div>
        <div class="station-logic-only" aria-hidden="true"><button id="pumpButton" type="button"></button><button id="resetButton" type="button"></button><div id="pressureDisplay"></div><div id="pressureBar"></div><span id="systolicValue"></span><span id="diastolicValue"></span><div id="cuffIcon"></div><div id="stethIcon"></div><div id="soundIndicator"></div></div>`;
}

function getBloodPressureResultDetails() {
    const placement = state.cuffPlaced && state.stethPlaced && state.handPlaced;
    const reading = state.answerSubmitted ? `${state.submittedSystolic}/${state.submittedDiastolic} mmHg` : 'No reading submitted';
    const criteria = [
        { label: 'Hand placed on the arm ( paplatory method used )', achieved: state.handPlacementEarned },
        { label: 'Cuff placed correctly', achieved: state.cuffPlacementEarned },
        { label: 'Stethoscope placed correctly ( auscultation method used )', achieved: state.stethoscopePlacementEarned },
        { label: 'Systolic/diastolic result correct', achieved: state.readingResultEarned },
    ];
    const totalDegree = criteria.filter((criterion) => criterion.achieved).length;
    const rightItems = criteria.filter((criterion) => criterion.achieved).map((criterion) => `<div>✓ ${criterion.label}</div>`).join('');
    const wrongItems = criteria.filter((criterion) => !criterion.achieved).map((criterion) => `<div>✗ ${criterion.label}</div>`).join('');

    return `
        <small class="text-muted d-block">Blood pressure reading</small>
        <strong>${reading}</strong>
        <small class="d-block mt-2">Target: ${state.systolic}/${state.diastolic} mmHg</small>
        <div class="mt-2"><strong>${totalDegree} / 4 degree</strong></div>
        <div class="mt-2 text-success">Right:</div>${rightItems || '<div>• None</div>'}
        <div class="mt-2 text-danger">Wrong:</div>${wrongItems || '<div>• None</div>'}
    `;
}

function getBloodPressureGrade() {
    // The complete station is worth one mark, awarded only when all checks pass.
    return { score: getScoringSummary().totalDegree === 4 ? 1 : 0, total: 1 };
}

window.Testing?.registerStation({
    id: 'blood-pressure',
    title: 'Blood Pressure OSCE',
    instructions: 'Measure the patient\'s blood pressure using the station below.',
    renderControls: renderBloodPressureControls,
    init: initializeBloodPressureStation,
    getPracticalResultDetails: getBloodPressureResultDetails,
    getPracticalGrade: getBloodPressureGrade,
    /* Station-specific questions moved to osce_exam.html:
    questions: [
        { q: 'Where should the stethoscope be placed during a BP exam?', options: ['Over the brachial artery', 'Over the radial artery', 'Over the carotid artery', 'Over the femoral artery'], correct: 0 },
        { q: 'What is the normal systolic blood pressure range?', options: ['80–90 mmHg', '100–120 mmHg', '140–160 mmHg', '180–200 mmHg'], correct: 1 },
        { q: 'Which sound indicates systolic pressure during auscultation?', options: ['First Korotkoff sound', 'Muffling sound', 'Absence of sound', 'Loud bruit'], correct: 0 }
    ] */
});
