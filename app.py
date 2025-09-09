# /shadowrun_quest/app.py

from flask import Flask, render_template, request, jsonify, url_for
import random

# --- Инициализация Flask ---
app = Flask(__name__)

# --- Игровая логика (почти без изменений) ---

# Начальное состояние игрока
def get_initial_player_state():
    return {
        "location": "apartment",
        "inventory": ["stimpak"], # Дадим один стимулятор для начала
        "credits": 100, # Уменьшим стартовые, чтобы побочный квест был полезнее
        "stats": {
            "hp": 60,
            "max_hp": 60,
            "attack": 6,
            "ap": 10,
            "max_ap": 10,
            "charisma": 3,
            "strength": 4
        },
        "implants": {
            "charisma": False
        },
        "quests": {
            "main_quest_step": "start", # 'start', 'need_key', 'has_key', 'data_hacked', 'meet_client', 'chapter_1_completed', 'chapter_2_start', 'chapter_2_find_processor', 'chapter_2_has_processor', 'chapter_2_fragment_location_known'
            "bartender_quest": "not_started", # 'not_started', 'started', 'completed', 'rewarded'
            "doc_razor_quest": "not_started", # 'not_started', 'started', 'has_component', 'completed'
            "substation_quest": "not_started", # 'not_started', 'started', 'completed', 'rewarded'
            "decker_quest": "not_started", # 'not_started', 'started', 'completed', 'rewarded',
            "decker_quest_2": "not_started", # 'not_started', 'started', 'completed', 'rewarded'
            "decker_location_inquired": False
        },
        "reputation": {
            "netrunners": 0
        },
        "combat": {
            "active": False,
            "enemy": None,
            "log": [],
            "is_defending": False,
            "grid_size": [15, 10], # width, height
            "player_pos": [0, 0],
            "enemy_pos": [0, 0]
        },
        "minigame": {
            "active": False,
            "type": None,
            "grid_size": [0, 0],
            "start_node": [0, 0],
            "end_node": [0, 0],
            "path": [],
            "completed": False
        },
    }

player = get_initial_player_state()

# Игровой мир
enemies = {
    "gang_member": {
        "name": "Панк из 'Хромированных Черепов'",
        "hp": 45,
        "max_hp": 45,
        "attack": 5,
        "ap": 8,
        "max_ap": 8,
        "reward_credits": 50
    }
}

shop_item_pool = {
    "stimpak": {
        "name": "Стимулятор",
        "price": 75,
        "chance": 0.6, # 60% шанс появления
        "description": "Стандартный армейский стимулятор. Восстанавливает немного здоровья."
    },
    "biomonitor_regulator": {
        "name": "Биомониторный регулятор",
        "price": 50,
        "quest_gate": ("doc_razor_quest", "started"),
        "description": "Редкая деталь для кибернетических протезов."
    },
    "quantum_processor": {
        "name": "Квантовый процессор",
        "price": 1000,
        "quest_gate": ("main_quest_step", "chapter_2_find_processor"),
        "description": "Древний, но невероятно мощный процессор. Основа для серьезных нетраннерских ригов."
    }
}


items = {
    "stimpak": {
        "name": "Стимулятор",
        "description": "Восстанавливает 25 HP.",
        "effect": "heal",
        "value": 25
    }
}

world = {
    "apartment": {
        "description": "Вы в своей тесной квартире. Неоновый свет Нео-Киото пробивается сквозь жалюзи. На столе гудит ваш старый терминал. В углу пылится видавший виды плащ.",
        "image": "apartment.jpg",
        "choices": [
            {"text": "Подойти к терминалу.", "action": "go", "target": "terminal"},
            {"text": "Выйти на улицы Нео-Киото.", "action": "go", "target": "neo_kyoto_streets"},
        ]
    },
    "terminal": {
        "description": "Экран терминала оживает, показывая знакомый интерфейс вашего личного Искина 'Kage'.",
        "image": "terminal.jpg",
        "effects": ["glitch"],
        "choices": [
            {"text": "Поговорить с 'Kage'.", "action": "talk_kage_prompt"},
            {"text": "Попробовать взломать сеть 'Арасаки'.", "action": "hack_arasaka"},
            {"text": "Отойти от терминала.", "action": "go", "target": "apartment"},
        ]
    },
    "neo_kyoto_streets": {
        "description": "Улицы Нео-Киото гудят жизнью. Дождь смешивается с неоном, отражаясь в лужах на асфальте. Мимо проносятся аэрокары, а толпа спешит по своим делам. Куда направитесь?",
        "image": "neo_kyoto_streets.jpg",
        "effects": ["rain"],
        "choices": [
            {"text": "Зайти в бар 'Забытый Бит'.", "action": "go", "target": "bar_forgotten_bit"},
            {"text": "Заглянуть в клинику риппердока.", "action": "go", "target": "doc_razors_clinic"},
            {"text": "Спуститься в 'Цифровое Погружение'.", "action": "go", "target": "digital_dive"},
            {"text": "Посетить лавку старьевщика.", "action": "go", "target": "junk_shop"},
            {"text": "Вернуться в квартиру.", "action": "go", "target": "apartment"},
        ],
        # Динамические выборы будут добавляться в коде
        "dynamic_choices": {
            "bartender_quest": {
                "text": "Свернуть в тёмный переулок.", "action": "go", "target": "back_alley"
            },
            "meet_client_quest": {
                "text": "Отправиться к башне 'Кусанаги'.", "action": "go", "target": "kusanagi_rooftop"
            }
        }
    },
    "bar_forgotten_bit": {
        "description": "В баре 'Забытый Бит' пахнет дешёвым синтетическим алкоголем и озоном от старой электроники. За стойкой протирает стакан угрюмый орк-бармен. В дальнем углу, склонившись над планшетом, сидит фигура в капюшоне.",
        "image": "bar_forgotten_bit.jpg",
        "effects": ["flicker"],
        "choices": [
            {"text": "Поговорить с барменом.", "action": "talk_bartender"},
            {"text": "Выйти на улицу.", "action": "go", "target": "neo_kyoto_streets"},
        ]
    },
    "back_alley": {
        "description": "Вонючий переулок завален мусором. В тусклом свете неоновой вывески трое панков с дешёвыми имплантами блокируют проход. Один из них, с хромированной челюстью, делает шаг вперёд.",
        "image": "back_alley.jpg",
        "effects": ["rain", "flicker"],
        "choices": [
            {"text": "Разобраться с проблемой бармена.", "action": "confront_gang"},
            {"text": "Молча развернуться и уйти.", "action": "go", "target": "neo_kyoto_streets"},
        ]
    },
    "doc_razors_clinic": {
        "description": "В стерильном помещении пахнет антисептиком и паленым металлом. На операционном столе лежит разобранный кибер-протез. Сам Док Рэйзор, человек с усталыми глазами и стальными пальцами, протирает скальпель.",
        "image": "doc_razors_clinic.jpg",
        "choices": [
            {"text": "Поговорить с Доком Рэйзором.", "action": "talk_doc_razor"},
            {"text": "Выйти на улицу.", "action": "go", "target": "neo_kyoto_streets"},
        ]
    },
    "junk_shop": {
        "description": "Лавка 'Железный Хлам' завалена горами старой электроники, сломанных дронов и ржавых имплантов. За прилавком сидит седой старик, копаясь в микросхемах с помощью лупы.",
        "image": "junk_shop.jpg",
        "effects": ["dust"],
        "choices": [
            {"text": "Поговорить со старьевщиком.", "action": "talk_shopkeeper"},
            {"text": "Выйти на улицу.", "action": "go", "target": "neo_kyoto_streets"},
        ]
    },
    "kusanagi_rooftop": {
        "description": "Вы на смотровой площадке башни 'Кусанаги'. Ветер треплет ваш плащ. Нео-Киото лежит под вами, как россыпь драгоценных камней. У края площадки стоит высокая фигура в идеально скроенном костюме и смотрит на город.",
        "image": "kusanagi_rooftop.jpg",
        "choices": [
            {"text": "Подойти к фигуре в костюме.", "action": "meet_mr_shadow"},
            {"text": "Пока не подходить.", "action": "go", "target": "neo_kyoto_streets"},
        ]
    },
    "digital_dive": {
        "description": "Вы в 'Цифровом Погружении', подвальном клубе для нетраннеров. Воздух густой от дыма и запаха озона. Десятки людей подключены к терминалам, их глаза пусты. За стойкой, заваленной проводами, стоит владелец клуба, тощий парень по имени Вектор. В углу за отдельным мощным ригом сидит девушка с волосами цвета фуксии.",
        "image": "digital_dive.jpg",
        "choices": [
            {"text": "Поговорить с Вектором.", "action": "talk_vector"},
            {"text": "Подойти к девушке с волосами цвета фуксии.", "action": "talk_cypher"},
            {"text": "Выйти на улицу.", "action": "go", "target": "neo_kyoto_streets"},
        ]
    },
    "substation_42": {
        "description": "Вы у подстанции 42. Гудение трансформаторов почти оглушает. Распределительный щит открыт, из него сыплются искры. Похоже, кто-то пытался его взломать и только всё испортил. Нужно перенаправить энергию, замкнув правильные контакты.",
        "image": "substation_42.jpg",
        "choices": [
            {"text": "Попробовать починить щит (Мини-игра).", "action": "substation_minigame"},
            {"text": "Уйти, пока не ударило током.", "action": "go", "target": "digital_dive"},
        ]
    },
    "arasaka_relay": {
        "description": "Вы у подножия огромной коммуникационной вышки 'Арасаки'. Периметр охраняется, но с ключ-картой Декера вы проходите через служебный вход. Перед вами главный терминал управления.",
        "image": "arasaka_relay.jpg",
        "choices": [
            {"text": "Попытаться саботировать ретранслятор.", "action": "sabotage_relay"},
            {"text": "Уйти, пока вас не заметили.", "action": "go", "target": "neo_kyoto_streets"},
        ]
    },
    "cybernesis_lab": {
        "description": "Заброшенная лаборатория 'Кибернесис' встречает вас тишиной и пылью. Повсюду разбросано оборудование и разбитые колбы. Похоже, эвакуация была поспешной. В центре зала стоит одинокий терминал, на экране которого слабо мерцает странный символ.",
        "image": "cybernesis_lab.jpg",
        "effects": ["dust", "flicker"],
        "choices": [
            {"text": "Подойти к терминалу.", "action": "approach_ai_fragment"},
            {"text": "Покинуть лабораторию.", "action": "go", "target": "neo_kyoto_streets"},
        ]
    },
    "ncpd_archive": {
        "description": "Вы в стерильном, холодном помещении архива данных NCPD. Ваш пропуск сработал, но вокруг снуют дроны-охранники. Нужно действовать быстро. Перед вами терминал с досье.",
        "image": "ncpd_archive.jpg",
        "choices": [
            {"text": "Попытаться стереть досье Декера.", "action": "erase_decker_file"},
            {"text": "Уйти, не привлекая внимания.", "action": "go", "target": "neo_kyoto_streets"},
        ]
    }
}

def _generate_shop_interface(player):
    """Генерирует динамический интерфейс магазина."""
    shop_inventory = []
    # Проверяем квестовые предметы
    for item_key, item_data in shop_item_pool.items():
        if "quest_gate" in item_data:
            quest_key, required_status = item_data["quest_gate"]
            # Убеждаемся, что квест существует в состоянии игрока
            if player["quests"].get(quest_key) == required_status and item_key not in player["inventory"]:
                shop_inventory.append(item_key)

    # Проверяем случайные предметы
    for item_key, item_data in shop_item_pool.items():
        if "chance" in item_data:
            if random.random() < item_data["chance"]:
                # Позволяем иметь в продаже до 2 стимуляторов
                if item_key == "stimpak" and shop_inventory.count("stimpak") < 2:
                    shop_inventory.append(item_key)
                elif item_key != "stimpak" and item_key not in shop_inventory:
                     shop_inventory.append(item_key)

    world["junk_shop"]["shop_inventory"] = shop_inventory

    description_parts = ["'Чего желаешь?' - ворчит старик. - 'Сегодня в продаже...'"]
    choices = []

    if not shop_inventory:
        description_parts.append("...а, впрочем, ничего интересного. Один хлам.")
    else:
        for item_key in sorted(list(set(shop_inventory))): # Сортируем для постоянного порядка
            item_data = shop_item_pool[item_key]
            description_parts.append(f"- {item_data['name']} ({item_data['price']} кредитов)")
            choices.append({"text": f"Купить: {item_data['name']}", "action": "buy_item_from_shop", "target": item_key})

    choices.append({"text": "Уйти.", "action": "go", "target": "neo_kyoto_streets"})
    return "\n".join(description_parts), choices

def talk_to_iskin(command):
    command = command.lower()
    quest_step = player["quests"]["main_quest_step"]

    if "миссия" in command or "задание" in command:
        if quest_step == "start":
            player["quests"]["main_quest_step"] = "need_key"
            return "ИСКИН 'Kage': Ваша цель - похитить архив 'Химера' из дата-центра 'Арасаки'. Их защита первоклассная. Вам понадобится 'Шифровальный ключ' последнего поколения, чтобы обойти их ICE. Я засек слухи, что такой ключ можно достать через информатора по кличке 'Глитч'. Последний раз его видели в баре 'Забытый Бит'."
        elif quest_step == "need_key":
            return "ИСКИН 'Kage': Вам все еще нужен 'Шифровальный ключ'. Ищите 'Глитча' в баре 'Забытый Бит'."
        elif quest_step == "has_key":
            return "ИСКИН 'Kage': Отлично, у вас есть ключ. Теперь вы можете попытаться взломать сеть 'Арасаки' с вашего терминала. Будьте осторожны."
        elif quest_step == "data_hacked":
            player["quests"]["main_quest_step"] = "meet_client"
            return "ИСКИН 'Kage': Получено зашифрованное сообщение. Отправитель: 'Мистер Шэдоу'. Содержание: 'Отличная работа. Принесите пакет на смотровую площадку башни Кусанаги. Я буду ждать.' Похоже, это ваш заказчик."
        elif quest_step == "meet_client":
            return "ИСКИН 'Kage': Заказчик ждет вас на смотровой площадке башни 'Кусанаги'. Не заставляйте его ждать слишком долго. 'Арасака' уже ищет вас."
        elif quest_step == "chapter_1_completed":
            player["quests"]["main_quest_step"] = "chapter_2_start"
            return "ИСКИН 'Kage': Снова сообщение от 'Мистера Шэдоу'. 'Данные 'Химеры' оказались фрагментом кода мощного, неконтролируемого ИИ. 'Арасака' пытается собрать его. Мы должны их опередить. Найдите нетраннера по кличке Сайфер в клубе 'Цифровое Погружение'. Она поможет отследить следующий фрагмент. Это наш новый контракт.'"
        elif quest_step == "chapter_2_start":
            return "ИСКИН 'Kage': Ваша цель - найти Сайфер в 'Цифровом Погружении' и заручиться ее помощью в поиске следующего фрагмента ИИ."
        elif quest_step == "chapter_2_find_processor":
            return "ИСКИН 'Kage': Сайфер нужен 'Квантовый процессор'. По слухам, такие раритеты иногда всплывают в лавке старьевщика. Но цена будет высокой."
        elif quest_step == "chapter_2_has_processor":
            return "ИСКИН 'Kage': У вас есть процессор. Отнесите его Сайфер в 'Цифровое Погружение'."
        elif quest_step == "chapter_2_fragment_location_known":
            return "ИСКИН 'Kage': Сайфер обнаружила следующий фрагмент. Он находится в заброшенной лаборатории 'Кибернесис'. Будьте осторожны, это неизведанная территория."
        elif quest_step == "chapter_2_completed":
            player["quests"]["main_quest_step"] = "chapter_3_start"
            return "ИСКИН 'Kage': Сообщение от 'Мистера Шэдоу'. 'Второй фрагмент у нас. Отлично. Но ИИ адаптируется. Он создал мощную защитную систему - 'Черный Лёд'. Чтобы получить следующий фрагмент, нам нужен военный ледокол. Я слышал, у вашего знакомого Декера мог остаться доступ к таким программам. Поговорите с ним. Это в его же интересах.'"
        elif quest_step == "chapter_3_start":
            return "ИСКИН 'Kage': Ваша цель - получить военный ледокол. Мистер Шэдоу предполагает, что Декер может помочь."
        elif quest_step == "chapter_3_has_icebreaker":
            player["quests"]["main_quest_step"] = "chapter_3_target_found"
            return "ИСКИН 'Kage': Ледокол у вас. Я проанализировал данные. 'Черный Лёд' защищает мобильный сервер 'Арасаки', который сейчас находится в бронированном конвое. Вам нужно перехватить его."
        elif quest_step == "chapter_3_target_found":
            return "ИСКИН 'Kage': Ваша цель - перехватить бронированный конвой 'Арасаки' и взломать мобильный сервер с помощью военного ледокола."



    elif "статус" in command:
        inventory_str = ", ".join(player['inventory']) if player['inventory'] else "пусто"
        hp_str = f"Здоровье: {player['stats']['hp']}/{player['stats']['max_hp']}"
        stats_str = f"Сила: {player['stats']['strength']}, Харизма: {player['stats']['charisma']}, Атака: {player['stats']['attack']}, ОД: {player['stats']['max_ap']}"
        rep_str = f"Репутация (Нетраннеры): {player['reputation']['netrunners']}"
        return f"ИСКИН 'Kage': Системы в норме. {hp_str}. Кредитов: {player['credits']}. Инвентарь: {inventory_str}. Ваши параметры: {stats_str}. {rep_str}."
    elif "справка" in command or "помощь" in command or "help" in command:
        return "ИСКИН 'Kage': Доступные команды: 'миссия', 'статус', 'журнал' (статус квестов), 'сканировать' (инфо о локации), 'справка'."
    elif "журнал" in command:
        main_quest_status = player['quests']['main_quest_step']
        bartender_quest_status = player['quests']['bartender_quest']
        doc_razor_quest_status = player['quests']['doc_razor_quest']
        return f"ИСКИН 'Kage': Журнал заданий:\n- Основная миссия: {main_quest_status}\n- Проблема с бандой: {bartender_quest_status}\n- Деталь для риппердока: {doc_razor_quest_status}"
    elif "сканировать" in command:
        if player['location'] == 'digital_dive':
            return "ИСКИН 'Kage': Сканирование... В клубе повышенный уровень сетевой активности. Девушка в углу использует кастомный риг с нестандартной архитектурой. Владелец, Вектор, имеет репутацию честного дельца."
        else:
            return "ИСКИН 'Kage': В данной локации нет примечательных данных для сканирования."
    else:
        return "ИСКИН 'Kage': Команда не распознана. Пожалуйста, уточните запрос."

# --- Маршруты Flask (API для нашей игры) ---

@app.route("/")
def index():
    """Отдает главную HTML страницу."""
    return render_template("index.html")

@app.route("/game_state")
def game_state():
    """Отправляет начальное состояние игры при загрузке страницы."""
    # Сброс состояния при перезагрузке страницы для простоты демонстрации
    player.clear(); player.update(get_initial_player_state())
    location_data = world[player["location"]]
    image_url = url_for('static', filename=f'images/{location_data.get("image", "default.jpg")}')
    effects = location_data.get("effects", [])

    return jsonify({
        "description": location_data["description"],
        "choices": location_data["choices"],
        "player": player,
        "combat": player["combat"],
        "background_image": image_url,
        "effects": effects
    })

@app.route("/action", methods=["POST"])
def handle_action():
    """Обрабатывает действие игрока."""
    data = request.json
    action = data.get("action")

    description = ""
    choices = []
    show_input = False
    background_image = ""
    effects = []

    # --- БЛОК ОБРАБОТКИ МИНИ-ИГРЫ ---
    if player.get("minigame", {}).get("active"):
        # Если активна мини-игра, все действия, кроме выхода, обрабатываются здесь
        if action != "minigame_exit":
            description, choices = handle_minigame_action(data, player)
            background_image = url_for('static', filename=f'images/{world[player["location"]].get("image", "default.jpg")}')
            effects = world[player["location"]].get("effects", [])
            return jsonify({
                "description": description,
                "choices": choices,
                "minigame": player["minigame"],
                "player": player,
                "combat": player["combat"],
                "background_image": background_image,
                "show_input": False,
                "effects": effects
            })
        # minigame_exit обрабатывается ниже в общем потоке

    # --- БЛОК ОБРАБОТКИ ТАКТИЧЕСКОГО БОЯ ---
    # Этот блок обрабатывает действия, когда бой уже активен.
    # Он получает действие от клиента (например, 'combat_move'),
    # вычисляет результат и возвращает новое состояние всего боя.
    if player.get("combat", {}).get("active"):
        combat_log = player["combat"]["log"]
        enemy = player["combat"]["enemy"]
        combat_log.clear() # Очищаем лог перед новым ходом

        # --- ХОД ИГРОКА: обработка одного действия ---
        player_action_handled = False
        target_pos = data.get("target_pos")

        if action == "combat_move":
            start_pos = player["combat"]["player_pos"]
            distance = abs(target_pos[0] - start_pos[0]) + abs(target_pos[1] - start_pos[1]) # Manhattan distance
            ap_cost = distance
            if player["stats"]["ap"] >= ap_cost:
                player["stats"]["ap"] -= ap_cost
                player["combat"]["player_pos"] = target_pos
                combat_log.append(f"Вы переместились. Потрачено {ap_cost} ОД.")
            else:
                combat_log.append(f"Недостаточно ОД для перемещения! (Требуется {ap_cost})")

        elif action == "combat_attack":
            start_pos = player["combat"]["player_pos"]
            distance = abs(target_pos[0] - start_pos[0]) + abs(target_pos[1] - start_pos[1])
            ap_cost = 4
            attack_range = 1 # Melee attack
            if distance <= attack_range and player["stats"]["ap"] >= ap_cost:
                player["stats"]["ap"] -= ap_cost
                player_damage = player["stats"]["attack"] + random.randint(0, 3)
                enemy["hp"] -= player_damage
                combat_log.append(f"Вы атаковали и нанесли {player_damage} урона.")
                player_action_handled = True
            elif distance > attack_range:
                combat_log.append("Цель слишком далеко для атаки.")
            else: # Not enough AP
                combat_log.append(f"Недостаточно ОД для атаки! (Требуется {ap_cost})")

            # Проверка победы
            if player_action_handled and enemy["hp"] <= 0:
                player["combat"]["active"] = False
                player["quests"]["bartender_quest"] = "completed"
                player["credits"] += enemy["reward_credits"]
                description = f"Вы победили '{enemy['name']}'!\nБанда разбегается.\n\n(Вы получили {enemy['reward_credits']} кредитов. Квест 'Проблема с бандой' может быть завершен.)"
                choices = [{"text": "Вернуться на улицы.", "action": "go", "target": "neo_kyoto_streets"}]
                background_image = url_for('static', filename=f'images/{world["neo_kyoto_streets"].get("image", "default.jpg")}')
                effects = world["neo_kyoto_streets"].get("effects", [])
                return jsonify({"description": description, "choices": choices, "combat": player["combat"], "player": player, "background_image": background_image, "effects": effects})

        # --- ЗАВЕРШЕНИЕ ХОДА И ХОД ПРОТИВНИКА ---
        elif action == "combat_end_turn":
            combat_log.append("Вы завершаете ход.")
            # Enemy AI
            enemy["ap"] = enemy["max_ap"]
            combat_log.append(f"Ход '{enemy['name']}'.")
            # Простая логика: двигаться к игроку и атаковать, если в радиусе
            player_pos = player["combat"]["player_pos"]
            enemy_pos = player["combat"]["enemy_pos"]
            distance = abs(player_pos[0] - enemy_pos[0]) + abs(player_pos[1] - enemy_pos[1])

            if distance <= 1: # Attack if in range
                enemy["ap"] -= 4
                enemy_damage = enemy["attack"] + random.randint(-1, 1)
                player["stats"]["hp"] -= enemy_damage
                combat_log.append(f"'{enemy['name']}' атакует и наносит вам {enemy_damage} урона.")
            elif enemy["ap"] > 0: # Move closer
                move_dist = min(enemy["ap"], 3) # Move up to 3 tiles
                # Move horizontally
                if player_pos[0] > enemy_pos[0]: enemy_pos[0] = min(player_pos[0], enemy_pos[0] + move_dist)
                elif player_pos[0] < enemy_pos[0]: enemy_pos[0] = max(player_pos[0], enemy_pos[0] - move_dist)
                # Move vertically
                elif player_pos[1] > enemy_pos[1]: enemy_pos[1] = min(player_pos[1], enemy_pos[1] + move_dist)
                elif player_pos[1] < enemy_pos[1]: enemy_pos[1] = max(player_pos[1], enemy_pos[1] - move_dist)
                player["combat"]["enemy_pos"] = enemy_pos
                combat_log.append(f"'{enemy['name']}' перемещается ближе к вам.")

            # Проверка поражения
            if player["stats"]["hp"] <= 0:
                player["combat"]["active"] = False; player["location"] = "apartment"; player["stats"]["hp"] = player["stats"]["max_hp"] // 2
                lost_credits = min(player["credits"], 50); player["credits"] -= lost_credits
                description = f"Вы теряете сознание... и приходите в себя в своей квартире. Голова раскалывается, а в кармане не хватает {lost_credits} кредитов."
                choices = world["apartment"]["choices"]
                background_image = url_for('static', filename=f'images/{world["apartment"].get("image", "default.jpg")}')
                effects = world["apartment"].get("effects", [])
                return jsonify({"description": description, "choices": choices, "combat": player["combat"], "player": player, "background_image": background_image, "effects": effects})

            # Начало нового хода игрока
            player["stats"]["ap"] = player["stats"]["max_ap"]
            combat_log.append("Ваш ход.")

        # --- ФОРМИРОВАНИЕ ОТВЕТА ДЛЯ ПРОДОЛЖЕНИЯ БОЯ ---
        background_image = url_for('static', filename=f'images/{world[player["location"]].get("image", "default.jpg")}')
        effects = world[player["location"]].get("effects", [])
        description = "\n".join(combat_log)
        choices = [{"text": "Завершить ход", "action": "combat_end_turn"}]
        return jsonify({"description": description, "choices": choices, "combat": player["combat"], "player": player, "background_image": background_image, "effects": effects})
    
    # Логика обработки действий
    if action == "go":
        target = data.get("target")
        player["location"] = target
        location_data = world[player["location"]]
        
        # Динамическое описание улиц
        if player["location"] == "neo_kyoto_streets" and player["quests"]["main_quest_step"] in ["data_hacked", "meet_client"]:
            description = "Улицы гудят, но в воздухе висит напряжение. Вы замечаете больше патрулей 'Арасаки', их красные визоры сканируют толпу. Похоже, корпорация взбешена."
        elif player["location"] == "neo_kyoto_streets" and player["quests"]["main_quest_step"] in ["chapter_2_start"]:
            description = "Патрулей 'Арасаки' стало меньше, но теперь на улицах можно заметить людей в штатском, внимательно осматривающих прохожих. Корпорация сменила тактику."
        else:
            description = location_data["description"]

        choices = list(location_data.get("choices", [])) # Make a copy to modify

        # Handle dynamic choices for streets
        if player["location"] == "neo_kyoto_streets":
            if player["quests"]["bartender_quest"] == "started":
                choices.append(location_data["dynamic_choices"]["bartender_quest"])
            if player["quests"]["main_quest_step"] == "meet_client":
                choices.append(location_data["dynamic_choices"]["meet_client_quest"])
            if player["quests"]["main_quest_step"] == "chapter_2_fragment_location_known":
                choices.append({"text": "Отправиться в лабораторию 'Кибернесис'.", "action": "go", "target": "cybernesis_lab"})
            if player["quests"].get("decker_quest_2") == "started":
                choices.append({"text": "Отправиться в архив NCPD.", "action": "go", "target": "ncpd_archive"})
            if player["quests"]["main_quest_step"] == "chapter_3_target_found":
                # В будущем здесь будет новая локация для перехвата конвоя
                choices.append({"text": "[ЗАГЛУШКА] Устроить засаду на конвой.", "action": "go", "target": "neo_kyoto_streets"})
            if player["quests"]["decker_quest"] == "started" and "relay_keycard" in player["inventory"]:
                choices.append({"text": "Отправиться к ретранслятору 'Арасаки'.", "action": "go", "target": "arasaka_relay"})

        # Динамические персонажи в баре
        if player["location"] == "bar_forgotten_bit":
            main_quest = player["quests"]["main_quest_step"]
            decker_is_available = player["quests"].get("decker_location_inquired", False) and player["quests"].get("decker_quest_2") != "rewarded"
            glitch_is_available = main_quest in ["need_key", "has_key"]

            # Глитч исчезает после взлома
            if glitch_is_available:
                 description = "В баре 'Забытый Бит' пахнет дешёвым синтетическим алкоголем и озоном от старой электроники. За стойкой протирает стакан угрюмый орк-бармен. В дальнем углу, склонившись над планшетом, сидит фигура в капюшоне."
                 choices.insert(1, {"text": "Подойти к фигуре в капюшоне (Глитч).", "action": "talk_glitch"})
            # Декер появляется после взлома и остается для новых квестов
            elif decker_is_available:
                 description = "В баре 'Забытый Бит' как обычно. Знакомый орк-бармен за стойкой. Фигура Глитча исчезла, но в углу теперь сидит суровый мужчина со шрамом, который внимательно вас изучает."
                 choices.insert(1, {"text": "Поговорить с ветераном в углу (Декер).", "action": "talk_decker"})
        
        # Динамические персонажи в клинике
        if player["location"] == "doc_razors_clinic":
            if player["quests"]["doc_razor_quest"] == "completed":
                description = "В клинике Дока Рэйзора чисто и пахнет антисептиком. Сам Док работает над протезом. На кушетке сидит молчаливый азиат с татуировками якудза, ожидая своей очереди."
                choices.insert(1, {"text": "Поговорить с пациентом.", "action": "talk_yakuza_patient"})


    elif action == "talk_kage_prompt":
        description = "Введите ваш запрос для Искина 'Kage'."
        choices = [{"text": "Отмена", "action": "go", "target": "terminal"}]
        show_input = True

    elif action == "talk_kage_submit":
        user_input = data.get("input")
        description = talk_to_iskin(user_input)
        choices = world["terminal"]["choices"]

    elif action == "hack_arasaka":
        if "cypher_key" in player["inventory"]:
            # Здесь можно запустить настоящую мини-игру
            player["inventory"].append("arasaka_data_chimera")
            player["inventory"].remove("cypher_key")
            player["quests"]["main_quest_step"] = "data_hacked"
            description = "--- ДОСТУП РАЗРЕШЕН ---\nС помощью 'Шифровального ключа' вы обходите защиту как нож сквозь масло. Архив 'Химера' у вас. Теперь самое сложное - доставить его заказчику. Ждите инструкций от 'Kage'."
        else:
            description = "--- ДОСТУП ЗАБЛОКИРОВАН ---\nВаш софт беспомощно скребется о ледяную стену защиты 'Арасаки'. Нужен более совершенный инструмент. Искин упоминал какой-то ключ..."
        choices = world["terminal"]["choices"]

    elif action == "talk_bartender":
        # Этот экшен теперь работает как хаб, открывая дерево диалога
        description = "Орк-бармен мрачно кивает вам. 'Чего тебе?'"
        choices = []

        # Вариант диалога для поиска Декера
        if player["quests"]["main_quest_step"] == "chapter_3_start" and not player["quests"].get("decker_location_inquired"):
            choices.append({"text": "Спросить о бывшем безопаснике 'Арасаки'.", "action": "ask_about_decker"})

        # Варианты диалога для квеста бармена
        bartender_quest_status = player["quests"]["bartender_quest"]
        if bartender_quest_status == "not_started":
            choices.append({"text": "Спросить, не нужна ли помощь.", "action": "start_bartender_quest"})
        elif bartender_quest_status == "started":
            choices.append({"text": "Спросить про 'Хромированных Черепов'.", "action": "check_bartender_quest"})
        elif bartender_quest_status == "completed":
            choices.append({"text": "Сообщить, что проблема с бандой решена.", "action": "complete_bartender_quest"})

        # Выход из диалога
        choices.append({"text": "Ничего. Просто выпить.", "action": "go", "target": "bar_forgotten_bit"})

    elif action == "talk_glitch":
        quest_step = player["quests"]["main_quest_step"]
        if quest_step == "need_key":
            description = "Фигура поднимает голову. Под капюшоном скрывается лицо с кибернетическими имплантами вокруг глаз. 'Я Глитч. Слышал, ты ищешь редкую железку. 'Шифровальный ключ' последнего поколения. У меня есть один. 500 кредитов - и он твой.'"
            # Добавляем динамический выбор
            current_choices = list(world[player["location"]]["choices"])
            buy_choice = {"text": "Купить ключ за 500 кредитов.", "action": "buy_key"}
            # Убираем опцию "Подойти к фигуре", так как мы уже говорим с ним
            choices = [c for c in current_choices if c.get('action') != 'talk_glitch']
            choices.insert(0, buy_choice)
        elif quest_step in ["has_key", "data_hacked", "meet_client", "chapter_1_completed", "chapter_2_start"]:
            description = "'Мы уже закончили дела', - говорит Глитч и снова утыкается в планшет."
            choices = world[player["location"]]["choices"]
        else:
            description = "Фигура в капюшоне игнорирует вас."
            choices = world[player["location"]]["choices"]

    elif action == "buy_key":
        if player["credits"] >= 500:
            player["credits"] -= 500
            player["inventory"].append("cypher_key")
            player["quests"]["main_quest_step"] = "has_key"
            description = "Вы переводите кредиты. Глитч незаметно передает вам небольшой чип. 'Не свети им зря', - бросает он. У вас есть 'Шифровальный ключ'!"
        else:
            description = f"'У тебя нет столько, приятель', - усмехается Глитч. - 'Приходи, когда разбогатеешь. У тебя всего {player['credits']} кредитов.'"
        # После попытки покупки возвращаем стандартные выборы для бара
        choices = world["bar_forgotten_bit"]["choices"]

    elif action == "confront_gang":
        description = "'Чего надо, чип-голова?' - рычит панк с хромированной челюстью. - 'Это наша территория. Бармен задолжал нам. Проваливай, пока целый.'"
        choices = [
            {"text": f"[Угроза СИЛ {player['stats']['strength']}] Проваливайте вы, пока я не сделал из ваших имплантов ожерелье.", "action": "intimidate_gang"},
            {"text": f"[Убеждение ХАР {player['stats']['charisma']}] Может, мы договоримся?", "action": "persuade_gang"},
            {"text": "Я заплачу за него. Сколько?", "action": "pay_gang"},
            {"text": "Молча атаковать.", "action": "fight_gang"},
            {"text": "Развернуться и уйти.", "action": "go", "target": "neo_kyoto_streets"},
        ]

    elif action == "intimidate_gang":
        if player["stats"]["strength"] >= 5:
            description = "Вы делаете шаг вперед, и в ваших глазах появляется стальной блеск. Панки переглядываются. 'Ты... ты псих. Ладно, забирай своего бармена. Нам проблемы не нужны.' Банда быстро ретируется."
            player["quests"]["bartender_quest"] = "completed"
            choices = [{"text": "Вернуться на улицы.", "action": "go", "target": "neo_kyoto_streets"}]
        else:
            description = "'Ха! Ты думаешь, можешь нас запугать?' - смеется лидер. - 'Проваливай, пока мы добрые.'"
            choices = world["back_alley"]["choices"]

    elif action == "pay_gang":
        if player["credits"] >= 200:
            description = "Вы переводите 200 кредитов на счет лидера. 'С тобой приятно иметь дело,' - говорит он. - 'Мы его больше не тронем.' Банда уходит."
            player["credits"] -= 200
            player["quests"]["bartender_quest"] = "completed"
            choices = [{"text": "Вернуться на улицы.", "action": "go", "target": "neo_kyoto_streets"}]
        else:
            description = "'Он должен нам 200 кредитов. У тебя их нет. Не трать наше время.'"
            choices = world["back_alley"]["choices"]

    elif action == "persuade_gang":
        if player['stats']['charisma'] >= 3:
            description = "Вы спокойно объясняете панкам, что бармен находится под вашей защитой и что конфликт с вами принесет им гораздо больше проблем, чем выгоды. Ваши слова звучат убедительно. Лидер кивает. 'Понял. Мы сваливаем.' Банда уходит."
            player["quests"]["bartender_quest"] = "completed"
            choices = [{"text": "Вернуться на улицы.", "action": "go", "target": "neo_kyoto_streets"}]
        else:
            description = "'Твои сказки на нас не действуют, гладкий', - огрызается панк. - 'Либо плати, либо дерись, либо проваливай.'"
            # Возвращаем к выбору действий в переулке
            choices = [
                {"text": f"[Угроза СИЛ {player['stats']['strength']}] Проваливайте вы...", "action": "intimidate_gang"},
                {"text": "Я заплачу за него. Сколько?", "action": "pay_gang"},
                {"text": "Молча атаковать.", "action": "fight_gang"},
                {"text": "Развернуться и уйти.", "action": "go", "target": "neo_kyoto_streets"},
            ]

    elif action == "fight_gang":
        # --- НАЧАЛО БОЯ ---
        player["combat"]["active"] = True
        player["combat"]["enemy"] = enemies["gang_member"].copy()
        player["stats"]["ap"] = player["stats"]["max_ap"]
        player["combat"]["player_pos"] = [2, 5]
        player["combat"]["enemy_pos"] = [12, 5]
        enemy = player["combat"]["enemy"]
        description = f"Боевой режим активирован! Вы видите '{enemy['name']}' на тактической сетке."
        choices = [{"text": "Завершить ход", "action": "combat_end_turn"}]
        background_image = url_for('static', filename=f'images/{world[player["location"]].get("image", "default.jpg")}')
        effects = world[player["location"]].get("effects", [])
        # Возвращаем полный объект player и combat, чтобы фронтенд знал, что нужно переключиться в режим сетки
        return jsonify({
            "description": description,
            "choices": choices,
            "combat": player["combat"],
            "player": player,
            "background_image": background_image,
            "effects": effects
        })

    elif action == "talk_doc_razor":
        quest_status = player["quests"]["doc_razor_quest"]
        
        # Определение основного описания диалога
        if "biomonitor_regulator" in player["inventory"] and quest_status == "started":
            player["inventory"].remove("biomonitor_regulator")
            player["credits"] += 300
            player["quests"]["doc_razor_quest"] = "completed"
            description = "'Ты его достал! Отлично.' - Док забирает деталь. 'Вот твои кредиты, как и договаривались. Ты спас моего клиента от больших проблем.'\n\n(Вы получили 300 кредитов)"
        elif quest_status == "not_started":
            player["quests"]["doc_razor_quest"] = "started"
            description = "'Ищешь работу?' - спрашивает Док, не отрываясь от скальпеля. - 'Мне срочно нужен 'Биомониторный регулятор' модели 7. Достань его, и я заплачу 300 кредитов. Поищи в лавках старья, может, повезет.'\n\n(Квест 'Деталь для риппердока' начат)"
        elif quest_status == "started":
            description = "'Все еще ищешь регулятор? Время - деньги, приятель. Особенно для моего клиента.'"
        elif quest_status == "completed":
            description = "'Спасибо за помощь. Если понадобится качественный хром - заходи.'"
        
        # Определение динамических выборов
        choices = list(world[player["location"]]["choices"]) # Создаем копию, чтобы не изменять оригинал
        
        # Динамическое добавление пациента после выполнения квеста
        if player["quests"]["doc_razor_quest"] == "completed":
            choices.insert(1, {"text": "Поговорить с пациентом.", "action": "talk_yakuza_patient"})

        # Динамическое добавление импланта после первой главы
        main_quest_status = player["quests"]["main_quest_step"]
        implant_available = main_quest_status not in ["start", "need_key", "has_key", "data_hacked", "meet_client"]
        if implant_available and not player.get("implants", {}).get("charisma"):
            choices.insert(1, {"text": "Спросить об улучшении харизмы (750 кредитов).", "action": "buy_charisma_implant"})

    elif action == "talk_shopkeeper":
        description, choices = _generate_shop_interface(player)

    elif action == "buy_item_from_shop":
        item_key = data.get("target")
        purchase_message = ""

        if item_key in world["junk_shop"]["shop_inventory"]:
            item_data = shop_item_pool[item_key]
            if player["credits"] >= item_data["price"]:
                player["credits"] -= item_data["price"]
                player["inventory"].append(item_key)
                world["junk_shop"]["shop_inventory"].remove(item_key)
                purchase_message = f"Вы приобрели '{item_data['name']}'."

                # Особая логика для квестовых предметов
                if item_key == "quantum_processor":
                    player["quests"]["main_quest_step"] = "chapter_2_has_processor"
            else:
                purchase_message = f"'Не хватает кредитов, парень. Нужно {item_data['price']}.'"
        else:
            purchase_message = "'Этого уже нет на прилавке.'"

        # Обновляем интерфейс магазина после покупки
        shop_description, shop_choices = _generate_shop_interface(player)
        description = purchase_message + "\n\n" + shop_description
        choices = shop_choices

    elif action == "meet_mr_shadow":
        if "arasaka_data_chimera" in player["inventory"]:
            player["inventory"].remove("arasaka_data_chimera")
            player["credits"] += 2000
            player["quests"]["main_quest_step"] = "chapter_1_completed"
            description = "Фигура поворачивается. Его лицо скрыто тенью, но голос звучит чётко и властно. 'Вы доставили товар.' Вы передаете чип. Он переводит вам кредиты. 'Это только начало нашего сотрудничества. Содержимое этого чипа изменит многое в этом городе. Будьте наготове.' С этими словами он разворачивается и уходит.\n\n(Вы получили 2000 кредитов. Глава 1 завершена. Спросите 'Kage' о новой миссии, когда будете готовы.)"
        else:
            description = "'Вы пришли с пустыми руками?' - голос фигуры холоден как сталь. - 'Не тратьте мое время.'"
        choices = [{"text": "Покинуть площадку.", "action": "go", "target": "neo_kyoto_streets"}]

    elif action == "buy_charisma_implant":
        implant_cost = 750
        if player["credits"] >= implant_cost:
            player["credits"] -= implant_cost
            player["stats"]["charisma"] += 1
            player["implants"]["charisma"] = True
            description = "Операция прошла быстро. Док Рэйзор вживил вам нейро-лингвистический процессор. Вы чувствуете, как слова складываются в предложения легче, а уверенность в себе растет.\n\n(Ваша Харизма увеличена на 1)"
        else:
            description = f"'Хороший хром стоит хороших денег', - говорит Док. - 'У тебя не хватает. Нужно {implant_cost} кредитов.'"
        
        # Возвращаемся в клинику с обновленными выборами
        choices = list(world[player["location"]]["choices"])
        if player["quests"]["doc_razor_quest"] == "completed":
            choices.insert(1, {"text": "Поговорить с пациентом.", "action": "talk_yakuza_patient"})
        # Опция покупки импланта исчезнет автоматически, так как player['implants']['charisma'] теперь True

    elif action == "talk_vector":
        quest_status = player["quests"]["substation_quest"]
        if quest_status == "not_started":
            description = "'Привет, бегун', - говорит Вектор, протирая очки. - 'Видишь, как свет мерцает? Какая-то сволочь опять полезла к подстанции 42 и всё там закоротила. Если починишь, сообщество нетраннеров этого не забудет. Да и я накину кредитов.'\n\n(Квест 'Перегрузка на подстанции' начат)"
            player["quests"]["substation_quest"] = "started"
            choices = world["digital_dive"]["choices"]
        elif quest_status == "started":
            description = "'Подстанция всё ещё барахлит. Будь осторожен там.'"
            choices = list(world["digital_dive"]["choices"])
            choices.append({"text": "Отправиться к подстанции 42.", "action": "go", "target": "substation_42"})
        elif quest_status == "completed":
            description = "'Свет горит ровно! Отличная работа!' - Вектор переводит вам 200 кредитов. - 'Твоя репутация среди нас выросла.'\n\n(Вы получили 200 кредитов. Репутация у нетраннеров +1)"
            player["credits"] += 200
            player["reputation"]["netrunners"] += 1
            player["quests"]["substation_quest"] = "rewarded" # Чтобы не давал награду дважды
            choices = world["digital_dive"]["choices"]
        elif quest_status == "rewarded":
            if player["reputation"]["netrunners"] > 0:
                description = f"'Приветствую, спаситель нашей сети', - с уважением кивает Вектор. - 'Твоя репутация здесь безупречна.'"
            else:
                description = "'Еще раз спасибо за помощь с питанием.'"
            choices = world["digital_dive"]["choices"]
        else:
            description = "'Еще раз спасибо за помощь с питанием.'"
            choices = world["digital_dive"]["choices"]

    elif action == "talk_cypher":
        quest_status = player["quests"]["main_quest_step"]
        if quest_status == "chapter_2_start":
            description = "Девушка отрывается от терминала. Ее кибернетические глаза оценивающе вас сканируют. 'Ты тот самый, кто взломал 'Арасаку'. Я Сайфер. Знаю, зачем ты здесь. Тебе нужен трекер для ИИ. Я могу его сделать, но мне нужен 'Квантовый процессор'. Достань его, и я помогу.'\n\n(Основной квест обновлен)"
            player["quests"]["main_quest_step"] = "chapter_2_find_processor"
        elif quest_status == "chapter_2_find_processor":
            description = "'Без процессора я ничего не смогу сделать', - говорит Сайфер, возвращаясь к своему терминалу."
        elif quest_status == "chapter_2_has_processor" and "quantum_processor" in player["inventory"]:
            description = "Сайфер берет процессор и подключает его к своему ригу. 'Отлично. Дай мне минуту... Готово. Я засекла сигнал. Следующий фрагмент находится в старой лаборатории 'Кибернесис' в секторе Омега. Удачи, она тебе понадобится.'\n\n(Основной квест обновлен)"
            player["inventory"].remove("quantum_processor")
            player["quests"]["main_quest_step"] = "chapter_2_fragment_location_known"
        elif quest_status == "chapter_2_fragment_location_known":
            description = "'Чего ждешь? Фрагмент не будет ждать вечно.'"
        else:
            description = "Сайфер занята и, похоже, не настроена на пустую болтовню."

        choices = world["digital_dive"]["choices"]

    elif action == "substation_minigame":
        # Инициализация мини-игры
        player["minigame"]["active"] = True
        player["minigame"]["type"] = "substation"
        player["minigame"]["grid_size"] = [12, 9]
        player["minigame"]["start_node"] = [0, 4]
        player["minigame"]["end_node"] = [11, 4]
        player["minigame"]["path"] = [[0, 4]]
        player["minigame"]["completed"] = False
        description = "Интерфейс подстанции. Проложите силовой кабель от входа (зеленый) к выходу (синий), кликая на соседние ячейки."
        choices = [{"text": "Отключиться от терминала", "action": "minigame_exit"}]
        background_image = url_for('static', filename=f'images/{world["substation_42"].get("image", "default.jpg")}')
        effects = world["substation_42"].get("effects", [])
        return jsonify({
            "description": description,
            "choices": choices,
            "minigame": player["minigame"],
            "player": player,
            "combat": player["combat"],
            "background_image": background_image,
            "show_input": False,
            "effects": effects
        })

    elif action == "talk_decker":
        decker_quest_1_status = player["quests"]["decker_quest"]
        decker_quest_2_status = player["quests"].get("decker_quest_2", "not_started")
        main_quest_status = player["quests"]["main_quest_step"]

        if decker_quest_2_status == "completed":
            description = "'Ты сделал это... Я в долгу. Вот, держи.' Декер передает вам зашифрованный чип. 'Это 'Коготь Дракона' - военный ледокол. Используй его с умом.'\n\n(Вы получили 'Военный ледокол'. Основной квест обновлен.)"
            player["inventory"].append("military_icebreaker")
            player["quests"]["decker_quest_2"] = "rewarded"
            player["quests"]["main_quest_step"] = "chapter_3_has_icebreaker"
        elif main_quest_status == "chapter_3_start":
            if decker_quest_1_status == "rewarded":
                # Первый квест Декера выполнен и награда получена, предлагаем второй квест
                if decker_quest_2_status == "not_started":
                    description = "Декер снова смотрит на вас. 'Военный ледокол? Ха. Такие вещи не валяются на дороге. Но... я могу достать один. Взамен сослужи мне еще одну службу. 'Арасака' уволила меня, но мое досье все еще в базе данных NCPD. Если оно всплывет, мне конец. Проникни в их архив и сотри его. Вот пропуск. Справишься - ледокол твой.'\n\n(Квест 'Удалить прошлое' начат)"
                    player["quests"]["decker_quest_2"] = "started"
                    player["inventory"].append("ncpd_archive_pass")
                elif decker_quest_2_status == "started":
                    description = "'Досье все еще в архиве NCPD. Не тяни с этим. Пока оно там, я не могу тебе помочь с ледоколом.'\n\n(Квест 'Удалить прошлое' все еще активен.)"
                # Если decker_quest_2_status == "completed", это обрабатывается в самом начале функции
            else: # Первый квест Декера еще не завершен или не получена награда
                if decker_quest_1_status == "not_started":
                    description = "Декер смотрит на вас с подозрением. 'Военный ледокол? Ты, похоже, не понимаешь, с кем говоришь. Сначала докажи, что ты чего-то стоишь. Саботируй ретранслятор 'Арасаки' в секторе 7. Вот ключ-карта. Тогда поговорим о ледоколах.'\n\n(Квест 'Саботаж' начат. Получена ключ-карта.)"
                    player["quests"]["decker_quest"] = "started"
                    player["inventory"].append("relay_keycard")
                elif decker_quest_1_status == "started":
                    description = "'Ретранслятор 'Арасаки' все еще работает. Закончи то, о чем мы договаривались, прежде чем просить о новом одолжении.'\n\n(Квест 'Саботаж' все еще активен.)"
                elif decker_quest_1_status == "completed":
                    # Сначала выдаем награду за первый квест
                    description = "'Ты саботировал ретранслятор? Отлично. Вот твоя награда.'\n\n(Вы получили 500 кредитов)\n\n"
                    player["credits"] += 500
                    player["quests"]["decker_quest"] = "rewarded"
                    if "relay_keycard" in player["inventory"]: player["inventory"].remove("relay_keycard")
                    # Сразу же предлагаем второй квест
                    description += "'А теперь о ледоколе... Такие вещи не валяются на дороге. Но... я могу достать один. Взамен сослужи мне еще одну службу. 'Арасака' уволила меня, но мое досье все еще в базе данных NCPD. Если оно всплывет, мне конец. Проникни в их архив и сотри его. Вот пропуск. Справишься - ледокол твой.'\n\n(Квест 'Удалить прошлое' начат)"
                    player["quests"]["decker_quest_2"] = "started"
                    player["inventory"].append("ncpd_archive_pass")
        elif decker_quest_1_status == "not_started":
            # Начальное предложение первого квеста Декера, если игрок не на квесте ледокола
            description = "Мужчина с суровым лицом и шрамом через бровь кивает вам. 'Я Декер. Был... начальником смены в 'Арасаке'. Пока кое-кто не устроил там переполох. Они сделали меня козлом отпущения. Я хочу отомстить. Саботируй их ретранслятор в секторе 7, и я заплачу.'\n\n(Квест 'Саботаж' начат. Получена ключ-карта.)"
            player["quests"]["decker_quest"] = "started"
            player["inventory"].append("relay_keycard")
        elif decker_quest_1_status == "started":
            # Напоминание о первом квесте, если он начат
            description = "'Ретранслятор все еще работает. Не тяни с этим.'"
        elif decker_quest_1_status == "completed":
            # Предложение забрать награду за первый квест
            description = "'Отличная работа. 'Арасака' будет несколько дней глуха и слепа в этом секторе. Вот твоя награда.'\n\n(Вы получили 500 кредитов)"
            player["credits"] += 500
            player["quests"]["decker_quest"] = "rewarded"
            if "relay_keycard" in player["inventory"]: player["inventory"].remove("relay_keycard")
        else: # decker_quest_1_status == "rewarded" и игрок не на квесте ледокола
            description = "Декер молча пьет свой напиток, не обращая на вас внимания."
        
        # После разговора возвращаем динамические выборы для бара
        choices = list(world["bar_forgotten_bit"]["choices"])
        main_quest = player["quests"]["main_quest_step"]
        if player["quests"].get("decker_location_inquired", False) and player["quests"].get("decker_quest_2") != "rewarded":
            choices.insert(1, {"text": "Поговорить с ветераном в углу (Декер).", "action": "talk_decker"})

    elif action == "sabotage_relay":
        # Проверка на Харизму (интеллект)
        if player["stats"]["charisma"] >= 4:
            description = "Используя свои знания, полученные от нетраннеров, вы запускаете каскадный сбой в системе. Ретранслятор выходит из строя, не подняв тревоги. Отличная работа."
            player["quests"]["decker_quest"] = "completed"
            choices = [{"text": "Покинуть территорию.", "action": "go", "target": "neo_kyoto_streets"}]
        else:
            description = "Вы пытаетесь взломать систему, но защита слишком сильна. Срабатывает тихая тревога. Лучше убираться отсюда, пока не прибыла охрана."
            # Можно добавить негативные последствия, например, временное появление патрулей
            choices = [{"text": "Срочно уйти.", "action": "go", "target": "neo_kyoto_streets"}]

    elif action == "approach_ai_fragment":
        # Заглушка для следующей главы
        description = "Когда вы прикасаетесь к терминалу, ваш разум пронзает поток чистого кода и обрывочных образов. Вы чувствуете... присутствие. Оно замечает вас и отступает, оставив лишь эхо. Вы получили второй фрагмент. Нужно сообщить об этом 'Мистеру Шэдоу' через Искина."
        player["inventory"].append("ai_fragment_2")
        player["quests"]["main_quest_step"] = "chapter_2_completed"
        choices = [{"text": "Покинуть лабораторию.", "action": "go", "target": "neo_kyoto_streets"}]

    elif action == "erase_decker_file":
        # Skill check based on charisma/intelligence
        if player["stats"]["charisma"] >= 5:
            description = "Вы используете свои навыки социальной инженерии, чтобы замаскировать свои действия под рутинное обслуживание. Файл Декера удален без следа. Охрана ничего не заметила."
            player["quests"]["decker_quest_2"] = "completed"
            if "ncpd_archive_pass" in player["inventory"]: player["inventory"].remove("ncpd_archive_pass")
            choices = [{"text": "Покинуть архив.", "action": "go", "target": "neo_kyoto_streets"}]
        else:
            description = "Ваши действия вызывают подозрение у системы безопасности. Срабатывает тревога! Вам едва удается сбежать, но досье осталось на месте."
            choices = [{"text": "Сбежать.", "action": "go", "target": "neo_kyoto_streets"}]

    elif action == "minigame_exit":
        player["minigame"]["active"] = False
        description = "Вы отключаетесь от терминала подстанции."
        player["location"] = "digital_dive"
        choices = world["digital_dive"]["choices"]

    elif action == "ask_about_decker":
        description = "Бармен хмыкает. 'Бывший из 'Арасаки'? Суровый тип со шрамом? Да, бывает тут. Зовут Декер. Загляни попозже, может, и повезет. Он обычно в углу сидит.'\n\n(Вы узнали, где искать Декера.)"
        player["quests"]["decker_location_inquired"] = True
        choices = world["bar_forgotten_bit"]["choices"]

    elif action == "start_bartender_quest":
        description = "Орк-бармен мрачно кивает вам. 'Вижу, ты не из пугливых. Слушай, есть дело. Местная шпана, 'Хромированные Черепа', достает меня. Если заставишь их убраться, я хорошо заплачу.'\n\n(Квест 'Проблема с бандой' начат)"
        player["quests"]["bartender_quest"] = "started"
        choices = world["bar_forgotten_bit"]["choices"]

    elif action == "check_bartender_quest":
        description = "'Ну что, есть новости по 'Черепам'?' - спрашивает бармен, протирая стакан."
        choices = world["bar_forgotten_bit"]["choices"]

    elif action == "complete_bartender_quest":
        description = "Бармен расплывается в редкой улыбке. 'Ты это сделал! Я твой должник. Вот, держи, как и обещал.'\n\n(Вы получили 250 кредитов)"
        player["credits"] += 250
        player["quests"]["bartender_quest"] = "rewarded"
        choices = world["bar_forgotten_bit"]["choices"]

    elif action == "talk_yakuza_patient":
        description = "Мужчина медленно поворачивает голову. Его глаза пусты, но в них видна старая боль. 'Док - хороший человек. Он помогает тем, от кого отказались другие. Не создавай ему проблем.' Он снова отворачивается, давая понять, что разговор окончен."
        choices = world["doc_razors_clinic"]["choices"]

    else: # Если действие не найдено, возвращаем текущее состояние
        location_data = world[player["location"]]
        description = location_data["description"]
        choices = location_data["choices"]

    final_location_data = world.get(player["location"], {})
    effects = final_location_data.get("effects", [])
    background_image = url_for('static', filename=f'images/{world[player["location"]].get("image", "default.jpg")}')

    return jsonify({
        "description": description,
        "choices": choices,
        "show_input": show_input,
        "player": player,
        "combat": player["combat"],
        "minigame": player["minigame"],
        "background_image": background_image,
        "effects": effects
    })

def handle_minigame_action(data, player):
    """Обрабатывает действия внутри мини-игры."""
    action = data.get("action")
    mg = player["minigame"]
    description = ""
    choices = [{"text": "Отключиться от терминала", "action": "minigame_exit"}]

    if action == "minigame_connect_node":
        target_pos = data.get("target_pos")
        last_node = mg["path"][-1]
        is_adjacent = abs(target_pos[0] - last_node[0]) + abs(target_pos[1] - last_node[1]) == 1
        
        if is_adjacent and target_pos not in mg["path"]:
            mg["path"].append(target_pos)
            if target_pos == mg["end_node"]:
                mg["completed"] = True
                mg["active"] = False
                player["quests"]["substation_quest"] = "completed"
                description = "Щелчок! Кабель встал на место, и гудение трансформаторов выровнялось. Вы починили щит!"
                player["location"] = "digital_dive" # Return to the club
                choices = world["digital_dive"]["choices"]
            else:
                description = "Соединение установлено. Продолжайте."
        else:
            description = "Неверный ход! Нельзя прокладывать кабель через ячейку или по диагонали."
    
    return description, choices
