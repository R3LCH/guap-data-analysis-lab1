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
numeric = df[['time_session', 'click_count', 'buy_count', 'price', 'age']].describe()
duration_stats = numeric['time_session']
organic_n = int((df['channel'] == 'organic').sum())
iphone_n = int((df['device'] == 'iPhone').sum())
facts['interpretations']['conclusion'] = (
    f'Объект исследования — {len(raw)} зарегистрированных сессий интернет-магазина '
    f'({facts["unique_users"]} различных user_id); единица наблюдения — сессия, '
    'не отдельный человек. Проверены названия и типы 11 полей, пропуски и повторы: '
    'два пропуска region/device отмечены Unknown, '
    f'исправлены {facts["normalized_cells"]} написания категорий; '
    f'удалено {implicit} полных дублей после нормализации, явных — {explicit}, '
    f'после приведения типов — {typed_duplicates}. Число сессий после обработки: {len(df)}; пропусков нет. '
    f'Продолжительность: среднее {duration_stats["mean"]:.2f} мин, медиана '
    f'{duration_stats["50%"]:.0f} мин, стандартное отклонение '
    f'{duration_stats["std"]:.2f} мин, квартильный диапазон '
    f'{duration_stats["25%"]:.0f}–{duration_stats["75%"]:.0f} мин, '
    f'минимум {duration_stats["min"]:.0f}, максимум {duration_stats["max"]:.0f} мин. '
    'Среднее выше медианы: длинные сессии увеличивают среднее; разброс значителен. '
    f'Медианы кликов и покупок — {numeric.loc["50%", "click_count"]:.0f} и '
    f'{numeric.loc["50%", "buy_count"]:.0f} за сессию; медианный price — '
    f'{numeric.loc["50%", "price"]:.0f} (валюта не задана), медианный возраст — '
    f'{numeric.loc["50%", "age"]:.0f} лет. '
    f'Страна {region_totals.index[0]}: {region_totals.iloc[0]} '
    f'({region_totals.iloc[0] / len(df):.1%}) сессий; '
    f'organic: {organic_n} ({organic_n / len(df):.1%}); '
    f'iPhone: {iphone_n} ({iphone_n / len(df):.1%}). '
    f'Самая частая пара device/channel — {leader_pair.device}/{leader_pair.channel}: '
    f'{leader_pair["count"]} сессий; по числу разных людей лидирует '
    f'{channel_leader}: {channel_count}, а пара {max_pair[0]}/{max_pair[1]} '
    f'содержит {max_users} разных людей. Повторные сессии одного человека '
    'сохранены; суммы пользователей между группами не обязательно аддитивны. '
    'Выводы описывают только предоставленный набор; без схемы отбора, '
    'затрат на рекламу и контроля смешивающих факторов нельзя переносить доли '
    'на рынок либо объявлять каналы эффективными по причинной связи.')
Path('analysis_facts.json').write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
print('Сохранены: analysis_facts.json и', len(exports), 'CSV-файлов в artifacts/')
print('Баланс строк:', facts['row_reconciliation'])''')
md(12, '''### Дополнительные задания варианта 6: № 7, 9, 13, 15, 22, 25
Расчётная «Длительность сессии» получена вычитанием session_start из session_end в минутах. Сверяем её с исходным time_session; часовой пояс в источнике не указан. Единица агрегации — сессия. Для заданий с категориями используем наблюдаемые квартили длительности: низкая — не более 9 мин (Q1), средняя — свыше 9 и не более 42 мин (Q3), высокая — свыше 42 мин. Так средняя категория охватывает центральную половину распределения; границы рассчитаны на очищенных данных и включают граничные значения однозначно.''')
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
Сводная таблица (pivot_table): по каждому устройству и категории длительности показаны среднее и медиана расчётной длительности в минутах. Пустые сочетания не подменяем нулём.''')
code(12, '''extra7 = df.pivot_table(
    index=['device', 'Категория длительности'], values='Длительность сессии',
    aggfunc=['mean', 'median'], observed=True)
extra7.columns = ['среднее, мин', 'медиана, мин']
display(extra7.round(2))''')
md(12, '', 'extra7')
md(13, '''#### Дополнительное задание № 9
Группировка по категории длительности и стране: средняя, минимальная, максимальная и медианная длительность в минутах. Дополнительно показано число сессий в каждой группе, чтобы единичные наблюдения Unknown нельзя было принять за устойчивую закономерность.''')
code(13, '''extra9 = df.groupby(
    ['Категория длительности', 'region'], observed=True
)['Длительность сессии'].agg(
    сессий='size', среднее='mean', минимум='min', максимум='max', медиана='median')
display(extra9.round(2))''')
md(13, '', 'extra9')
md(14, '''#### Дополнительное задание № 13
Условие «записи, средняя длительность на которых выше числа» трактуем как **выбор каналов, для которых средняя по всем их сессиям превышает порог**, после чего сохраняем все строки выбранных каналов; сравнение каждой отдельной сессии с порогом дало бы иное условие. Порог — строго более 28 минут: близок к общей средней 29,06 мин, но исключает каналы с заметно более короткими сессиями. По отобранным записям группируем канал и вычисляем среднюю и медиану.''')
code(14, '''threshold_min = 28
channel_means = df.groupby('channel', observed=True)['Длительность сессии'].mean()
qualified_channels = channel_means[channel_means > threshold_min].index.tolist()
filtered13 = df[df['channel'].isin(qualified_channels)]
extra13 = filtered13.groupby('channel', observed=True)['Длительность сессии'].agg(
    сессий='size', среднее='mean', медиана='median')
print('Порог: среднее канала >', threshold_min, 'мин; каналы:', qualified_channels,
      '; отобрано сессий:', len(filtered13))
display(extra13.round(2))''')
md(14, '', 'extra13')
md(15, '''#### Дополнительное задание № 15
Из **всего очищенного набора** сначала выбираются два наиболее популярных устройства по числу строк; из них остаются только устройства, средняя длительность по всем их сессиям строго больше 28 мин. Далее включаются все сессии выбранных устройств и рассчитываются средняя, медиана, максимум и минимум длительности; показано число сессий. Равенства по популярности разрешаются по имени устройства.''')
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
display(extra15.round(2))''')
md(15, '', 'extra15')
md(16, '''#### Дополнительное задание № 22
Оставляем только сессии **средней категории** (>9 и ≤42 мин) и два самых популярных устройства по количеству записей во всём очищенном наборе, а не в уже отфильтрованной подвыборке. Сводная таблица (pivot_table): средняя, минимум, максимум, медиана длительности для пар устройство/канал; отдельно показаны размеры ячеек.''')
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
display(extra22.round(2))''')
md(16, '', 'extra22')
md(17, '''#### Дополнительное задание № 25
Берём **низкую и высокую** категории (среднюю исключаем) и два наименее популярных канала по количеству строк во всём очищенном наборе. Сводная таблица (pivot_table) по каналу и устройству показывает среднее и медиану расчётной длительности; рядом число сессий. Это намеренно усечённая выборка: её средние нельзя считать средними по каналам в целом.''')
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
display(extra25.round(2))''')
md(17, '', 'extra25')
md(18, '### Итог статистического анализа дополнительных заданий')
md(18, '', 'extra_conclusion')
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
    f'Для {len(df)} сессий получены {len(extra7)} наблюдаемых сочетаний устройства '
    'и категории; среднее и медиана рассчитаны из интервала timestamps, а не '
    'взяты из готового time_session. '
    f'Сопоставление с исходным полем: {duration_mismatches} расхождений. '
    'Сравнивать средние между категориями можно описательно: группы заранее '
    'сформированы по самой длительности, поэтому разница ожидаема.')
facts['interpretations']['extra9'] = (
    f'Получены {len(extra9)} наблюдаемых сочетаний категории и страны. '
    'Сессия Unknown — единичное наблюдение, а у Russia существенно меньше '
    'записей, чем у United States; минимум и максимум не характеризуют '
    'типичную длительность, для неё рядом приведена медиана.')
facts['interpretations']['extra13'] = (
    f'Порог {threshold_min} мин превышен в средних по каналам '
    f'{", ".join(qualified_channels)}: {len(filtered13)} сессий. '
    'Агрегаты относятся ко всем сессиям этих каналов, включая отдельные '
    'сессии короче порога.')
facts['interpretations']['extra15'] = (
    f'По популярности лидируют {", ".join(top_devices)}; порогу среднего '
    f'>{threshold_min} мин удовлетворяют {", ".join(qualified_devices)}. '
    f'В выборке {len(filtered15)} сессий. Средняя и медиана описывают центр, '
    'минимум и максимум показывают фактические крайние значения внутри группы.')
facts['interpretations']['extra22'] = (
    f'Для средней категории и устройств {", ".join(top_devices)} '
    f'число сессий — {len(filtered22)}, сочетаний устройства и канала — {len(extra22)}. '
    'Полученные средние и крайние значения условны на интервале '
    f'({q1:g}; {q3:g}] минут, не на всех сессиях.')
facts['interpretations']['extra25'] = (
    f'Два наименее частых канала: {", ".join(least_channels)}. '
    f'После исключения средней категории осталось {len(filtered25)} сессий '
    f'в {len(extra25)} наблюдаемых парах канал/устройство. '
    'Высокая и низкая длительности смешаны; медиана может резко отличаться '
    'от среднего, а ячейки с малым n особенно нестабильны.')
facts['interpretations']['extra_conclusion'] = (
    f'Расчётная длительность по всем {len(df)} сессиям полностью совпала с '
    f'time_session ({duration_mismatches} расхождений). '
    f'Квартили Q1={q1:g} и Q3={q3:g} мин задают классы: '
    f'низкий — {category_counts["низкая"]} сессий, '
    f'средний — {category_counts["средняя"]}, '
    f'высокий — {category_counts["высокая"]}. '
    f'Из канальных средних порог >{threshold_min} мин выполняют '
    f'{", ".join(qualified_channels)}; среди двух самых частых устройств '
    f'его выполняют {", ".join(qualified_devices)}. '
    f'Число сессий средней категории и этих двух устройств — {len(filtered22)}; '
    f'у крайних категорий и каналов {", ".join(least_channels)} — '
    f'{len(filtered25)}. Статистики по подвыборкам не подменяют показатели '
    'исходной совокупности: выбор выполнен по измеряемой длительности и '
    'частоте категорий, причинность и значимость различий не проверялись.')
Path('analysis_facts.json').write_text(
    json.dumps(facts, ensure_ascii=False, indent=2), encoding='utf-8')
print('Сохранены дополнительные таблицы:', len(supplemental),
      'CSV; строк по заданиям:', facts['duration_analysis']['filtered_rows'])''')

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
