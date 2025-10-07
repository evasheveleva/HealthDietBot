def calc_water(weight, activity):
    water = weight * 30 + 500 * activity / 30
    return round(water)

def calc_calorie(weight, height, age, activity):
    calorie = weight * 10 + 6.25 * height - 5 * age + 10 * activity #за минуту ходьбы тратится примерно 10 калорий, поэтому такая формула
    return round(calorie)
