"""
main.py
Аналитика сети аптек: Pandas + Matplotlib
Автор: Кирилл
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from sqlalchemy import create_engine, text
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 0. ПОДКЛЮЧЕНИЕ К БД
# ============================================================
DB_URL = "postgresql+psycopg2://postgres:1234@localhost:5432/pharmacy_db"

try:
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Подключение к PostgreSQL успешно")
except Exception as e:
    print(f"⚠️  PostgreSQL недоступен: {e}")
    print("🔄 Генерация синтетических данных для демонстрации...\n")
    engine = None


# ============================================================
# 1. ЗАГРУЗКА / ГЕНЕРАЦИЯ ДАННЫХ
# ============================================================

def load_data(engine):
    """Загружает данные из PostgreSQL или генерирует синтетические."""
    if engine:
        sales_query = """
            SELECT s.sale_date, s.quantity, s.total_amount, s.discount_pct,
                   p.name AS product, p.unit_price,
                   c.name AS category, c.is_seasonal, c.season,
                   ph.name AS pharmacy, ph.city,
                   cu.age_group
            FROM sales s
            JOIN products p    ON s.product_id  = p.product_id
            JOIN categories c  ON p.category_id = c.category_id
            JOIN pharmacies ph ON s.pharmacy_id  = ph.pharmacy_id
            JOIN customers  cu ON s.customer_id  = cu.customer_id
        """
        inventory_query = """
            SELECT ph.name AS pharmacy, p.name AS product,
                   c.name AS category, i.quantity,
                   i.min_stock, i.batch_expires
            FROM inventory i
            JOIN pharmacies ph ON i.pharmacy_id = ph.pharmacy_id
            JOIN products   p  ON i.product_id  = p.product_id
            JOIN categories c  ON p.category_id = c.category_id
        """
        df_sales = pd.read_sql(sales_query, engine)
        df_inv   = pd.read_sql(inventory_query, engine)
    else:
        # ---- Синтетические данные ----
        np.random.seed(42)
        n = 1000

        categories = ['Противовирусные', 'Антигистаминные', 'Солнцезащитные',
                       'Витамины и добавки', 'Сердечно-сосудистые', 'Обезболивающие',
                       'Антибиотики', 'От кашля и простуды', 'Желудочно-кишечные',
                       'Дерматологические']
        seasonal_cats = {'Противовирусные': 'winter', 'Антигистаминные': 'spring',
                          'Солнцезащитные': 'summer', 'От кашля и простуды': 'winter'}
        pharmacies = ['Аптека №1 «Здоровье»', 'Аптека №2 «Фармация»',
                       'Аптека №3 «Медфарм»', 'Аптека №4 «Vita»',
                       'Аптека №5 «ФармПлюс»', 'Аптека №6 «Aptekar»']
        cities = {'Аптека №1 «Здоровье»': 'Алматы', 'Аптека №2 «Фармация»': 'Алматы',
                   'Аптека №3 «Медфарм»': 'Алматы', 'Аптека №4 «Vita»': 'Нур-Султан',
                   'Аптека №5 «ФармПлюс»': 'Нур-Султан', 'Аптека №6 «Aptekar»': 'Шымкент'}
        age_groups = ['18-30', '31-45', '46-60', '60+']

        # Генерация дат с сезонностью
        dates = []
        cat_list = []
        for i in range(n):
            cat = np.random.choice(categories, p=[0.15,0.08,0.05,0.12,0.10,0.12,0.08,0.12,0.10,0.08])
            cat_list.append(cat)
            if cat in ('Противовирусные', 'От кашля и простуды'):
                month = np.random.choice([1,2,11,12,3,4], p=[0.25,0.25,0.20,0.20,0.05,0.05])
            elif cat == 'Антигистаминные':
                month = np.random.choice([3,4,5,6,1,2], p=[0.30,0.30,0.20,0.10,0.05,0.05])
            elif cat == 'Солнцезащитные':
                month = np.random.choice([6,7,8,5,9,1], p=[0.30,0.30,0.20,0.10,0.05,0.05])
            else:
                month = np.random.randint(1, 13)
            year = np.random.choice([2023, 2024], p=[0.55, 0.45])
            day = np.random.randint(1, 28)
            dates.append(pd.Timestamp(year=year, month=month, day=day))

        pharm_list = np.random.choice(pharmacies, n)
        qty = np.random.randint(1, 6, n)
        price = np.random.uniform(300, 5500, n)
        discount = np.where(np.random.random(n) < 0.2,
                             np.random.choice([5, 10, 15], n), 0)
        total = qty * price * (1 - discount / 100)

        df_sales = pd.DataFrame({
            'sale_date':   dates,
            'quantity':    qty,
            'total_amount': total,
            'discount_pct': discount,
            'product':     [f'Препарат {np.random.randint(1,31)}' for _ in range(n)],
            'unit_price':  price,
            'category':    cat_list,
            'is_seasonal': [c in seasonal_cats for c in cat_list],
            'season':      [seasonal_cats.get(c) for c in cat_list],
            'pharmacy':    pharm_list,
            'city':        [cities[p] for p in pharm_list],
            'age_group':   np.random.choice(age_groups, n),
        })

        products_n = 30
        pharmacies_n = 6
        df_inv = pd.DataFrame({
            'pharmacy':    np.repeat(pharmacies[:pharmacies_n], products_n),
            'product':     [f'Препарат {i+1}' for i in range(products_n)] * pharmacies_n,
            'category':    np.random.choice(categories, products_n * pharmacies_n),
            'quantity':    np.random.randint(0, 200, products_n * pharmacies_n),
            'min_stock':   np.random.randint(5, 25, products_n * pharmacies_n),
            'batch_expires': [pd.Timestamp.today() + pd.Timedelta(days=int(d))
                               for d in np.random.randint(-10, 400, products_n * pharmacies_n)]
        })

    return df_sales, df_inv


df_sales, df_inv = load_data(engine)

# ============================================================
# 2. ОЧИСТКА И ПОДГОТОВКА ДАННЫХ
# ============================================================

# Привести даты
df_sales['sale_date'] = pd.to_datetime(df_sales['sale_date'])
df_inv['batch_expires'] = pd.to_datetime(df_inv['batch_expires'])

# Убрать пропуски
df_sales.dropna(subset=['total_amount', 'quantity'], inplace=True)
df_sales['total_amount'] = df_sales['total_amount'].astype(float)
df_sales['quantity']     = df_sales['quantity'].astype(int)

# Добавить временные поля
df_sales['year']    = df_sales['sale_date'].dt.year
df_sales['month']   = df_sales['sale_date'].dt.month
df_sales['month_str'] = df_sales['sale_date'].dt.to_period('M').astype(str)
df_sales['week']    = df_sales['sale_date'].dt.isocalendar().week.astype(int)

print(f"📊 Загружено продаж: {len(df_sales)}")
print(f"📦 Загружено складских позиций: {len(df_inv)}")
print(f"\n📅 Период данных: {df_sales['sale_date'].min().date()} — {df_sales['sale_date'].max().date()}")
print(f"\n🗂 Категории: {df_sales['category'].nunique()}")
print(f"🏪 Аптеки: {df_sales['pharmacy'].nunique()}")

# ============================================================
# 3. АНАЛИТИКА НА PANDAS (5 динамик)
# ============================================================

print("\n" + "="*60)
print("📈 АНАЛИТИКА 1: Ежемесячная выручка + скользящее среднее")
print("="*60)

monthly_rev = (df_sales.groupby('month_str')['total_amount']
               .sum().reset_index().sort_values('month_str'))
monthly_rev.columns = ['month', 'revenue']
monthly_rev['rolling_avg_3m'] = monthly_rev['revenue'].rolling(3, min_periods=1).mean()
monthly_rev['pct_change'] = monthly_rev['revenue'].pct_change() * 100
print(monthly_rev.to_string(index=False))

print("\n" + "="*60)
print("📈 АНАЛИТИКА 2: Сводная таблица — выручка по категориям и месяцам")
print("="*60)

pivot_cat_month = df_sales.pivot_table(
    values='total_amount',
    index='category',
    columns='month',
    aggfunc='sum',
    fill_value=0
).round(0)
pivot_cat_month.columns = [f'M{c:02d}' for c in pivot_cat_month.columns]
print(pivot_cat_month.to_string())

print("\n" + "="*60)
print("📈 АНАЛИТИКА 3: Дефицит склада — позиции ниже минимального порога")
print("="*60)

df_inv['is_deficit'] = df_inv['quantity'] < df_inv['min_stock']
deficit_summary = df_inv[df_inv['is_deficit']].groupby('pharmacy').size().reset_index()
deficit_summary.columns = ['pharmacy', 'deficit_positions']
print(deficit_summary.sort_values('deficit_positions', ascending=False).to_string(index=False))

print("\n" + "="*60)
print("📈 АНАЛИТИКА 4: Процентное изменение выручки по категориям M/M")
print("="*60)

cat_monthly = (df_sales.groupby(['category', 'month_str'])['total_amount']
               .sum().reset_index())
cat_monthly.sort_values(['category', 'month_str'], inplace=True)
cat_monthly['pct_change'] = (cat_monthly.groupby('category')['total_amount']
                              .pct_change() * 100).round(1)
print(cat_monthly[cat_monthly['pct_change'].notna()].to_string(index=False))

print("\n" + "="*60)
print("📈 АНАЛИТИКА 5: Препараты с истекающим сроком (< 60 дней)")
print("="*60)

today = pd.Timestamp.today().normalize()
df_inv['days_to_expire'] = (df_inv['batch_expires'] - today).dt.days
expiring = df_inv[df_inv['days_to_expire'].between(0, 60) & (df_inv['quantity'] > 0)]
print(expiring[['pharmacy', 'product', 'quantity', 'days_to_expire']]
      .sort_values('days_to_expire').to_string(index=False))

# ============================================================
# 4. ВИЗУАЛИЗАЦИЯ MATPLOTLIB (5 графиков → dashboard.png)
# ============================================================

# Стиль
plt.rcParams.update({
    'font.family':      'DejaVu Sans',
    'font.size':        9,
    'axes.titlesize':   11,
    'axes.titleweight': 'bold',
    'axes.spines.top':  False,
    'axes.spines.right':False,
    'figure.facecolor': '#f8f9fa',
    'axes.facecolor':   '#ffffff',
    'axes.grid':        True,
    'grid.alpha':       0.3,
    'grid.linestyle':   '--',
})

fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.patch.set_facecolor('#f0f2f5')
fig.suptitle('📊 Аналитика сети аптек — Дашборд', fontsize=16, fontweight='bold',
             color='#1a1a2e', y=1.01)

COLORS = ['#2196F3', '#4CAF50', '#FF5722', '#9C27B0', '#FF9800',
          '#00BCD4', '#F44336', '#607D8B', '#8BC34A', '#E91E63']

# ─── ГРАФИК 1: Line Chart — динамика выручки + скользящее среднее ───
ax1 = axes[0, 0]
x = range(len(monthly_rev))
ax1.fill_between(x, monthly_rev['revenue'] / 1000, alpha=0.15, color='#2196F3')
ax1.plot(x, monthly_rev['revenue'] / 1000, color='#2196F3', linewidth=2,
         marker='o', markersize=4, label='Выручка')
ax1.plot(x, monthly_rev['rolling_avg_3m'] / 1000, color='#FF5722',
         linewidth=2, linestyle='--', label='Скол. ср. 3М')
ax1.set_xticks(x)
ax1.set_xticklabels(monthly_rev['month'], rotation=45, ha='right', fontsize=7)
ax1.set_title('📈 Ежемесячная выручка + скользящее среднее')
ax1.set_ylabel('Выручка (тыс. тенге)')
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.0f}K'))
ax1.legend(framealpha=0.7)

# ─── ГРАФИК 2: Bar Chart — топ-7 категорий по выручке ───
ax2 = axes[0, 1]
cat_rev = (df_sales.groupby('category')['total_amount'].sum()
           .sort_values(ascending=False).head(7))
bars = ax2.barh(range(len(cat_rev)), cat_rev.values / 1000, color=COLORS[:len(cat_rev)])
ax2.set_yticks(range(len(cat_rev)))
ax2.set_yticklabels(cat_rev.index, fontsize=8)
ax2.set_title('🏆 Топ категорий по выручке')
ax2.set_xlabel('Выручка (тыс. тенге)')
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.0f}K'))
for i, (bar, val) in enumerate(zip(bars, cat_rev.values)):
    ax2.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
             f'{val/1000:.0f}K', va='center', fontsize=7, color='#333')

# ─── ГРАФИК 3: Pie Chart — доли продаж по городам ───
ax3 = axes[0, 2]
city_rev = df_sales.groupby('city')['total_amount'].sum()
wedges, texts, autotexts = ax3.pie(
    city_rev.values,
    labels=city_rev.index,
    autopct='%1.1f%%',
    colors=COLORS[:len(city_rev)],
    startangle=140,
    pctdistance=0.75,
    wedgeprops=dict(edgecolor='white', linewidth=2)
)
for at in autotexts:
    at.set_fontsize(9)
ax3.set_title('🏙️ Доли выручки по городам')

# ─── ГРАФИК 4: Scatter Plot — выручка аптеки vs. дефицитные позиции ───
ax4 = axes[1, 0]
pharmacy_rev  = df_sales.groupby('pharmacy')['total_amount'].sum()
pharmacy_def  = df_inv.groupby('pharmacy')['is_deficit'].sum()
scatter_df = pd.DataFrame({'revenue': pharmacy_rev, 'deficit': pharmacy_def}).dropna()

sc = ax4.scatter(scatter_df['deficit'], scatter_df['revenue'] / 1000,
                  s=120, c=range(len(scatter_df)), cmap='Set1', edgecolors='white', zorder=3)
for i, (idx, row) in enumerate(scatter_df.iterrows()):
    ax4.annotate(idx.replace('Аптека ', '').replace('«', '').replace('»', ''),
                 (row['deficit'], row['revenue']/1000),
                 fontsize=7, ha='left', va='bottom',
                 xytext=(3, 3), textcoords='offset points')

# Линия тренда
if len(scatter_df) > 1:
    z = np.polyfit(scatter_df['deficit'], scatter_df['revenue']/1000, 1)
    p = np.poly1d(z)
    xline = np.linspace(scatter_df['deficit'].min(), scatter_df['deficit'].max(), 50)
    ax4.plot(xline, p(xline), 'r--', alpha=0.5, linewidth=1)

ax4.set_xlabel('Кол-во дефицитных позиций')
ax4.set_ylabel('Выручка (тыс. тенге)')
ax4.set_title('🔗 Дефицит склада vs. Выручка аптеки')

# ─── ГРАФИК 5: Histogram — распределение размеров чеков ───
ax5 = axes[1, 1]
amounts = df_sales['total_amount']
n_bins = 25
counts, bins, patches = ax5.hist(amounts, bins=n_bins, color='#2196F3',
                                   edgecolor='white', alpha=0.85)
# Раскрасить по зонам
for patch, left in zip(patches, bins):
    if left < amounts.quantile(0.33):
        patch.set_facecolor('#4CAF50')
    elif left < amounts.quantile(0.67):
        patch.set_facecolor('#FF9800')
    else:
        patch.set_facecolor('#F44336')

ax5.axvline(amounts.mean(), color='navy', linestyle='--', linewidth=1.5,
            label=f'Среднее: {amounts.mean():.0f} ₸')
ax5.axvline(amounts.median(), color='darkred', linestyle=':', linewidth=1.5,
            label=f'Медиана: {amounts.median():.0f} ₸')
ax5.set_xlabel('Сумма покупки (тенге)')
ax5.set_ylabel('Кол-во продаж')
ax5.set_title('📊 Распределение сумм продаж')
ax5.legend(fontsize=8)

# ─── ВСТАВКА 6: Тепловая карта — сезонные продажи по месяцам ───
ax6 = axes[1, 2]
seasonal_cats_list = ['Противовирусные', 'Антигистаминные',
                       'Солнцезащитные', 'От кашля и простуды']
df_seas = df_sales[df_sales['category'].isin(seasonal_cats_list)]
heat = df_seas.pivot_table(values='total_amount', index='category',
                             columns='month', aggfunc='sum', fill_value=0)
heat = heat.reindex(columns=range(1, 13), fill_value=0)
heat_norm = heat.div(heat.max(axis=1), axis=0)

im = ax6.imshow(heat_norm.values, aspect='auto', cmap='YlOrRd', vmin=0, vmax=1)
ax6.set_xticks(range(12))
ax6.set_xticklabels(['Янв','Фев','Мар','Апр','Май','Июн',
                      'Июл','Авг','Сен','Окт','Ноя','Дек'], fontsize=7)
ax6.set_yticks(range(len(heat_norm)))
ax6.set_yticklabels(heat_norm.index, fontsize=8)
ax6.set_title('🌡️ Сезонность продаж (нормализовано)')
plt.colorbar(im, ax=ax6, fraction=0.046, pad=0.04)

plt.tight_layout(pad=2.0)
plt.savefig('dashboard.png', dpi=150, bbox_inches='tight',
            facecolor=fig.get_facecolor())
print("\n✅ Дашборд сохранён: dashboard.png")
plt.show()

# ============================================================
# 5. КЛЮЧЕВЫЕ ИНСАЙТЫ
# ============================================================
print("\n" + "="*60)
print("💡 КЛЮЧЕВЫЕ БИЗНЕС-ИНСАЙТЫ")
print("="*60)

top_cat = df_sales.groupby('category')['total_amount'].sum().idxmax()
top_cat_rev = df_sales.groupby('category')['total_amount'].sum().max()
print(f"🥇 Самая прибыльная категория: {top_cat} ({top_cat_rev:,.0f} ₸)")

best_month_idx = monthly_rev['revenue'].idxmax()
best_month = monthly_rev.loc[best_month_idx, 'month']
print(f"📅 Лучший месяц по выручке: {best_month} ({monthly_rev.loc[best_month_idx,'revenue']:,.0f} ₸)")

total_deficit = df_inv['is_deficit'].sum()
print(f"⚠️  Позиций с дефицитом: {total_deficit} / {len(df_inv)} ({100*total_deficit/len(df_inv):.1f}%)")

exp_soon = len(df_inv[(df_inv['days_to_expire'].between(0, 60)) & (df_inv['quantity'] > 0)])
print(f"🚨 Партий с истечением < 60 дней: {exp_soon}")

avg_check = df_sales['total_amount'].mean()
print(f"🧾 Средний чек: {avg_check:,.0f} ₸")
