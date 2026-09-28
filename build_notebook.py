from pathlib import Path
import json
import hashlib
import textwrap
import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent
cells = []


def md(stage, text, fact_key=None):
    cell = nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())
    cell.metadata.stage = stage
    if fact_key:
        cell.metadata.fact_key = fact_key
    cells.append(cell)


def code(stage, text):
    cell = nbf.v4.new_code_cell(textwrap.dedent(text).strip())
    cell.metadata.stage = stage
    cells.append(cell)


md(1, '''**Цель работы:**
Осуществить предварительную обработку данных csv-файла, выявить и устранить проблемы в этих данных.

Горяев Дмитрий Сергеевич, группа 4415.

# Загрузка набора данных''')
md(3, '''### Описание предметной области
Вариант № 6. Набор данных: visits.csv — пользовательские сессии интернет-магазина. Одна строка описывает сессию; один пользователь может посетить магазин несколько раз. Поэтому число строк не равно числу уникальных пользователей. Файл предоставлен в материалах дисциплины; разделитель — точка с запятой.

В условии перечислены шесть основных полей; фактический CSV содержит 11 атрибутов. Значения дополнительных полей интерпретируются по именам; валюта price источником не указана.

| Атрибут | Содержание и смысловой тип |
| --- | --- |
| user_id | Идентификатор пользователя, строковый ключ, не количественный показатель. В исходном заголовке есть конечный пробел. |
| region | Страна пользователя, категория. |
| device | Устройство или платформа пользователя, категория; серийного номера устройства нет. |
| channel | Канал привлечения (рекламный источник либо organic), категория. |
| session_start | Дата и время начала сессии, день.месяц.год час:минута. |
| session_end | Дата и время окончания сессии, тот же формат; часовой пояс не задан. |
| time_session | Длительность сессии в минутах; уже присутствует в исходном CSV. |
| click_count | Число кликов в сессии, целое неотрицательное число. |
| buy_count | Число покупок в сессии, целое неотрицательное число. |
| price | Денежный показатель сессии; единица валюты и точная методика не документированы. |
| age | Возраст пользователя в годах, целое число. |''')
md(1, '### 1.Чтение файла (набора данных)\nЛокально используется копия официального CSV. При открытии блокнота в Google Colab файл автоматически загружается из опубликованного репозитория вместе с работой; контроль SHA-256 подтверждает совпадение с исходным набором. Для запуска ячеек нужен доступ к интернету.')
code(1, '''from pathlib import Path
import hashlib
import json
import io
from urllib.request import urlopen
import pandas as pd
from IPython.display import display

source = Path('sources/visits.csv')
if not source.exists():
    source.parent.mkdir(parents=True, exist_ok=True)
    dataset_url = ('https://raw.githubusercontent.com/R3LCH/'
                   'guap-data-analysis-lab1/main/sources/visits.csv')
    data = urlopen(dataset_url, timeout=30).read()
    expected_sha256 = 'ed4789a51f48f715dd46be71d84f2ff46cb672b6cd12f45f7e65a85b8da03b79'
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError('Опубликованный visits.csv отличается от исходного файла')
    source.write_bytes(data)
artifacts = Path('artifacts')
artifacts.mkdir(exist_ok=True)
pd.set_option('display.max_rows', 100)
pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 160)
raw = pd.read_csv(source, sep=';')
df = raw.copy()
facts = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
         'source_rows': len(raw), 'source_columns': len(raw.columns),
         'pandas_version': pd.__version__}
print(f"Загружено: {len(df)} строк × {len(df.columns)} столбцов")
print('SHA-256:', facts['source_sha256'])''')
md(2, '### 2. Обзор данных\n\n2.1 Вывод первых 20 строк с помощью метода head.')
code(2, 'display(df.head(20))')
md(4, '2.2 Оценка данных с помощью метода info.\nМетод показывает типы, количество непустых значений и размер таблицы до очистки.')
code(4, '''df.info()
missing_initial = df.isna().sum()
display(pd.DataFrame({'тип': df.dtypes.astype(str),
                      'непустых': df.notna().sum(), 'пропусков': missing_initial}))''')
md(4, '', 'info')
md(5, '2.3 Оценка данных с помощью метода describe.\nЧисловое хранение user_id не делает идентификатор измеряемой величиной: его среднее, медиана и стандартное отклонение не имеют предметного смысла. Сначала показан стандартный describe, затем описание содержательных числовых показателей без идентификатора.')
code(5, '''display(df.describe().round(3))
metrics = ['time_session', 'click_count', 'buy_count', 'price', 'age']
display(df[metrics].describe().round(3))''')
md(5, '', 'describe')
md(6, '2.4 Оценка названий столбцов\nrepr делает пробелы на границах заголовков видимыми. str.strip удаляет их; остальные названия уже в едином стиле snake_case.')
code(6, '''print('Исходные df.columns:', df.columns.tolist())
print('Явное представление:', [repr(name) for name in df.columns])
old_columns = df.columns.tolist()
df.columns = df.columns.str.strip()
facts['renamed_columns'] = {old: new for old, new in zip(old_columns, df.columns) if old != new}
print('После strip:', df.columns.tolist())
print('Переименованы:', facts['renamed_columns'])''')
md(7, '### 3. Проверка пропусков\nПустые строки в категориальных полях также считаются пропусками. Неизвестные страну и устройство заменяем отдельной категорией Unknown: это сохраняет сессии и пользователей и не приписывает им наиболее частую страну/платформу. По идентификатору, времени и числовым показателям пропусков в данном файле нет. Удаление неполных строк потеряло бы реальные посещения; заполнение модой исказило бы распределения.')
code(7, '''categories = ['region', 'device', 'channel']
for col in categories:
    df[col] = df[col].astype('string').str.strip().replace('', pd.NA)
missing_before = df.isna().sum()
missing_rows = int(df.isna().any(axis=1).sum())
display(pd.DataFrame({'пропусков': missing_before,
                      'доля_%': (missing_before / len(df) * 100).round(4)}))
display(df.loc[df.isna().any(axis=1)])
df[categories] = df[categories].fillna('Unknown')
facts['missing_before'] = missing_before.astype(int).to_dict()
facts['missing_rows'] = missing_rows
facts['missing_after'] = df.isna().sum().astype(int).to_dict()
print('Пропусков после заполнения:', int(df.isna().sum().sum()))''')
md(7, '', 'missing')
md(8, '### 4. Проверка дубликатов\n\n#### Проверка явных дубликатов\nЯвный дубликат — строка, совпадающая по всем 11 полям. Повторение только user_id не является основанием для удаления: пользователь может иметь несколько сессий.')
code(8, '''explicit = int(df.duplicated().sum())
print('Явных полных дубликатов:', explicit)
df = df.drop_duplicates().copy()
facts['explicit_duplicates_removed'] = explicit''')
md(8, '#### Проверка неявных дубликатов\nСравниваем словари категорий до и после нормализации регистра и общеизвестного обозначения страны. USA и United States обозначают одну страну, IPHONE/iPhone и MAC/Mac — одинаковые платформы. Сопоставление выполняется через strip и casefold с явным словарём канонических значений; неизвестные категории сохраняются. Затем повторно проверяем полное совпадение строк. Совпадение пользователя, устройства и канала без совпадения времени не означает дубликат сессии.')
code(8, '''canonical = {
    'region': {'usa': 'United States', 'united states': 'United States',
               'russia': 'Russia', 'unknown': 'Unknown'},
    'device': {'iphone': 'iPhone', 'mac': 'Mac', 'android': 'Android',
               'pc': 'PC', 'unknown': 'Unknown'},
    'channel': {'organic': 'organic', 'faceboom': 'FaceBoom',
                'tiptop': 'TipTop', 'mediatornado': 'MediaTornado'}
}
normalization = []
for col in categories:
    before = df[col].copy()
    after = before.str.casefold().map(canonical[col]).fillna(before)
    for old in sorted(before.unique()):
        new = after[before.eq(old)].iloc[0]
        normalization.append({'column': col, 'before': old, 'after': new,
                              'rows': int(before.eq(old).sum())})
    df[col] = after
normalization_table = pd.DataFrame(normalization)
display(normalization_table)
implicit = int(df.duplicated().sum())
print('Полных дубликатов после нормализации:', implicit)
display(df.loc[df.duplicated(keep=False)].sort_values('user_id'))
df = df.drop_duplicates().reset_index(drop=True)
facts['category_normalization'] = normalization
facts['normalized_cells'] = int(normalization_table.loc[
    normalization_table['before'].ne(normalization_table['after']), 'rows'].sum())
facts['implicit_duplicates_removed'] = implicit
facts['retained_repeated_user_rows'] = int(df['user_id'].duplicated().sum())
print('Сохранено повторных посещений сверх первого для каждого пользователя:',
      facts['retained_repeated_user_rows'])''')
md(8, '', 'duplicates')
md(9, '### 5. Провека типов данных\nЗаголовок сохранён как в официальном шаблоне. Идентификатор переводится в строку, даты — в datetime64 с явно заданным форматом; категории — в category. Целочисленность счётчиков, длительности и возраста проверяется перед переводом в int64. Денежное поле остаётся float64: единица валюты не определена, произвольное округление не применяется.')
code(9, '''types_before = df.dtypes.astype(str)
df['user_id'] = df['user_id'].astype('string')
for col in ['session_start', 'session_end']:
    df[col] = pd.to_datetime(df[col], format='%d.%m.%Y %H:%M', errors='raise')
for col in ['time_session', 'click_count', 'buy_count', 'age']:
    if not df[col].mod(1).eq(0).all():
        raise ValueError(f'Нецелые значения в {col}')
    df[col] = df[col].astype('int64')
for col in categories:
    df[col] = df[col].astype('category')
display(pd.DataFrame({'до': types_before, 'после': df.dtypes.astype(str)}))
typed_duplicates = int(df.duplicated().sum())
print('Дополнительных дубликатов после приведения типов:', typed_duplicates)
df = df.drop_duplicates().reset_index(drop=True)
facts['typed_duplicates_removed'] = typed_duplicates
facts['types_after'] = df.dtypes.astype(str).to_dict()
facts['clean_rows'] = len(df)
facts['unique_users'] = int(df['user_id'].nunique())
facts['remaining_missing'] = int(df.isna().sum().sum())
print('Итого сессий:', len(df), '; уникальных пользователей:', facts['unique_users'])''')
md(10, '### 6. Группировка данных\n\n#### Задание 1\nГруппировка — region и количество устройств каждого типа device. Подсчитываются строки-сессии, а не физические устройства: идентификатора экземпляра устройства в данных нет. Unknown сохраняется отдельной группой.')
code(10, '''region_device = df.groupby(['region', 'device'], observed=True)['user_id'].count()
region_device.name = 'count'
display(region_device.to_frame())''')
md(10, '', 'task1')
md(10, '#### Задание 2\nГруппировка — device и число сессий для каждого channel. Результат — DataFrame count со столбцом count, упорядоченный по убыванию count; равные значения дополнительно сортируются по устройству и каналу.')
code(10, '''count = (df.groupby(['device', 'channel'], observed=True)['user_id']
                  .count().reset_index(name='count')
                  .sort_values(['count', 'device', 'channel'],
                               ascending=[False, True, True], ignore_index=True))
display(count)''')
md(10, '', 'task2')
md(10, '#### Задание 3\nВ условии написано «количество пользователей для каждого канала (device)»: слово «канала» противоречит имени device. Основная сводная таблица построена по смыслу слова «канал», то есть channel. Для прозрачного разрешения опечатки рядом приведена таблица по device. В обоих случаях nunique считает уникальных пользователей, а не количество посещений. Один человек может попасть в несколько групп, поэтому суммы уникальных по группам в общем случае не равны общему числу людей.')
code(10, '''users_channel = (df.pivot_table(index='channel', values='user_id',
                                aggfunc='nunique', observed=True)
                 .rename(columns={'user_id': 'users'})
                 .sort_values('users', ascending=False, kind='stable'))
users_device = (df.pivot_table(index='device', values='user_id',
                               aggfunc='nunique', observed=True)
                .rename(columns={'user_id': 'users'})
                .sort_values('users', ascending=False, kind='stable'))
display(users_channel)
display(users_device)''')
md(10, '', 'task3')
md(10, '#### Задание 4\nСводная таблица уникальных пользователей: device — строки, channel — столбцы. Строки отсортированы по возрастанию device. Ноль означает отсутствие пользователей в соответствующем сочетании в данном наборе, а не пропуск исходного измерения.')
code(10, '''users_device_channel = df.pivot_table(index='device', columns='channel',
                                      values='user_id', aggfunc='nunique',
                                      fill_value=0, observed=True).sort_index()
display(users_device_channel)''')
md(10, '', 'task4')
md(11, '### Вывод')
md(11, '', 'conclusion')
code(11, '''exports = {
    'visits_clean': df,
    'region_device_counts': region_device.reset_index(),
    'device_channel_counts': count,
    'users_by_channel': users_channel.reset_index(),
    'users_by_device': users_device.reset_index(),
    'users_device_channel': users_device_channel.reset_index(),
    'category_normalization': normalization_table,
}
for name, table in exports.items():
    table.to_csv(artifacts / f'{name}.csv', index=False, encoding='utf-8',
                 lineterminator='\\n')
facts['artifact_sha256'] = {
    f'{name}.csv': hashlib.sha256((artifacts / f'{name}.csv').read_bytes()).hexdigest()
    for name in exports
}
facts['aggregations'] = {
    name: json.loads(table.to_json(orient='records', force_ascii=False))
    for name, table in exports.items() if name != 'visits_clean'
}
facts['row_reconciliation'] = {
    'input': len(raw), 'missing_removed': 0, 'explicit_removed': explicit,
    'implicit_removed': implicit, 'typed_removed': typed_duplicates, 'output': len(df)
}
facts['interpretations'] = {
    'info': f'В таблице {len(raw)} строк и 11 столбцов. По одному пропуску в region и device; остальные поля заполнены. Четыре поля первоначально float64, два int64, пять строковых.',
    'describe': 'В исходной таблице медиана time_session равна 21 минуте, среднее — 29,063, максимум — 262: распределение с длинным правым хвостом. Медиана click_count — 7, buy_count — 2, price — 3739. Возраст лежит в диапазоне 10–71 год, медиана — 39. Эти статистики относятся к строкам-сессиям, поэтому повторные посетители учитываются несколько раз. Нулевые значения не считаем пропусками без подтверждения источником.',
    'missing': f'Неполных строк: {missing_rows} из {len(raw)} ({missing_rows / len(raw) * 100:.4f}%). Каждое из полей region и device имеет один пропуск (0,1048%). Заполнение Unknown сохранило обе сессии; после заполнения пропусков нет.',
    'duplicates': f'Явных полных повторов — {explicit}; нормализация исправила {facts["normalized_cells"]} значений категорий и выявила {implicit} полных повторов, которые удалены. Сохранено {facts["retained_repeated_user_rows"]} повторных посещений сверх первого по user_id: отличаются другие поля, поэтому удалять их по одному идентификатору нельзя.',
}
region_totals = df.groupby('region', observed=True).size().sort_values(ascending=False)
leader_pair = count.iloc[0]
channel_leader = users_channel.index[0]
channel_count = int(users_channel.iloc[0, 0])
max_pair = users_device_channel.stack().idxmax()
max_users = int(users_device_channel.loc[max_pair])
facts['interpretations']['task1'] = (f'Больше всего сессий относится к {region_totals.index[0]}: '
    f'{region_totals.iloc[0]} из {len(df)} ({region_totals.iloc[0] / len(df) * 100:.2f}%). '
    'Это распределение посещений по указанной стране, а не оценка населения или рынка. Unknown не смешивается с известными странами.')
facts['interpretations']['task2'] = (f'Наиболее частое сочетание — {leader_pair.device} / {leader_pair.channel}: '
    f'{leader_pair["count"]} сессий. Высокое число сессий не доказывает эффективность рекламы: здесь не сравниваются затраты и конверсия.')
facts['interpretations']['task3'] = (f'Лидер по числу уникальных пользователей — {channel_leader}: {channel_count}. '
    f'Всего в наборе {facts["unique_users"]} уникальных пользователей и {len(df)} сессий. '
    'В таблице по устройствам также считаются пользователи внутри каждой категории, а не визиты.')
facts['interpretations']['task4'] = (f'Наибольшее число пользователей в сочетании {max_pair[0]} / {max_pair[1]}: {max_users}. '
    'Отдельная строка Unknown позволяет не потерять сессию с неизвестным устройством. '
    'Таблица характеризует совместное распределение платформ и каналов в предоставленной выборке.')
facts['interpretations']['conclusion'] = (
    f'Проанализирован visits.csv с {len(raw)} записями сессий интернет-магазина и 11 атрибутами. '
    'Удалён пробел из имени user_id, два пропуска категориальных признаков заменены на Unknown без потери строк. '
    f'Унифицированы {facts["normalized_cells"]} значений страны и устройства; явных дубликатов {explicit}, '
    f'после нормализации удалено {implicit}. После приведения типов дополнительно удалено {typed_duplicates} полных повторов. '
    f'Итог — {len(df)} сессий и {facts["unique_users"]} уникальных пользователей. '
    'Даты преобразованы в datetime, идентификаторы — в строки, категории — в category, целые показатели — в int64. '
    f'По посещениям лидирует {region_totals.index[0]} ({region_totals.iloc[0]} сессий); '
    f'чаще всего встречается {leader_pair.device} / {leader_pair.channel} ({leader_pair["count"]} сессий). '
    f'Канал {channel_leader} привлёк {channel_count} уникальных пользователей; '
    f'максимальная ячейка сводной таблицы — {max_pair[0]} / {max_pair[1]} ({max_users} пользователей). '
    'Повторные визиты сохранены: их нельзя приравнивать к новым людям. '
    'Результаты характеризуют данную выборку, но без данных о рекламных расходах не показывают окупаемость каналов. '
    'Очищенная таблица и все группировки сохранены в CSV для воспроизведения анализа.')
Path('analysis_facts.json').write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
print('Сохранены: analysis_facts.json и', len(exports), 'CSV-файлов в artifacts/')
print('Баланс строк:', facts['row_reconciliation'])''')
md(11, '### Дополнительное задание\nНе выдавалось; не выполнялось. Дополнительные упражнения, назначаемые после защиты, в эту работу не включены.')

notebook = nbf.v4.new_notebook(cells=cells, metadata={
    'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
    'language_info': {'name': 'python'},
    'assignment': {'variant': 6, 'student': 'Горяев Дмитрий Сергеевич', 'group': '4415'}
})
for index, cell in enumerate(notebook.cells):
    cell.id = f'stage-{cell.metadata.stage}-{index:02d}'
NotebookClient(notebook, timeout=180, kernel_name='python3',
               resources={'metadata': {'path': str(ROOT)}}).execute()
facts_result = json.loads((ROOT / 'analysis_facts.json').read_text(encoding='utf-8'))
for cell in notebook.cells:
    if 'fact_key' in cell.metadata:
        cell.source = facts_result['interpretations'][cell.metadata.fact_key]
    cell.metadata.pop('execution', None)
output_path = ROOT / 'ЛР1_Горяев_6.ipynb'
nbf.write(notebook, output_path)
print(f'Исполненный блокнот: {output_path.name}')
print(json.dumps(facts_result['row_reconciliation'], ensure_ascii=False))
