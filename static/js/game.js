// /shadowrun_quest/static/js/game.js
document.addEventListener('DOMContentLoaded', () => {
    // --- DOM элементы ---
    const textModeContainer = document.getElementById('text-mode-container');
    const gameTextEl = document.getElementById('game-text');
    const choicesContainerEl = document.getElementById('choices-container');
    const inputAreaEl = document.getElementById('input-area');
    const playerInputEl = document.getElementById('player-input');
    const submitInputBtn = document.getElementById('submit-input');

    const combatModeContainer = document.getElementById('combat-mode-container');
    const combatCanvas = document.getElementById('combat-canvas');
    const combatLogEl = document.getElementById('combat-log');
    const combatChoicesEl = document.getElementById('combat-choices');
    const ctx = combatCanvas.getContext('2d');

    const minigameContainer = document.getElementById('minigame-container');
    const minigameCanvas = document.getElementById('minigame-canvas');
    const minigameLogEl = document.getElementById('minigame-log');
    const minigameChoicesEl = document.getElementById('minigame-choices');
    const mg_ctx = minigameCanvas.getContext('2d');

    // --- Константы для рендеринга боя ---
    const TILE_SIZE = 50;
    const PLAYER_COLOR = '#00ff41';
    const ENEMY_COLOR = '#ff4141';
    const RANGE_COLOR = 'rgba(0, 255, 65, 0.3)';

    const sceneBackgroundEl = document.getElementById('scene-background');

    let currentCombatState = null;

    // --- Главная функция обновления ---
    function update(data) {
        // Обновляем фон сцены
        if (data.background_image) {
            sceneBackgroundEl.style.backgroundImage = `url(${data.background_image})`;
        }

        // Проверяем, есть ли в ответе сервера активный боевой режим
        if (data.minigame && data.minigame.active) {
            renderMinigameMode(data);
        } else if (data.combat && data.combat.active) {
            renderCombatMode(data);
        } else {
            renderTextMode(data);
        }
    }

    // --- Рендеринг текстового режима ---
    function renderTextMode(data) {
        combatModeContainer.style.display = 'none';
        minigameContainer.style.display = 'none';
        textModeContainer.style.display = 'flex';

        gameTextEl.innerText = data.description;
        choicesContainerEl.innerHTML = '';
        data.choices.forEach(choice => {
            const button = document.createElement('button');
            button.innerText = choice.text;
            button.dataset.action = choice.action;
            if (choice.target) button.dataset.target = choice.target;
            choicesContainerEl.appendChild(button);
        });
        inputAreaEl.style.display = data.show_input ? 'block' : 'none';
    }

    // --- Рендеринг тактического режима ---
    function renderCombatMode(data) {
        textModeContainer.style.display = 'none';
        minigameContainer.style.display = 'none';
        combatModeContainer.style.display = 'flex';
        currentCombatState = data.combat;

        // Обновляем лог и кнопки
        combatLogEl.innerText = data.description;
        combatChoicesEl.innerHTML = '';
        data.choices.forEach(choice => {
            const button = document.createElement('button');
            button.innerText = choice.text;
            button.dataset.action = choice.action;
            combatChoicesEl.appendChild(button);
        });

        // Рендерим канвас
        drawGrid(currentCombatState.grid_size);
        drawMovementRange(data.player.stats, currentCombatState.player_pos);
        drawUnit(currentCombatState.player_pos, PLAYER_COLOR, data.player.stats);
        drawUnit(currentCombatState.enemy_pos, ENEMY_COLOR, currentCombatState.enemy);
    }

    // --- Рендеринг режима мини-игры ---
    function renderMinigameMode(data) {
        textModeContainer.style.display = 'none';
        combatModeContainer.style.display = 'none';
        minigameContainer.style.display = 'flex';

        minigameLogEl.innerText = data.description;
        minigameChoicesEl.innerHTML = '';
        data.choices.forEach(choice => {
            const button = document.createElement('button');
            button.innerText = choice.text;
            button.dataset.action = choice.action;
            minigameChoicesEl.appendChild(button);
        });

        // Draw minigame
        const mg = data.minigame;
        const TILE_SIZE_MG = 50; // minigame tile size
        mg_ctx.clearRect(0, 0, minigameCanvas.width, minigameCanvas.height);

        // Draw grid
        mg_ctx.strokeStyle = 'rgba(65, 160, 255, 0.2)';
        for (let x = 0; x < mg.grid_size[0]; x++) {
            for (let y = 0; y < mg.grid_size[1]; y++) {
                mg_ctx.strokeRect(x * TILE_SIZE_MG, y * TILE_SIZE_MG, TILE_SIZE_MG, TILE_SIZE_MG);
            }
        }

        // Draw path
        mg_ctx.strokeStyle = '#ffff00'; // Yellow path
        mg_ctx.lineWidth = 4;
        mg_ctx.beginPath();
        mg_ctx.moveTo(mg.path[0][0] * TILE_SIZE_MG + TILE_SIZE_MG / 2, mg.path[0][1] * TILE_SIZE_MG + TILE_SIZE_MG / 2);
        for (let i = 1; i < mg.path.length; i++) {
            mg_ctx.lineTo(mg.path[i][0] * TILE_SIZE_MG + TILE_SIZE_MG / 2, mg.path[i][1] * TILE_SIZE_MG + TILE_SIZE_MG / 2);
        }
        mg_ctx.stroke();
        mg_ctx.lineWidth = 1;

        // Draw nodes
        const drawNode = (pos, color) => {
            mg_ctx.fillStyle = color;
            mg_ctx.beginPath();
            mg_ctx.arc(pos[0] * TILE_SIZE_MG + TILE_SIZE_MG / 2, pos[1] * TILE_SIZE_MG + TILE_SIZE_MG / 2, TILE_SIZE_MG / 4, 0, 2 * Math.PI);
            mg_ctx.fill();
        };
        drawNode(mg.start_node, '#00ff41'); // Green start
        drawNode(mg.end_node, '#41a0ff'); // Blue end
    }

    function drawGrid(gridSize) {
        ctx.clearRect(0, 0, combatCanvas.width, combatCanvas.height);
        ctx.strokeStyle = 'rgba(0, 255, 65, 0.2)';
        for (let x = 0; x < gridSize[0]; x++) {
            for (let y = 0; y < gridSize[1]; y++) {
                ctx.strokeRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
            }
        }
    }

    function drawMovementRange(playerStats, playerPos) {
        const moveRange = playerStats.ap;
        ctx.fillStyle = RANGE_COLOR;
        for (let x = 0; x < currentCombatState.grid_size[0]; x++) {
            for (let y = 0; y < currentCombatState.grid_size[1]; y++) {
                const distance = Math.abs(x - playerPos[0]) + Math.abs(y - playerPos[1]);
                if (distance > 0 && distance <= moveRange) {
                    ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
                }
            }
        }
    }

    function drawUnit(pos, color, stats) {
        const x = pos[0] * TILE_SIZE;
        const y = pos[1] * TILE_SIZE;
        
        // Вместо квадрата здесь можно будет рисовать спрайт
        // ctx.drawImage(spriteImage, x, y, TILE_SIZE, TILE_SIZE);
        ctx.fillStyle = color;
        ctx.fillRect(x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10);

        // Рисуем полоску здоровья
        const hpPercentage = stats.hp / stats.max_hp;
        ctx.fillStyle = '#333';
        ctx.fillRect(x + 5, y, TILE_SIZE - 10, 4);
        ctx.fillStyle = (color === PLAYER_COLOR) ? PLAYER_COLOR : ENEMY_COLOR;
        ctx.fillRect(x + 5, y, (TILE_SIZE - 10) * hpPercentage, 4);
    }

    // --- Отправка действий на сервер ---
    async function sendAction(payload) {
        try {
            const response = await fetch('/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            update(data);
        } catch (error) {
            console.error("Ошибка при отправке действия:", error);
            gameTextEl.innerText = "Ошибка соединения с сервером. Попробуйте перезагрузить страницу.";
        }
    }

    // --- Обработчики событий ---
    choicesContainerEl.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') {
            const { action, target } = e.target.dataset;
            sendAction({ action, target });
        }
    });

    combatChoicesEl.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') {
            const { action } = e.target.dataset;
            sendAction({ action });
        }
    });

    minigameChoicesEl.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON') {
            const { action } = e.target.dataset;
            sendAction({ action });
        }
    });

    submitInputBtn.addEventListener('click', () => {
        sendAction({ action: 'talk_kage_submit', input: playerInputEl.value });
        playerInputEl.value = '';
    });

    combatCanvas.addEventListener('click', (e) => {
        if (!currentCombatState || !currentCombatState.active) return;

        const rect = combatCanvas.getBoundingClientRect();
        const x = Math.floor((e.clientX - rect.left) / TILE_SIZE);
        const y = Math.floor((e.clientY - rect.top) / TILE_SIZE);

        const enemyPos = currentCombatState.enemy_pos;
        const playerPos = currentCombatState.player_pos;
        
        // Если кликнули по врагу
        if (x === enemyPos[0] && y === enemyPos[1]) {
            sendAction({ action: 'combat_attack', target_pos: [x, y] });
        } 
        // Если кликнули по пустой клетке
        else if (x !== playerPos[0] || y !== playerPos[1]) {
            sendAction({ action: 'combat_move', target_pos: [x, y] });
        }
    });

    minigameCanvas.addEventListener('click', (e) => {
        if (!minigameContainer.style.display || minigameContainer.style.display === 'none') return;

        const TILE_SIZE_MG = 50;
        const rect = minigameCanvas.getBoundingClientRect();
        const x = Math.floor((e.clientX - rect.left) / TILE_SIZE_MG);
        const y = Math.floor((e.clientY - rect.top) / TILE_SIZE_MG);

        sendAction({ action: 'minigame_connect_node', target_pos: [x, y] });
    });


    // --- Запуск игры ---
    async function initGame() {
        const response = await fetch('/game_state');
        const data = await response.json();
        update(data);
    }

    initGame();
});
