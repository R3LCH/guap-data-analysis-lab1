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


def code(stage, text, table_caption=None):
    cell = nbf.v4.new_code_cell(textwrap.dedent(text).strip())
    cell.metadata.stage = stage
    if table_caption:
        cell.metadata.report_table_caption = table_caption
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
display(normalization_table.loc[
    normalization_table['before'].ne(normalization_table['after'])
].reset_index(drop=True))
implicit = int(df.duplicated().sum())
print('Полных дубликатов после нормализации:', implicit)
if implicit:
    display(df.loc[df.duplicated(keep=False)].sort_values('user_id'))
else:
    print('Совпадающих полных строк после нормализации нет; пустая таблица не нужна.')
df = df.drop_duplicates().reset_index(drop=True)
facts['category_normalization'] = normalization
facts['normalized_cells'] = int(normalization_table.loc[
    normalization_table['before'].ne(normalization_table['after']), 'rows'].sum())
facts['implicit_duplicates_removed'] = implicit
facts['retained_repeated_user_rows'] = int(df['user_id'].duplicated().sum())
print('Сохранено повторных посещений сверх первого для каждого пользователя:',
      facts['retained_repeated_user_rows'])''',
     table_caption='Исправленные написания категориальных значений')
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
print('Итого сессий:', len(df), '; уникальных пользователей:', facts['unique_users'])''',
     table_caption='Типы данных до и после обработки')
md(10, '### 6. Группировка данных\n\n#### Задание 1\nГруппировка — region и количество устройств каждого типа device. Подсчитываются строки-сессии, а не физические устройства: идентификатора экземпляра устройства в данных нет. Unknown сохраняется отдельной группой.')
code(10, '''region_device = df.groupby(['region', 'device'], observed=True)['user_id'].count()
region_device.name = 'count'
display(region_device.to_frame())''',
     table_caption='Число сессий по стране и устройству')
md(10, '', 'task1')
md(10, '#### Задание 2\nГруппировка — device и число сессий для каждого channel. Результат — DataFrame count со столбцом count, упорядоченный по убыванию count; равные значения дополнительно сортируются по устройству и каналу.')
code(10, '''count = (df.groupby(['device', 'channel'], observed=True)['user_id']
                  .count().reset_index(name='count')
                  .sort_values(['count', 'device', 'channel'],
                               ascending=[False, True, True], ignore_index=True))
display(count)''',
     table_caption='Число сессий по устройству и каналу')
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
display(users_device)''', table_caption=[
    'Задание 3: число уникальных пользователей по каналу',
    'Задание 3: число уникальных пользователей по устройству'])
md(10, '', 'task3')
md(10, '#### Задание 4\nСводная таблица уникальных пользователей: device — строки, channel — столбцы. Строки отсортированы по возрастанию device. Ноль означает отсутствие пользователей в соответствующем сочетании в данном наборе, а не пропуск исходного измерения.')
code(10, '''users_device_channel = df.pivot_table(index='device', columns='channel',
                                      values='user_id', aggfunc='nunique',
                                      fill_value=0, observed=True).sort_index()
display(users_device_channel)''',
     table_caption='Задание 4: уникальные пользователи по устройству и каналу')
md(10, '', 'task4')
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
numeric = df[['time_session', 'click_count', 'buy_count', 'price', 'age']].describe()
duration_stats = numeric['time_session']
organic_n = int((df['channel'] == 'organic').sum())
iphone_n = int((df['device'] == 'iPhone').sum())
facts['interpretations']['conclusion'] = (
    f'**Объект и подготовка.** Исследованы {len(raw)} сессии интернет-магазина '
    f'по 11 признакам, принадлежащие {facts["unique_users"]} различным пользователям. '
    'Единица наблюдения — сессия; повторные посещения одного человека не удаляются. '
    'Заголовок user_id очищен от пробела, два пропуска region/device заменены на Unknown, '
    f'исправлены {facts["normalized_cells"]} записи категорий. Полных дубликатов '
    f'до нормализации — {explicit}, после неё — {implicit}, после приведения '
    f'типов — {typed_duplicates}; итог — {len(df)} сессии без пропусков. '
    f'Сохранены {facts["retained_repeated_user_rows"]} повторных посещений '
    'пользователей сверх первого. Даты приведены к datetime, категории — '
    'к category, идентификатор — к строке, счётчики — к целым числам.\\n\\n'
    f'**Количественные признаки.** Длительность сессии в среднем '
    f'{duration_stats["mean"]:.2f} мин при медиане {duration_stats["50%"]:.0f} мин '
    f'и стандартном отклонении {duration_stats["std"]:.2f} мин; квартильный '
    f'интервал {duration_stats["25%"]:.0f}–{duration_stats["75%"]:.0f} мин, '
    f'наблюдаемые пределы {duration_stats["min"]:.0f}–{duration_stats["max"]:.0f} мин. '
    'Среднее превышает медиану из-за длинного правого хвоста: единственное '
    'среднее скрывает разброс длительности. На сессию приходятся в среднем '
    f'{numeric.loc["mean", "click_count"]:.2f} клика и '
    f'{numeric.loc["mean", "buy_count"]:.2f} покупки; медианы — '
    f'{numeric.loc["50%", "click_count"]:.0f} и '
    f'{numeric.loc["50%", "buy_count"]:.0f}. Сессий без покупок — '
    f'{int(df["buy_count"].eq(0).sum())} '
    f'({df["buy_count"].eq(0).mean():.1%}); price имеет среднее '
    f'{numeric.loc["mean", "price"]:.2f} и медиану '
    f'{numeric.loc["50%", "price"]:.0f}, но валюта в источнике не указана. '
    f'Возраст: медиана {numeric.loc["50%", "age"]:.0f} лет, '
    f'наблюдаемый диапазон {numeric.loc["min", "age"]:.0f}–'
    f'{numeric.loc["max", "age"]:.0f} лет.\\n\\n'
    f'**Группировки и сводные таблицы.** В задании 1 страна '
    f'{region_totals.index[0]} дала {region_totals.iloc[0]} '
    f'({region_totals.iloc[0] / len(df):.1%}) сессий; '
    'подавляющая доля одной страны ограничивает сравнение географий. '
    f'В задании 2 канал organic дал {organic_n} '
    f'({organic_n / len(df):.1%}) сессий, устройство iPhone — {iphone_n} '
    f'({iphone_n / len(df):.1%}); наиболее частая пара '
    f'{leader_pair.device}/{leader_pair.channel} насчитывает '
    f'{leader_pair["count"]} ({leader_pair["count"] / len(df):.1%}) сессий. '
    f'В задании 3 {channel_leader} охватывает {channel_count} разных '
    f'пользователей из {facts["unique_users"]}; в задании 4 максимум '
    f'сводной таблицы — {max_pair[0]}/{max_pair[1]}: {max_users} '
    'разных пользователей. Суммировать уникальных пользователей разных '
    'каналов или устройств нельзя: человек мог присутствовать в нескольких группах.\\n\\n'
    '**Ограничения.** Описаны посещения только данного CSV. Нет схемы отбора '
    'посетителей, стоимости рекламы и подтверждения единицы измерения price; '
    'частоту сессий и число пользователей нельзя объявлять доходностью канала, '
    'причинным эффектом или оценкой всей аудитории.')
Path('analysis_facts.json').write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
print('Сохранены: analysis_facts.json и', len(exports), 'CSV-файлов в artifacts/')
print('Баланс строк:', facts['row_reconciliation'])''')
cells[-1].metadata.report_hide = True
md(11, '### Вывод')
md(11, '', 'conclusion')
md(12, '''### Дополнительные задания варианта 6: № 7, 9, 13, 15, 22, 25
Расчётная «Длительность сессии» получена как (session_end − session_start) в минутах для каждой из 954 очищенных строк; сверка с исходным time_session контролирует правильность вычисления. Часовой пояс не указан, абсолютное время между зонами не сравнивается. Единица агрегации — сессия, а не уникальный пользователь.

Пороги категорий заданы эмпирическими квартилями полной очищенной выборки: низкая — не более 9 мин (Q1), средняя — больше 9 и не более 42 мин (Q3), высокая — больше 42 мин. Средняя категория охватывает центральную половину распределения; из-за повторяющихся значений фактические доли могут отличаться от 25/50/25 %. Граничные значения 9 и 42 включены в нижележащую категорию. Пустые сочетания не превращаем в нулевую длительность.''')
code(12, '''df['Длительность сессии'] = (
    (df['session_end'] - df['session_start']).dt.total_seconds() / 60)
if df['Длительность сессии'].isna().any() or (df['Длительность сессии'] < 0).any():
    raise ValueError('Некорректная расчётная длительность сессии')
duration_mismatches = int((df['Длительность сессии'] != df['time_session']).sum())
q1, q3 = df['Длительность сессии'].quantile([0.25, 0.75])
df['Категория длительности'] = pd.cut(
    df['Длительность сессии'], bins=[-float('inf'), q1, q3, float('inf')],
    labels=['низкая', 'средняя', 'высокая'])
print(f'Расхождений с time_session: {duration_mismatches}; Q1={q1:g}, Q3={q3:g} мин')
display(df['Категория длительности'].value_counts(sort=False).to_frame('сессий'))
display(df[['session_start', 'session_end', 'time_session',
            'Длительность сессии', 'Категория длительности']].head(5))''')
md(12, '''#### Дополнительное задание № 7
**Ход выполнения.**

1. После проверки дат берём уже вычисленную из `session_end - session_start` длительность каждой сессии; готовый `time_session` служит лишь контролем, а не источником нового столбца.
2. Применяем одни и те же границы Q1=9 и Q3=42 мин ко всем устройствам, чтобы классы были сопоставимыми. Сохраняем все 954 строки; отбирать только отдельные устройства условие не требует.
3. `pivot_table` с индексом `(device, Категория длительности)` считает среднее и медиану только для реально встречающихся пар (`observed=True`). Отдельная группировка этих же пар даёт `n`: без него совпадающая средняя одной сессии и большой группы выглядела бы одинаково убедительно.

**Зачем две статистики:** среднее чувствительно к крайним значениям даже внутри интервала, медиана показывает его центральную сессию. Воспринимать разницу между низкой и высокой группами как эффект устройства нельзя: группы построены по самой длительности.''')
code(12, '''extra7 = df.pivot_table(
    index=['device', 'Категория длительности'], values='Длительность сессии',
    aggfunc=['mean', 'median'], observed=True)
extra7.columns = ['среднее, мин', 'медиана, мин']
extra7.insert(0, 'сессий', df.groupby(
    ['device', 'Категория длительности'], observed=True).size())
display(extra7.round(2))''', table_caption='Задание 7: длительность по устройству и категории')
md(12, '', 'extra7')
md(13, '''#### Дополнительное задание № 9
**Ход выполнения.**

1. Используем общие для всей таблицы классы длительности из задания 7, не вычисляем новые квартили отдельно для каждой страны: иначе одинаковая сессия получала бы разные метки в разных странах.
2. Группировка по `(Категория длительности, region)` оставляет `Unknown` самостоятельной страной с неизвестным значением, а не приписывает её России или США.
3. В каждой наблюдаемой группе `size` показывает число сессий, `mean` и `median` — центр, `min` и `max` — разброс. Значения округлены только при отображении до двух знаков, вычисления и экспорт сохраняют точность.

**Зачем показывать n:** сравнение средних при одной сессии и сотнях сессий без численности вводит в заблуждение. Различия стран рассматриваются внутри одной категории, а не объявляются свойством всех посетителей соответствующей страны.''')
code(13, '''extra9 = df.groupby(
    ['Категория длительности', 'region'], observed=True
)['Длительность сессии'].agg(
    сессий='size', среднее='mean', минимум='min', максимум='max', медиана='median')
display(extra9.round(2))''',
     table_caption='Задание 9: длительность по категории и стране')
md(13, '', 'extra9')
md(14, '''#### Дополнительное задание № 13
**Ход выполнения и выбор порога.**

1. Считаем `mean` расчётной длительности для **каждого канала по всем его исходным сессиям**, до какого-либо фильтра. Выбираем порог **строго больше 28 мин**: он немного ниже общей средней 29,06 мин и отделяет каналы со сравнительно длинными средними сессиями от двух остальных; это исследовательский критерий, а не норматив качества рекламы.
2. Из списка каналов оставляем те, для которых средняя >28, и маской `.isin()` сохраняем **все** их строки — в том числе посещения короче 28 мин. Фильтр отдельных сессий искусственно поднял бы обе статистики и не отвечал бы условию о средней по каналу.
3. На оставшейся выборке группируем по `channel`, выводим число сессий, среднюю и медиану в минутах. Медиана нужна, чтобы понять, типична ли отобранная высокая средняя для большинства посещений.''')
code(14, '''threshold_min = 28
channel_means = df.groupby('channel', observed=True)['Длительность сессии'].mean()
qualified_channels = channel_means[channel_means > threshold_min].index.tolist()
filtered13 = df[df['channel'].isin(qualified_channels)]
extra13 = filtered13.groupby('channel', observed=True)['Длительность сессии'].agg(
    сессий='size', среднее='mean', медиана='median')
print('Порог: среднее канала >', threshold_min, 'мин; каналы:', qualified_channels,
      '; отобрано сессий:', len(filtered13))
display(extra13.round(2))''',
     table_caption='Задание 13: каналы со средней длительностью более 28 минут')
md(14, '', 'extra13')
md(15, '''#### Дополнительное задание № 15
**Ход выполнения.**

1. На **полном очищенном наборе** считаем число строк для каждого `device`; сортируем по убыванию количества, равенства — по имени, и фиксируем первые два устройства. Это рейтинг популярности по *сессиям*, поскольку серийных номеров физических устройств в CSV нет.
2. Отдельно на том же полном наборе вычисляем среднюю расчётную длительность для каждого типа устройства. Пересекаем зафиксированный топ-2 с условием «средняя >28 мин» из задания 13. Нельзя пересчитывать топ после отбора по времени: изменится базис популярности.
3. `.isin()` сохраняет все сессии оставшихся устройств. Для каждого выводим `n`, среднюю, медиану, минимум и максимум; медиана устойчива к очень длинным сессиям, крайние значения показывают фактический диапазон, а не доверительный интервал.''')
code(15, '''device_popularity = df['device'].value_counts().sort_index().sort_values(
    ascending=False, kind='stable')
top_devices = device_popularity.head(2).index.tolist()
device_means = df.groupby('device', observed=True)['Длительность сессии'].mean()
qualified_devices = [name for name in top_devices
                     if device_means.loc[name] > threshold_min]
filtered15 = df[df['device'].isin(qualified_devices)]
extra15 = filtered15.groupby('device', observed=True)['Длительность сессии'].agg(
    сессий='size', среднее='mean', медиана='median', максимум='max', минимум='min')
print('Топ-2 устройства:', top_devices, '; с допустимой средней:',
      qualified_devices, '; отобрано сессий:', len(filtered15))
display(extra15.round(2))''',
     table_caption='Задание 15: длительность по двум популярным устройствам')
md(15, '', 'extra15')
md(16, '''#### Дополнительное задание № 22
**Ход выполнения.**

1. Используем границы длительности всей очищенной таблицы, полученные до фильтра: «средняя» означает >9 и ≤42 мин. Не называем «средними» сессии длительностью около арифметического среднего 29,06 мин — это именно *категория по квартилям*.
2. Берём топ-2 устройства по количеству **всех 954 строк** из задания 15. Маской с логическим **И** оставляем только строки, одновременно относящиеся к средней категории и к одному из этих устройств. Фильтр >28 мин из заданий 13 и 15 здесь не применяется: его нет в условии № 22.
3. На полученной подвыборке `pivot_table` группирует пары `(device, channel)`, рассчитывает среднюю, минимум, максимум и медиану; `size` добавляет число сессий в ячейке. `observed=True` не создаёт фиктивные пустые сочетания; экстремумы нельзя переносить за пределы интервала отбора.''')
code(16, '''filtered22 = df[
    df['Категория длительности'].eq('средняя') & df['device'].isin(top_devices)]
extra22 = filtered22.pivot_table(
    index=['device', 'channel'], values='Длительность сессии',
    aggfunc=['mean', 'min', 'max', 'median'], observed=True
).rename(columns={'mean': 'среднее', 'min': 'минимум',
                  'max': 'максимум', 'median': 'медиана'})
extra22.columns = extra22.columns.get_level_values(0)
extra22.insert(0, 'сессий', filtered22.groupby(
    ['device', 'channel'], observed=True).size())
print('Топ-2 устройства:', top_devices, '; отобрано сессий:', len(filtered22))
display(extra22.round(2))''',
     table_caption='Задание 22: средняя категория по устройству и каналу')
md(16, '', 'extra22')
md(17, '''#### Дополнительное задание № 25
**Ход выполнения.**

1. Подсчитываем частоты `channel` на полном очищенном наборе и выбираем **два минимальных значения** с однозначным порядком при равенстве. Частоту нельзя пересчитывать только среди коротких или длинных сессий: «непопулярность» в условии относится к исходным записям.
2. Отдельная маска оставляет только категории «низкая» (≤9 мин) **или** «высокая» (>42 мин), исключая весь центральный интервал. Пересекаем её с каналами из шага 1 логическим **И**; то есть не включаем длинные сессии из других каналов.
3. На пересечении `pivot_table` группирует пары `(channel, device)` и считает среднее/медиану длительности, а `size` — объём каждой ячейки. Медиана и n необходимы: выборка намеренно смешивает противоположные хвосты распределения, а одиночная сессия не даёт устойчивой оценки.''')
code(17, '''least_channels = df['channel'].value_counts().sort_index().sort_values(
    ascending=True, kind='stable').head(2).index.tolist()
filtered25 = df[
    df['Категория длительности'].isin(['низкая', 'высокая'])
    & df['channel'].isin(least_channels)]
extra25 = filtered25.pivot_table(
    index=['channel', 'device'], values='Длительность сессии',
    aggfunc=['mean', 'median'], observed=True
).rename(columns={'mean': 'среднее', 'median': 'медиана'})
extra25.columns = extra25.columns.get_level_values(0)
extra25.insert(0, 'сессий', filtered25.groupby(
    ['channel', 'device'], observed=True).size())
print('Два наименее популярных канала:', least_channels,
      '; отобрано сессий:', len(filtered25))
display(extra25.round(2))''',
     table_caption='Задание 25: крайние категории по каналу и устройству')
md(17, '', 'extra25')
code(18, '''supplemental = {
    'visits_with_duration': df, 'extra7_device_duration_category': extra7.reset_index(),
    'extra9_category_region': extra9.reset_index(),
    'extra13_channels_above_threshold': extra13.reset_index(),
    'extra15_top_devices_above_threshold': extra15.reset_index(),
    'extra22_medium_top_devices': extra22.reset_index(),
    'extra25_extremes_least_channels': extra25.reset_index(),
}
for name, table in supplemental.items():
    target = artifacts / f'{name}.csv'
    table.to_csv(target, index=False, encoding='utf-8', lineterminator='\\n')
    facts['artifact_sha256'][target.name] = hashlib.sha256(target.read_bytes()).hexdigest()
    if name != 'visits_with_duration':
        facts['aggregations'][name] = json.loads(
            table.to_json(orient='records', force_ascii=False))
category_counts = df['Категория длительности'].value_counts(sort=False)
facts['duration_analysis'] = {
    'q1_min': float(q1), 'q3_min': float(q3),
    'source_duration_mismatches': duration_mismatches,
    'categories': {str(k): int(v) for k, v in category_counts.items()},
    'threshold_min': threshold_min, 'qualified_channels': qualified_channels,
    'top_devices': top_devices, 'qualified_devices': qualified_devices,
    'least_channels': least_channels,
    'filtered_rows': {str(n): len(v) for n, v in (
        (13, filtered13), (15, filtered15), (22, filtered22), (25, filtered25))}
}
facts['interpretations']['extra7'] = (
    f'**Результат.** Расчёт охватил все {len(df)} сессии; значения '
    f'получены из временных меток, расхождений с time_session — '
    f'{duration_mismatches}. Наблюдаются {len(extra7)} сочетаний устройства '
    'и категории. Для iPhone в низкой категории среднее '
    f'{extra7.loc[("iPhone", "низкая"), "среднее, мин"]:.2f} мин '
    f'(n={extra7.loc[("iPhone", "низкая"), "сессий"]}), '
    f'в высокой — {extra7.loc[("iPhone", "высокая"), "среднее, мин"]:.2f} мин '
    f'(n={extra7.loc[("iPhone", "высокая"), "сессий"]}); '
    f'медиана высокой категории — {extra7.loc[("iPhone", "высокая"), "медиана, мин"]:.0f} мин. '
    f'Единственная сессия Unknown находится в средней категории '
    f'({extra7.loc[("Unknown", "средняя"), "среднее, мин"]:.0f} мин). '
    '**Вывод.** Различие низкой и высокой категорий задано самой '
    'классификацией длительности, поэтому его нельзя объяснять влиянием '
    'устройства. Показатель Unknown на одной сессии не обобщается.')
facts['interpretations']['extra9'] = (
    f'**Результат.** Показаны {len(extra9)} наблюдаемых пар категории и страны. '
    'В средней категории для Russia '
    f'n={extra9.loc[("средняя", "Russia"), "сессий"]}, '
    f'среднее {extra9.loc[("средняя", "Russia"), "среднее"]:.2f} и медиана '
    f'{extra9.loc[("средняя", "Russia"), "медиана"]:.0f} мин; '
    'для United States '
    f'n={extra9.loc[("средняя", "United States"), "сессий"]}, '
    f'среднее {extra9.loc[("средняя", "United States"), "среднее"]:.2f} и медиана '
    f'{extra9.loc[("средняя", "United States"), "медиана"]:.0f} мин. '
    f'В высокой категории средние соответственно '
    f'{extra9.loc[("высокая", "Russia"), "среднее"]:.2f} и '
    f'{extra9.loc[("высокая", "United States"), "среднее"]:.2f} мин. '
    '**Вывод.** Группы неравночисленны, Unknown содержит одну сессию; '
    'квартильные категории намеренно ограничивают диапазоны. Наблюдаемые '
    'различия стран не доказывают различия типичных пользователей или рынков.')
facts['interpretations']['extra13'] = (
    f'**Отбор.** При пороге среднего канала строго >{threshold_min} мин '
    f'сохранены {", ".join(qualified_channels)} — '
    f'{len(filtered13)} из {len(df)} сессий '
    f'({len(filtered13) / len(df):.1%}); другие каналы исключены. '
    f'**Результат.** FaceBoom: n={extra13.loc["FaceBoom", "сессий"]}, '
    f'среднее {extra13.loc["FaceBoom", "среднее"]:.2f}, медиана '
    f'{extra13.loc["FaceBoom", "медиана"]:.0f} мин; organic: '
    f'n={extra13.loc["organic", "сессий"]}, среднее '
    f'{extra13.loc["organic", "среднее"]:.2f}, медиана '
    f'{extra13.loc["organic", "медиана"]:.0f} мин. '
    '**Вывод.** Разница средних не сопровождается разницей медиан; '
    'отбор выполнен по средней канала, а не по длительности каждой сессии. '
    'Это описание посещений, не оценка эффективности привлечения.')
facts['interpretations']['extra15'] = (
    f'**Отбор.** Самые частые устройства — iPhone ({device_popularity["iPhone"]} '
    f'сессия) и Mac ({device_popularity["Mac"]}); среднее обоих '
    f'строго >{threshold_min} мин, поэтому осталось {len(filtered15)} '
    'сессий. **Результат.** iPhone: среднее '
    f'{extra15.loc["iPhone", "среднее"]:.2f}, медиана '
    f'{extra15.loc["iPhone", "медиана"]:.0f}, пределы '
    f'{extra15.loc["iPhone", "минимум"]:.0f}–'
    f'{extra15.loc["iPhone", "максимум"]:.0f} мин. '
    f'Mac: среднее {extra15.loc["Mac", "среднее"]:.2f}, медиана '
    f'{extra15.loc["Mac", "медиана"]:.0f}, пределы '
    f'{extra15.loc["Mac", "минимум"]:.0f}–'
    f'{extra15.loc["Mac", "максимум"]:.0f} мин. '
    '**Вывод.** Центры распределений близки; больший максимум iPhone '
    'характеризует единичную длинную сессию, а не типичную работу устройства.')
facts['interpretations']['extra22'] = (
    '**Отбор.** Из средней категории (>9 и ≤42 мин) и двух самых частых '
    f'устройств {", ".join(top_devices)} получены {len(filtered22)} '
    f'сессии в {len(extra22)} наблюдаемых парах устройство/канал. '
    '**Результат.** Для iPhone/MediaTornado '
    f'n={extra22.loc[("iPhone", "MediaTornado"), "сессий"]}, '
    f'среднее {extra22.loc[("iPhone", "MediaTornado"), "среднее"]:.2f}, '
    f'медиана {extra22.loc[("iPhone", "MediaTornado"), "медиана"]:.0f} мин; '
    'iPhone/organic: '
    f'n={extra22.loc[("iPhone", "organic"), "сессий"]}, '
    f'среднее {extra22.loc[("iPhone", "organic"), "среднее"]:.2f}, '
    f'медиана {extra22.loc[("iPhone", "organic"), "медиана"]:.0f} мин. '
    '**Вывод.** Первое среднее выше в этом интервале, но размер '
    'ячеек различается многократно; минимумы и максимумы искусственно '
    'ограничены фильтром, без фильтра сравнение могло бы измениться.')
facts['interpretations']['extra25'] = (
    f'**Отбор.** По частоте всей таблицы два наименее популярных канала — '
    f'{least_channels[0]} ({df["channel"].value_counts()[least_channels[0]]} '
    f'сессии) и {least_channels[1]} '
    f'({df["channel"].value_counts()[least_channels[1]]}). '
    f'После исключения средней категории осталось {len(filtered25)} '
    f'сессий в {len(extra25)} парах канал/устройство. '
    '**Результат.** TipTop/iPhone: '
    f'n={extra25.loc[("TipTop", "iPhone"), "сессий"]}, '
    f'среднее {extra25.loc[("TipTop", "iPhone"), "среднее"]:.2f}, '
    f'медиана {extra25.loc[("TipTop", "iPhone"), "медиана"]:.0f} мин; '
    f'MediaTornado/PC: n={extra25.loc[("MediaTornado", "PC"), "сессий"]}. '
    '**Вывод.** Разрыв среднего и медианы согласуется со смесью '
    'коротких и длинных сессий; единственная PC-сессия не годится '
    'для сравнения устройств. Итоги не распространяются на исключённую '
    'среднюю категорию или каналы целиком.')
facts['interpretations']['extra_conclusion'] = (
    f'**Сводка по длительности.** Из временных меток рассчитаны '
    f'{len(df)} длительности без ошибок и расхождений с time_session '
    f'({duration_mismatches}). Границы Q1={q1:g} и Q3={q3:g} мин дали '
    f'низкую категорию — {category_counts["низкая"]} сессии, '
    f'среднюю — {category_counts["средняя"]}, '
    f'высокую — {category_counts["высокая"]}. Устройства и страны '
    'сравниваются внутри этих интервалов, а не по всему диапазону '
    'принадлежащих им сессий.\\n\\n'
    '**Что дают дополнительные группировки.** В задании 7 показано '
    'различие внутри трёх категорий для каждого устройства; в задании 9 '
    'страны различаются по числу наблюдений, а не только по среднему. '
    f'При пороге >{threshold_min} мин задание 13 выделило '
    f'{", ".join(qualified_channels)} ({len(filtered13)} сессий), '
    f'задание 15 — {", ".join(qualified_devices)} '
    f'({len(filtered15)}). Задание 22 охватывает '
    f'{len(filtered22)} сессии средней категории двух частых устройств; '
    f'задание 25 — {len(filtered25)} коротких/длинных сессий редких каналов '
    f'{", ".join(least_channels)}.\\n\\n'
    '**Границы интерпретации.** Отбор по длительности создаёт '
    'предсказуемые различия между группами и сдвигает средние; '
    'сравнение разнородных и малых ячеек без доверительных интервалов '
    'не подтверждает значимость или причинный эффект. Выводы ограничены '
    'этими сессиями, а не всей популяцией посетителей магазина.')
Path('analysis_facts.json').write_text(
    json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
print('Сохранены дополнительные таблицы:', len(supplemental),
      'CSV; строк по заданиям:', facts['duration_analysis']['filtered_rows'])''')
cells[-1].metadata.report_hide = True
md(18, '### Итог статистического анализа дополнительных заданий')
md(18, '', 'extra_conclusion')

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
