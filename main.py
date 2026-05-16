import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings('ignore')

# Подключение к БД
DB_URL = "postgresql+psycopg2://postgres:password@localhost:5432/pharmacy_db"
try:
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("Подключение успешно")
except:
    engine = None
    print("Работаем с тестовыми данными")

# Загрузка данных
if engine:
    df_sales = pd.read_sql("""
        SELECT s.sale_date, s.quantity, s.total_amount, s.discount_pct,
               p.name AS product, c.name AS category,
               ph.name AS pharmacy, ph.city, cu.age_group
        FROM sales s
        JOIN products p    ON s.product_id  = p.product_id
        JOIN categories c  ON p.category_id = c.category_id
        JOIN pharmacies ph ON s.pharmacy_id  = ph.pharmacy_id
        JOIN customers  cu ON s.customer_id  = cu.customer_id
    """, engine)
    df_inv = pd.read_sql("""
        SELECT ph.name AS pharmacy, p.name AS product,
               i.quantity, i.min_stock, i.batch_expires
        FROM inventory i
        JOIN pharmacies ph ON i.pharmacy_id = ph.pharmacy_id
        JOIN products   p  ON i.product_id  = p.product_id
    """, engine)
else:
    np.random.seed(42)
    n = 1000
    cats = ['Противовирусные','Антигистаминные','Витамины','Обезболивающие',
            'Антибиотики','От кашля','Желудочно-кишечные','Дерматологические',
            'Сердечно-сосудистые','Солнцезащитные']
    phs  = ['№1 Здоровье','№2 Фармация','№3 Медфарм','№4 Vita','№5 ФармПлюс','№6 Aptekar']
    cities = {'№1 Здоровье':'Алматы','№2 Фармация':'Алматы','№3 Медфарм':'Алматы',
              '№4 Vita':'Астана','№5 ФармПлюс':'Астана','№6 Aptekar':'Шымкент'}
    ph_list = np.random.choice(phs, n)
    cat_list = np.random.choice(cats, n, p=[0.15,0.08,0.12,0.12,0.08,0.12,0.10,0.08,0.10,0.05])
    qty   = np.random.randint(1, 6, n)
    price = np.random.uniform(300, 5500, n)
    dates = [pd.Timestamp(year=np.random.choice([2023,2024]), month=np.random.randint(1,13), day=np.random.randint(1,28)) for _ in range(n)]
    df_sales = pd.DataFrame({
        'sale_date': dates, 'quantity': qty, 'total_amount': qty*price,
        'discount_pct': 0, 'product': 'Препарат',
        'category': cat_list, 'pharmacy': ph_list,
        'city': [cities[p] for p in ph_list],
        'age_group': np.random.choice(['18-30','31-45','46-60','60+'], n)
    })
    df_inv = pd.DataFrame({
        'pharmacy': np.repeat(phs, 30),
        'product':  [f'Препарат {i+1}' for i in range(30)] * 6,
        'quantity': np.random.randint(0, 200, 180),
        'min_stock': np.random.randint(5, 25, 180),
        'batch_expires': [pd.Timestamp.today() + pd.Timedelta(days=int(d)) for d in np.random.randint(-10, 400, 180)]
    })

# Подготовка данных
df_sales['sale_date'] = pd.to_datetime(df_sales['sale_date'])
df_sales['month_str'] = df_sales['sale_date'].dt.to_period('M').astype(str)
df_inv['batch_expires'] = pd.to_datetime(df_inv['batch_expires'])
df_inv['is_deficit'] = df_inv['quantity'] < df_inv['min_stock']
df_inv['days_to_expire'] = (df_inv['batch_expires'] - pd.Timestamp.today()).dt.days

# Аналитика 1: ежемесячная выручка + скользящее среднее
monthly = df_sales.groupby('month_str')['total_amount'].sum().reset_index()
monthly.columns = ['month', 'revenue']
monthly['rolling_3m'] = monthly['revenue'].rolling(3, min_periods=1).mean()
monthly['pct_change']  = monthly['revenue'].pct_change() * 100
print("=== Аналитика 1: Выручка по месяцам ===")
print(monthly.to_string(index=False))

# Аналитика 2: сводная таблица категории × месяц
df_sales['month'] = df_sales['sale_date'].dt.month
pivot = df_sales.pivot_table(values='total_amount', index='category', columns='month', aggfunc='sum', fill_value=0)
print("\n=== Аналитика 2: Сводная таблица ===")
print(pivot.to_string())

# Аналитика 3: дефицит по аптекам
deficit = df_inv[df_inv['is_deficit']].groupby('pharmacy').size().reset_index(name='дефицит')
print("\n=== Аналитика 3: Дефицит склада ===")
print(deficit.sort_values('дефицит', ascending=False).to_string(index=False))

# Аналитика 4: % изменение выручки по категориям
cat_mon = df_sales.groupby(['category','month_str'])['total_amount'].sum().reset_index()
cat_mon['pct'] = cat_mon.groupby('category')['total_amount'].pct_change() * 100
print("\n=== Аналитика 4: Изменение выручки по категориям ===")
print(cat_mon.dropna().to_string(index=False))

# Аналитика 5: истекающие сроки годности
expiring = df_inv[(df_inv['days_to_expire'].between(0,60)) & (df_inv['quantity'] > 0)]
print("\n=== Аналитика 5: Истекает срок годности (<60 дней) ===")
print(expiring[['pharmacy','product','quantity','days_to_expire']].sort_values('days_to_expire').to_string(index=False))

# Графики
fig, axes = plt.subplots(2, 3, figsize=(16, 9))
fig.suptitle('Аналитика сети аптек', fontsize=14, fontweight='bold')
COLORS = ['#2196F3','#4CAF50','#FF9800','#9C27B0','#F44336','#00BCD4','#FF5722','#607D8B','#8BC34A','#E91E63']

# 1. Line chart
ax = axes[0,0]
x = range(len(monthly))
ax.fill_between(x, monthly['revenue']/1000, alpha=0.1, color='#2196F3')
ax.plot(x, monthly['revenue']/1000, color='#2196F3', marker='o', markersize=4, label='Выручка')
ax.plot(x, monthly['rolling_3m']/1000, color='#FF5722', linestyle='--', label='Среднее 3М')
ax.set_xticks(x)
ax.set_xticklabels(monthly['month'], rotation=45, ha='right', fontsize=6)
ax.set_title('Динамика выручки по месяцам')
ax.set_ylabel('тыс. тенге')
ax.legend(fontsize=7)
ax.grid(alpha=0.3)

# 2. Bar chart
ax = axes[0,1]
cat_rev = df_sales.groupby('category')['total_amount'].sum().sort_values(ascending=True).tail(7)
ax.barh(range(len(cat_rev)), cat_rev.values/1000, color=COLORS[:len(cat_rev)])
ax.set_yticks(range(len(cat_rev)))
ax.set_yticklabels(cat_rev.index, fontsize=8)
ax.set_title('Топ категорий по выручке')
ax.set_xlabel('тыс. тенге')
ax.grid(axis='x', alpha=0.3)

# 3. Pie chart
ax = axes[0,2]
city_rev = df_sales.groupby('city')['total_amount'].sum()
ax.pie(city_rev.values, labels=city_rev.index, autopct='%1.1f%%',
       colors=COLORS[:3], startangle=140, wedgeprops=dict(edgecolor='white'))
ax.set_title('Доли выручки по городам')

# 4. Scatter plot
ax = axes[1,0]
ph_rev = df_sales.groupby('pharmacy')['total_amount'].sum()
ph_def = df_inv.groupby('pharmacy')['is_deficit'].sum()
sc_df  = pd.DataFrame({'rev': ph_rev, 'def': ph_def}).dropna()
ax.scatter(sc_df['def'], sc_df['rev']/1000, s=150, c=range(len(sc_df)), cmap='Set1', edgecolors='white', zorder=3)
for idx, row in sc_df.iterrows():
    ax.annotate(idx, (row['def'], row['rev']/1000), fontsize=7, xytext=(3,3), textcoords='offset points')
ax.set_title('Дефицит склада vs Выручка')
ax.set_xlabel('Дефицитных позиций')
ax.set_ylabel('тыс. тенге')
ax.grid(alpha=0.3)

# 5. Histogram
ax = axes[1,1]
amounts = df_sales['total_amount']
ax.hist(amounts, bins=25, color='#2196F3', edgecolor='white', alpha=0.8)
ax.axvline(amounts.mean(),   color='navy',    linestyle='--', linewidth=1.5, label=f'Среднее: {amounts.mean():.0f}₸')
ax.axvline(amounts.median(), color='darkred', linestyle=':',  linewidth=1.5, label=f'Медиана: {amounts.median():.0f}₸')
ax.set_title('Распределение сумм продаж')
ax.set_xlabel('Сумма (тенге)')
ax.set_ylabel('Кол-во продаж')
ax.legend(fontsize=7)
ax.grid(alpha=0.3)

# 6. Heatmap сезонность
ax = axes[1,2]
seas_cats = ['Противовирусные','Антигистаминные','Солнцезащитные','От кашля']
df_s = df_sales[df_sales['category'].isin(seas_cats)]
heat = df_s.pivot_table(values='total_amount', index='category', columns='month', aggfunc='sum', fill_value=0)
heat = heat.reindex(columns=range(1,13), fill_value=0)
heat_n = heat.div(heat.max(axis=1), axis=0)
im = ax.imshow(heat_n.values, aspect='auto', cmap='YlOrRd')
ax.set_xticks(range(12))
ax.set_xticklabels(['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'], fontsize=7)
ax.set_yticks(range(len(heat_n)))
ax.set_yticklabels(heat_n.index, fontsize=8)
ax.set_title('Сезонность продаж')
plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

plt.tight_layout()
plt.savefig('dashboard.png', dpi=150, bbox_inches='tight')
print("\nДашборд сохранён: dashboard.png")

# Инсайты
print(f"\n Топ категория: {df_sales.groupby('category')['total_amount'].sum().idxmax()}")
print(f" Лучший месяц: {monthly.loc[monthly['revenue'].idxmax(), 'month']}")
print(f" Дефицит позиций: {df_inv['is_deficit'].sum()} / {len(df_inv)}")
print(f" Средний чек: {df_sales['total_amount'].mean():,.0f} тенге")
