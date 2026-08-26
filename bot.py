import uuid
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.enums import ParseMode

# ========== ТОКЕН (ЗАМЕНИ НА НОВЫЙ!) ==========
BOT_TOKEN = "ТВОЙ_НОВЫЙ_ТОКЕН_ЗДЕСЬ"

# ========== ИНИЦИАЛИЗАЦИЯ ==========
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ========== FSM ==========
class OSINTForm(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_birth_date = State()
    waiting_for_city = State()
    waiting_for_additional = State()

# ========== ГЕНЕРАТОР HTML ==========
def generate_html(user_data: dict, session_id: str) -> str:
    full_name = user_data.get("full_name", "Неизвестно")
    birth_date = user_data.get("birth_date", "Неизвестно")
    city = user_data.get("city", "Неизвестно")
    additional = user_data.get("additional", "")
    
    additional_nodes = []
    if additional:
        items = [item.strip() for item in additional.split(",") if item.strip()]
        for idx, item in enumerate(items):
            color = "#fd79a8"
            emoji = "📌"
            if "@" in item:
                color = "#00b894"
                emoji = "✉️"
            elif any(c.isdigit() for c in item) and len(item) > 6:
                color = "#0984e3"
                emoji = "📱"
            elif "http" in item.lower() or "." in item and len(item) > 4:
                color = "#e17055"
                emoji = "🌐"
            elif "работа" in item.lower() or "компания" in item.lower():
                color = "#6c5ce7"
                emoji = "🏢"
            additional_nodes.append({
                "id": f"add_{idx}",
                "label": f"{emoji} {item}",
                "color": color
            })
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>OSINT - {full_name}</title>
    <script src="https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.js"></script>
    <style>
        * {{ margin:0; padding:0; }}
        body {{ background:#0f0f1a; color:#fff; font-family: Arial; }}
        .app {{ display:flex; height:100vh; }}
        .sidebar {{
            width:320px; background:#1a1a2e; padding:15px; overflow-y:auto;
            border-right:2px solid #2a2a4a;
        }}
        .logo {{ color:#6c5ce7; font-size:20px; font-weight:bold; margin-bottom:15px; }}
        .info {{
            background:#12121f; padding:10px; border-radius:8px;
            font-size:13px; margin-bottom:10px;
        }}
        .info .lbl {{ color:#8888aa; font-size:11px; }}
        .ctrl {{
            background:#12121f; padding:10px; border-radius:8px; margin-bottom:8px;
        }}
        .ctrl h4 {{ color:#8888aa; font-size:12px; margin-bottom:6px; }}
        .input-group {{ display:flex; gap:5px; margin-bottom:5px; }}
        .input-group input, .input-group select {{
            flex:1; padding:5px 8px; background:#1e1e32; border:1px solid #2a2a4a;
            border-radius:4px; color:#fff; font-size:12px; outline:none;
        }}
        .btn {{
            padding:5px 12px; border:none; border-radius:4px; cursor:pointer;
            font-weight:bold; font-size:12px;
        }}
        .btn-p {{ background:#6c5ce7; color:#fff; }}
        .btn-s {{ background:#00b894; color:#fff; }}
        .btn-d {{ background:#e17055; color:#fff; }}
        .btn-w {{ background:#fdcb6e; color:#1a1a2e; }}
        .graph {{ flex:1; background:#0a0a14; }}
        #network {{ width:100%; height:100%; }}
        .node-item {{
            display:flex; justify-content:space-between; padding:3px 6px;
            background:#1e1e32; border-radius:3px; margin-bottom:2px;
            font-size:12px; cursor:pointer;
        }}
        .node-item:hover {{ background:#2a2a4a; }}
        .status {{
            padding:6px; background:#12121f; border-radius:4px; font-size:11px;
            color:#8888aa; margin-top:8px;
        }}
    </style>
</head>
<body>
<div class="app">
    <div class="sidebar">
        <div class="logo">🕵️ OSINT Map</div>
        <div class="info">
            <div><span class="lbl">👤</span> {full_name}</div>
            <div><span class="lbl">📅</span> {birth_date}</div>
            <div><span class="lbl">🏙️</span> {city}</div>
            {f'<div><span class="lbl">📌</span> {additional}</div>' if additional else ''}
            <div style="font-size:10px;color:#666;margin-top:4px;">ID: {session_id}</div>
        </div>
        
        <div class="ctrl">
            <h4>➕ Добавить узел</h4>
            <div class="input-group">
                <input type="text" id="nodeLabel" placeholder="Название">
                <select id="nodeType">
                    <option value="person">👤 Человек</option>
                    <option value="email">✉️ Email</option>
                    <option value="phone">📱 Телефон</option>
                    <option value="domain">🌐 Сайт</option>
                    <option value="other">📌 Другое</option>
                </select>
            </div>
            <button class="btn btn-p" onclick="addNode()">Добавить</button>
        </div>
        
        <div class="ctrl">
            <h4>🔗 Соединить</h4>
            <div class="input-group">
                <select id="fromNode"><option value="">От</option></select>
                <select id="toNode"><option value="">До</option></select>
            </div>
            <div class="input-group">
                <input type="text" id="edgeLabel" placeholder="Тип связи">
                <button class="btn btn-s" onclick="addEdge()">Связать</button>
            </div>
        </div>
        
        <div class="ctrl" style="flex:1;">
            <h4>📋 Узлы (<span id="nodeCount">0</span>)</h4>
            <div id="nodeList"></div>
        </div>
        
        <div style="display:flex; gap:5px; flex-wrap:wrap;">
            <button class="btn btn-p" onclick="buildGraph()" style="flex:1;">▶ Построить</button>
            <button class="btn btn-w" onclick="clearGraph()" style="flex:1;">🗑 Очистить</button>
            <button class="btn btn-d" onclick="exportGraph()" style="flex:1;">💾 Экспорт</button>
        </div>
        
        <div class="status" id="statusBar">✅ Готов</div>
    </div>
    <div class="graph">
        <div id="network"></div>
    </div>
</div>

<script>
const sessionId = "{session_id}";
let selectedNodes = [];
let network = null;
let nodes = new vis.DataSet([]);
let edges = new vis.DataSet([]);

const initialNodes = [
    {{ id:"main", label:"{full_name}", color:"#6c5ce7", shape:"star", size:30 }},
    {{ id:"birth", label:"📅 {birth_date}", color:"#00b894" }},
    {{ id:"city", label:"🏙️ {city}", color:"#fdcb6e" }}
];
const initialEdges = [
    {{ from:"main", to:"birth", label:"дата" }},
    {{ from:"main", to:"city", label:"город" }}
];
{chr(10).join([f'initialNodes.push({{ id:"{n["id"]}", label:"{n["label"]}", color:"{n["color"]}" }});' for n in additional_nodes])}
{chr(10).join([f'initialEdges.push({{ from:"main", to:"{n["id"]}", label:"связь" }});' for n in additional_nodes])}

function initNetwork() {{
    const container = document.getElementById('network');
    initialNodes.forEach(n => nodes.add(n));
    initialEdges.forEach(e => edges.add(e));
    network = new vis.Network(container, {{ nodes, edges }}, {{
        nodes: {{ shape:'dot', size:20, font:{{ color:'#fff', size:13 }}, borderWidth:2 }},
        edges: {{ width:2, color:'#8888cc', arrows:{{to:{{enabled:true}}}} }},
        physics: {{ enabled:true, stabilization:{{iterations:30}} }},
        interaction: {{ hover:true }}
    }});
    network.on('click', function(p) {{
        if(p.nodes.length) toggleNodeSelection(p.nodes[0]);
        else {{
            document.querySelectorAll('.node-item').forEach(el => el.classList.remove('selected'));
            selectedNodes = [];
        }}
        updateSelectors();
    }});
    updateList();
    updateSelectors();
    setTimeout(() => network.fit(), 300);
}}

function toggleNodeSelection(id) {{
    document.querySelectorAll('.node-item').forEach(el => {{
        if(el.dataset.id == id) {{
            el.classList.toggle('selected');
            const idx = selectedNodes.indexOf(id);
            if(idx > -1) selectedNodes.splice(idx,1);
            else selectedNodes.push(id);
        }}
    }});
    if(selectedNodes.length === 2) {{
        document.getElementById('fromNode').value = selectedNodes[0];
        document.getElementById('toNode').value = selectedNodes[1];
    }}
    updateSelectors();
}}

function addNode() {{
    const label = document.getElementById('nodeLabel').value.trim();
    const type = document.getElementById('nodeType').value;
    if(!label) {{ status('❌ Введите название', true); return; }}
    const colors = {{ person:'#6c5ce7', email:'#00b894', phone:'#0984e3', domain:'#e17055', other:'#fd79a8' }};
    const id = 'n' + Date.now().toString(36);
    nodes.add({{ id, label, color:colors[type]||'#6c5ce7', title:type }});
    document.getElementById('nodeLabel').value = '';
    status('✅ Добавлен: ' + label);
    updateList();
    updateSelectors();
}}

function addEdge() {{
    const from = document.getElementById('fromNode').value;
    const to = document.getElementById('toNode').value;
    const label = document.getElementById('edgeLabel').value.trim() || 'связь';
    if(!from || !to) {{ status('❌ Выберите узлы', true); return; }}
    if(from === to) {{ status('❌ Нельзя в себя', true); return; }}
    edges.add({{ id:'e'+Date.now().toString(36), from, to, label }});
    document.getElementById('edgeLabel').value = '';
    status('✅ Связь добавлена');
    buildGraph();
}}

function buildGraph() {{
    updateList();
    updateSelectors();
    status('✅ Узлов: ' + nodes.length + ', связей: ' + edges.length);
    setTimeout(() => network.fit(), 200);
}}

function clearGraph() {{
    if(!confirm('Очистить всё?')) return;
    nodes.clear();
    edges.clear();
    selectedNodes = [];
    updateList();
    updateSelectors();
    status('🗑 Очищено');
}}

function exportGraph() {{
    const data = {{ session:sessionId, nodes:nodes.get(), edges:edges.get() }};
    const blob = new Blob([JSON.stringify(data,null,2)], {{type:'application/json'}});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'osint_' + sessionId + '.json';
    a.click();
    status('📥 Экспортировано');
}}

function updateList() {{
    const list = document.getElementById('nodeList');
    const all = nodes.get();
    document.getElementById('nodeCount').textContent = all.length;
    list.innerHTML = all.map(n => `
        <div class="node-item" data-id="${{n.id}}" onclick="toggleNodeSelection('${{n.id}}')">
            <span>${{n.label}}</span>
            <span onclick="event.stopPropagation(); removeNode('${{n.id}}')">✕</span>
        </div>
    `).join('');
}}

function updateSelectors() {{
    const from = document.getElementById('fromNode');
    const to = document.getElementById('toNode');
    const opts = nodes.get().map(n => `<option value="${{n.id}}">${{n.label}}</option>`).join('');
    from.innerHTML = '<option value="">От</option>' + opts;
    to.innerHTML = '<option value="">До</option>' + opts;
    if(selectedNodes.length === 2) {{
        from.value = selectedNodes[0];
        to.value = selectedNodes[1];
    }}
}}

function removeNode(id) {{
    if(!confirm('Удалить узел?')) return;
    nodes.remove(id);
    const remove = edges.get().filter(e => e.from === id || e.to === id).map(e => e.id);
    edges.remove(remove);
    selectedNodes = selectedNodes.filter(n => n !== id);
    updateList();
    updateSelectors();
    status('🗑 Удалён');
}}

function status(msg, err=false) {{
    const bar = document.getElementById('statusBar');
    bar.innerHTML = (err ? '❌ ' : '✅ ') + msg;
    bar.style.color = err ? '#e17055' : '#8888aa';
}}

window.onload = function() {{
    initNetwork();
    document.getElementById('nodeLabel').addEventListener('keypress', e => {{
        if(e.key === 'Enter') addNode();
    }});
}};
</script>
</body>
</html>'''
    return html

# ========== ОБРАБОТЧИКИ БОТА ==========

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Собрать данные", callback_data="start_osint")],
        [InlineKeyboardButton(text="📖 Инструкция", callback_data="help")]
    ])
    await message.answer(
        "🕵️ **OSINT Визуализатор**\n\n"
        "Создам HTML-файл с картой связей.\n"
        "Нажми 'Собрать данные' и ответь на 4 вопроса.",
        reply_markup=kb,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query(lambda c: c.data == "help")
async def help_cmd(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📖 **Инструкция:**\n\n"
        "1️⃣ Нажми 'Собрать данные'\n"
        "2️⃣ Введи ФИО\n"
        "3️⃣ Введи дату рождения\n"
        "4️⃣ Введи город\n"
        "5️⃣ Введи доп. инфо (или пропусти)\n"
        "6️⃣ Получи HTML-файл!"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "start_osint")
async def start_osint(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(session_id=str(uuid.uuid4())[:8])
    await state.set_state(OSINTForm.waiting_for_full_name)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
    ])
    await callback.message.edit_text(
        "📝 **Шаг 1/4: Введите ФИО**\n\nПример: `Иванов Иван`",
        reply_markup=kb,
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "cancel")
async def cancel_osint(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")
    await callback.answer()

@dp.message(OSINTForm.waiting_for_full_name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    if len(message.text) < 2:
        await message.answer("❌ Минимум 3 символа:")
        return
    await state.update_data(full_name=message.text.strip())
    await state.set_state(OSINTForm.waiting_for_birth_date)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_name")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
    ])
    await message.answer(
        "📝 **Шаг 2/4: Дата рождения**\n\nФормат: `15.05.1990` или `неизвестно`",
        reply_markup=kb,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query(lambda c: c.data == "back_name")
async def back_name(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(OSINTForm.waiting_for_full_name)
    await callback.message.edit_text("📝 **Шаг 1/4: Введите ФИО**")
    await callback.answer()

@dp.message(OSINTForm.waiting_for_birth_date, F.text)
async def process_birth(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text.lower() != "неизвестно" and len(text) < 6:
        await message.answer("❌ Неверный формат:")
        return
    await state.update_data(birth_date=text)
    await state.set_state(OSINTForm.waiting_for_city)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_birth")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
    ])
    await message.answer(
        "📝 **Шаг 3/4: Город**\n\nПример: `Москва` или `неизвестно`",
        reply_markup=kb,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query(lambda c: c.data == "back_birth")
async def back_birth(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(OSINTForm.waiting_for_birth_date)
    await callback.message.edit_text("📝 **Шаг 2/4: Дата рождения**")
    await callback.answer()

@dp.message(OSINTForm.waiting_for_city, F.text)
async def process_city(message: types.Message, state: FSMContext):
    if len(message.text) < 2:
        await message.answer("❌ Слишком коротко:")
        return
    await state.update_data(city=message.text.strip())
    await state.set_state(OSINTForm.waiting_for_additional)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_city")],
        [InlineKeyboardButton(text="⏭️ Пропустить", callback_data="skip")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
    ])
    await message.answer(
        "📝 **Шаг 4/4: Доп. информация**\n\n"
        "Телефоны, email через запятую.\n"
        "Пример: `+7(999)123-45-67, email@mail.ru`",
        reply_markup=kb,
        parse_mode=ParseMode.MARKDOWN
    )

@dp.callback_query(lambda c: c.data == "back_city")
async def back_city(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(OSINTForm.waiting_for_city)
    await callback.message.edit_text("📝 **Шаг 3/4: Город**")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "skip")
async def skip(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(additional="")
    await send_file(callback.message, state)
    await callback.answer()

@dp.message(OSINTForm.waiting_for_additional, F.text)
async def process_additional(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text.lower() == "пропустить":
        text = ""
    await state.update_data(additional=text)
    await send_file(message, state)

async def send_file(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_data = {
        "full_name": data.get("full_name", "Неизвестно"),
        "birth_date": data.get("birth_date", "Неизвестно"),
        "city": data.get("city", "Неизвестно"),
        "additional": data.get("additional", "")
    }
    session_id = data.get("session_id", str(uuid.uuid4())[:8])
    
    html = generate_html(user_data, session_id)
    file = BufferedInputFile(html.encode('utf-8'), 
                             filename=f"OSINT_{user_data['full_name'].replace(' ', '_')}.html")
    
    await message.answer_document(
        document=file,
        caption=f"✅ **Готово!**\n\n"
                f"👤 {user_data['full_name']}\n"
                f"📅 {user_data['birth_date']}\n"
                f"🏙️ {user_data['city']}\n"
                f"{'📌 ' + user_data['additional'] if user_data['additional'] else ''}"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Новая визуализация", callback_data="start_osint")]
    ])
    await message.answer("🎯 Нажми для новой визуализации", reply_markup=kb)
    await state.clear()

@dp.message(StateFilter(OSINTForm))
async def invalid(message: types.Message):
    await message.answer("❌ Введи текст.")

# ========== ЗАПУСК ==========
async def main():
    print("🚀 OSINT бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
