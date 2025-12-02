import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, date, timedelta
from typing import Optional
import io
from db import get_daily_calories, get_daily_water, get_monthly_stats, get_user_profile


def generate_daily_chart(user_id: int, chart_date: Optional[date] = None) -> Optional[io.BytesIO]:
    if chart_date is None:
        chart_date = date.today()

    calories = get_daily_calories(user_id, chart_date)
    water = get_daily_water(user_id, chart_date)

    user_profile = get_user_profile(user_id)
    if not user_profile:
        return None

    calorie_goal = user_profile.get('calorie_goal', 0)
    water_goal = user_profile.get('water_goal', 0)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    fig.suptitle(f'Статистика за {chart_date.strftime("%d.%m.%Y")}', fontsize=16, fontweight='bold')

    categories = ['Факт', 'Норма']
    calories_data = [calories, calorie_goal]
    colors_cal = ['#FF6B6B', '#FFB6C1']
    bars1 = ax1.bar(categories, calories_data, color=colors_cal, alpha=0.7)
    ax1.set_ylabel('Ккал', fontsize=12)
    ax1.set_title('Калории', fontsize=14)
    ax1.grid(axis='y', alpha=0.3)

    for bar, value in zip(bars1, calories_data):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2., height,
                 f'{int(value)}',
                 ha='center', va='bottom', fontsize=11, fontweight='bold')

    water_data = [water, water_goal]
    colors_water = ['#4ECDC4', '#87CEEB']
    bars2 = ax2.bar(categories, water_data, color=colors_water, alpha=0.7)
    ax2.set_ylabel('мл', fontsize=12)
    ax2.set_title('Вода', fontsize=14)
    ax2.grid(axis='y', alpha=0.3)

    for bar, value in zip(bars2, water_data):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2., height,
                 f'{int(value)}',
                 ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def generate_monthly_chart(user_id: int, year: Optional[int] = None, month: Optional[int] = None) -> Optional[io.BytesIO]:
    if year is None or month is None:
        today = date.today()
        year = today.year
        month = today.month

    stats = get_monthly_stats(user_id, year, month)

    if not stats['dates']:
        return None

    dates = [datetime.strptime(d, '%Y-%m-%d') if isinstance(d, str) else datetime.combine(d, datetime.min.time()) for d
             in stats['dates']]

    fig, ax1 = plt.subplots(figsize=(12, 6))

    color1 = '#FF6B6B'
    ax1.set_xlabel('Дата', fontsize=12)
    ax1.set_ylabel('Калории (ккал)', color=color1, fontsize=12)
    line1 = ax1.plot(dates, stats['calories'], color=color1, marker='o', linewidth=2, markersize=6, label='Калории')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.grid(alpha=0.3)

    ax2 = ax1.twinx()
    color2 = '#4ECDC4'
    ax2.set_ylabel('Вода (мл)', color=color2, fontsize=12)
    bars = ax2.bar(dates, stats['water'], color=color2, alpha=0.6, width=0.8, label='Вода')
    ax2.tick_params(axis='y', labelcolor=color2)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    month_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    fig.suptitle(f'Статистика за {month_names[month - 1]} {year}', fontsize=16, fontweight='bold')

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf
